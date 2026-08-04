from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    Body,
    status,
)
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

# ==========================================================
# Cookie Configuration
# ==========================================================

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"

ACCESS_COOKIE_MAX_AGE = 60 * 15
REFRESH_COOKIE_MAX_AGE = 60 * 60 * 24 * 30

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

COOKIE_DOMAIN = getattr(
    settings,
    "COOKIE_DOMAIN",
    None,
)


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
) -> None:
    """
    Store authentication tokens in secure HttpOnly cookies.
    """

    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN,
        path="/",
        max_age=ACCESS_COOKIE_MAX_AGE,
    )

    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN,
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
        key=ACCESS_COOKIE,
        domain=COOKIE_DOMAIN,
        path="/",
    )

    response.delete_cookie(
        key=REFRESH_COOKIE,
        domain=COOKIE_DOMAIN,
        path="/",
    )


# ==========================================================
# Registration
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
    service = AuthService(db)

    return service.register(
        email=request.email,
        password=request.password,
        first_name=request.first_name,
        last_name=request.last_name,
    )
    
# ==========================================================
# Login
# ==========================================================


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
def login(
    request: LoginRequest,
    response: Response,
    http_request: Request,
    db: Session = Depends(get_db),
):
    service = AuthService(db)

    user = service.authenticate(
        request.email,
        request.password,
    )

    ip_address = (
        http_request.client.host
        if http_request.client
        else None
    )

    user_agent = http_request.headers.get(
        "user-agent"
    )

    device_name = http_request.headers.get(
        "x-device-name"
    )

    tokens = service.login(
        user,
        ip_address=ip_address,
        user_agent=user_agent,
        device_name=device_name,
    )

    set_auth_cookies(
        response=response,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
    )

    return TokenResponse(**tokens)


# ==========================================================
# Refresh Token Rotation
# ==========================================================


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
def refresh(
    request: Request,
    response: Response,
    body: RefreshTokenRequest | None = Body(default=None),
    db: Session = Depends(get_db),
):
    service = AuthService(db)

    refresh_token = request.cookies.get(
        REFRESH_COOKIE
    )

    if refresh_token is None and body is not None:
        refresh_token = body.refresh_token

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    tokens = service.refresh_access_token(
        refresh_token
    )

    set_auth_cookies(
        response=response,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
    )

    return TokenResponse(**tokens)

# ==========================================================
# Current User
# ==========================================================


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
def me(
    current_user: User = Depends(
        get_current_user,
    ),
):
    return current_user


# ==========================================================
# Logout
# ==========================================================


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    service = AuthService(db)

    refresh_token = request.cookies.get(
        REFRESH_COOKIE,
    )

    if refresh_token:
        service.logout(refresh_token)

    clear_auth_cookies(response)

    return MessageResponse(
        message="Logged out successfully",
    )


# ==========================================================
# Logout All Sessions
# ==========================================================


@router.post(
    "/logout-all",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
def logout_all(
    response: Response,
    current_user: User = Depends(
        get_current_user,
    ),
    db: Session = Depends(get_db),
):
    service = AuthService(db)

    revoked = service.logout_all(
        current_user,
    )

    clear_auth_cookies(response)

    return MessageResponse(
        message=(
            f"Logged out from {revoked} active "
            "session(s)."
        ),
    )
    
# ==========================================================
# Revoke Current Session
# ==========================================================


@router.post(
    "/sessions/{session_id}/revoke",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AuthService(db)

    revoked = service.revoke_session(
        session_id=session_id,
    )

    return MessageResponse(
        message=(
            f"Revoked {revoked} token(s) "
            "for the specified session."
        ),
    )


# ==========================================================
# Active Sessions
# ==========================================================


@router.get(
    "/sessions",
    status_code=status.HTTP_200_OK,
)
def active_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AuthService(db)

    return service.get_active_sessions(
        current_user,
    )


# ==========================================================
# Module Public API
# ==========================================================

__all__ = [
    "router",
]