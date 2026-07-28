from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)

from sqlalchemy.orm import Session


from app.database.session import get_db


from app.core.dependencies import (
    get_current_user,
)


from app.models.user import User


from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserResponse,
    MessageResponse,
)


from app.services.auth_service import (
    AuthService,
)



router = APIRouter(
    prefix="/auth",
    tags=[
        "Authentication"
    ],
)



# ==========================================================
# Cookie Configuration
# ==========================================================


ACCESS_COOKIE = "access_token"

REFRESH_COOKIE = "refresh_token"


ACCESS_COOKIE_MAX_AGE = (
    60 * 15
)


REFRESH_COOKIE_MAX_AGE = (
    60 * 60 * 24 * 30
)



def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
) -> None:
    """
    Stores JWT tokens securely.

    Access:
        HttpOnly cookie

    Refresh:
        HttpOnly cookie

    Prevents JavaScript access.
    """


    response.set_cookie(

        key=ACCESS_COOKIE,

        value=access_token,

        httponly=True,

        secure=True,

        samesite="lax",

        path="/",

        max_age=ACCESS_COOKIE_MAX_AGE,
    )



    response.set_cookie(

        key=REFRESH_COOKIE,

        value=refresh_token,

        httponly=True,

        secure=True,

        samesite="lax",

        path="/",

        max_age=REFRESH_COOKIE_MAX_AGE,
    )



def clear_auth_cookies(
    response: Response,
) -> None:
    """
    Remove authentication cookies.
    """


    response.delete_cookie(
        ACCESS_COOKIE,
        path="/",
    )


    response.delete_cookie(
        REFRESH_COOKIE,
        path="/",
    )
    
# ==========================================================
# REGISTER
# ==========================================================


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):
    """
    Register a new Bhudi user.

    Business logic is handled by
    AuthService.
    """

    service = AuthService(
        db
    )


    user = service.register(

        email=request.email,

        password=request.password,

        first_name=request.first_name,

        last_name=request.last_name,
    )


    return user



# ==========================================================
# LOGIN
# ==========================================================


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    request: LoginRequest,

    response: Response,

    http_request: Request,

    db: Session = Depends(get_db),
):
    """
    Authenticate user and issue tokens.

    Captures:

    - IP address
    - User agent

    for refresh-token session tracking.
    """

    service = AuthService(
        db
    )


    user = service.authenticate(

        request.email,

        request.password,
    )



    #
    # Capture client information
    #

    ip_address = None


    if http_request.client:

        ip_address = (
            http_request.client.host
        )



    user_agent = (
        http_request.headers.get(
            "user-agent"
        )
    )



    tokens = service.login(

        user,

        ip_address=ip_address,

        user_agent=user_agent,
    )



    set_auth_cookies(

        response,

        tokens["access_token"],

        tokens["refresh_token"],
    )



    return tokens

# ==========================================================
# REFRESH TOKEN ROTATION
# ==========================================================


@router.post(
    "/refresh",
    response_model=TokenResponse,
)
def refresh(
    request: Request,

    response: Response,

    body: RefreshTokenRequest | None = None,

    db: Session = Depends(get_db),
):
    """
    Rotate refresh token.

    Supported clients:

    Browser:
        HttpOnly refresh_token cookie


    API clients:
        JSON body refresh_token


    Security:

    - JWT validation
    - Token family validation
    - Replay detection
    - Rotation
    """

    service = AuthService(
        db
    )


    #
    # 1. Try secure cookie first
    #

    refresh_token = (
        request.cookies.get(
            REFRESH_COOKIE
        )
    )


    #
    # 2. Fallback to API request body
    #

    if (
        refresh_token is None
        and body is not None
    ):

        refresh_token = (
            body.refresh_token
        )



    if not refresh_token:

        raise HTTPException(

            status_code=status.HTTP_401_UNAUTHORIZED,

            detail="Refresh token missing",

            headers={
                "WWW-Authenticate": "Bearer",
            },
        )



    #
    # AuthService handles:
    #
    # - JWT verification
    # - database lookup
    # - replay detection
    # - token rotation
    #

    tokens = (
        service.refresh_access_token(
            refresh_token
        )
    )



    #
    # Replace old cookies
    #

    set_auth_cookies(

        response,

        tokens["access_token"],

        tokens["refresh_token"],
    )



    return tokens

# ==========================================================
# CURRENT USER
# ==========================================================


@router.get(
    "/me",
    response_model=UserResponse,
)
def me(
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    Return authenticated user.

    Protected endpoint.

    Requires:

        Authorization:
        Bearer <access_token>

    or

        access_token cookie
    """

    return current_user



# ==========================================================
# LOGOUT
# ==========================================================


@router.post(
    "/logout",
    response_model=MessageResponse,
)
def logout(
    request: Request,

    response: Response,

    db: Session = Depends(get_db),
):
    """
    Logout current session.

    Actions:

    1. Revoke refresh token
    2. Delete authentication cookies
    """


    service = AuthService(
        db
    )


    refresh_token = (
        request.cookies.get(
            REFRESH_COOKIE
        )
    )



    if refresh_token:

        service.logout(
            refresh_token
        )



    clear_auth_cookies(
        response
    )



    return MessageResponse(
        message="Logged out successfully"
    )



# ==========================================================
# LOGOUT ALL SESSIONS
# ==========================================================


@router.post(
    "/logout-all",
    response_model=MessageResponse,
)
def logout_all(
    response: Response,

    current_user: User = Depends(
        get_current_user
    ),

    db: Session = Depends(get_db),
):
    """
    Revoke every active session
    belonging to the user.

    Used for:

    - password compromise
    - security response
    - user request
    """


    service = AuthService(
        db
    )


    service.logout_all(
        current_user
    )



    clear_auth_cookies(
        response
    )



    return MessageResponse(
        message="All sessions logged out successfully"
    )
    
# ==========================================================
# Cookie Security Helpers
# ==========================================================


COOKIE_SECURE = getattr(
    settings,
    "COOKIE_SECURE",
    True,
)


COOKIE_SAMESITE = getattr(
    settings,
    "COOKIE_SAMESITE",
    "lax",
)



def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
) -> None:
    """
    Store authentication tokens
    in HttpOnly cookies.
    """


    response.set_cookie(

        key=ACCESS_COOKIE,

        value=access_token,

        httponly=True,

        secure=COOKIE_SECURE,

        samesite=COOKIE_SAMESITE,

        path="/",

        max_age=ACCESS_COOKIE_MAX_AGE,
    )


    response.set_cookie(

        key=REFRESH_COOKIE,

        value=refresh_token,

        httponly=True,

        secure=COOKIE_SECURE,

        samesite=COOKIE_SAMESITE,

        path="/",

        max_age=REFRESH_COOKIE_MAX_AGE,
    )