from fastapi import (
    APIRouter,
    Depends,
    Response,
    Request,
    status,
)

from sqlalchemy.orm import Session

from app.database.session import get_db
from app.core.dependencies import get_current_user

from app.models.user import User

from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserResponse,
    MessageResponse,
)

from app.services.auth_service import AuthService


router = APIRouter(
    tags=["Authentication"],
)



def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
):

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60 * 15,
    )


    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )



# -------------------------------------------------
# REGISTER
# -------------------------------------------------

@router.post(
    "/refresh",
    response_model=TokenResponse,
)
def refresh_access_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    """
    Rotate a refresh token and issue a new access token.

    All business logic is delegated to AuthService.
    """

    auth_service = AuthService(db)

    return auth_service.refresh_access_token(
        request.refresh_token,
    )


# -------------------------------------------------
# LOGIN
# -------------------------------------------------

@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    request: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):

    service = AuthService(db)


    user = service.authenticate(
        request.email,
        request.password,
    )


    tokens = service.login(user)


    set_auth_cookies(
        response,
        tokens["access_token"],
        tokens["refresh_token"],
    )


    return tokens



# -------------------------------------------------
# CURRENT USER
# -------------------------------------------------

@router.get(
    "/me",
    response_model=UserResponse,
)
def me(
    current_user: User = Depends(get_current_user),
):

    return current_user



# -------------------------------------------------
# REFRESH TOKEN
# -------------------------------------------------

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

    service = AuthService(db)


    refresh_token = (
        request.cookies.get(
            "refresh_token"
        )
    )


    if not refresh_token and body:
        refresh_token = body.refresh_token


    if not refresh_token:

        from fastapi import HTTPException

        raise HTTPException(
            status_code=401,
            detail="Refresh token missing",
        )


    tokens = service.refresh_access_token(
        refresh_token
    )


    set_auth_cookies(
        response,
        tokens["access_token"],
        tokens["refresh_token"],
    )


    return tokens



# -------------------------------------------------
# LOGOUT
# -------------------------------------------------

@router.post(
    "/logout",
    response_model=MessageResponse,
)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):

    service = AuthService(db)


    refresh_token = request.cookies.get(
        "refresh_token"
    )


    if refresh_token:

        service.logout(
            refresh_token
        )


    response.delete_cookie(
        "access_token"
    )

    response.delete_cookie(
        "refresh_token"
    )


    return MessageResponse(
        message="Logged out successfully"
    )