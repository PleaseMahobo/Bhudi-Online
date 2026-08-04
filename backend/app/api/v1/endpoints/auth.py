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
from app.services.mfa_service import MfaService
from app.services.passkey_service import PasskeyService
from app.services.sso_service import SsoService
from app.services.secrets_service import SecretsService

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
# MFA
# ==========================================================


@router.post(
    "/mfa/setup",
    status_code=status.HTTP_200_OK,
)
def setup_mfa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = MfaService(db)
    secret, otpauth_uri = service.generate_secret(current_user)
    return {
        "enabled": service.is_enabled(current_user),
        "secret": secret,
        "otpauth_uri": otpauth_uri,
    }


@router.post(
    "/mfa/verify",
    status_code=status.HTTP_200_OK,
)
def verify_mfa(
    payload: dict[str, str],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = MfaService(db)
    code = payload.get("code", "")
    enabled = service.enable_totp(current_user, code)
    return {
        "enabled": enabled and service.is_enabled(current_user),
    }


# ==========================================================
# Passkeys
# ==========================================================


@router.post(
    "/passkeys/register",
    status_code=status.HTTP_200_OK,
)
def register_passkey(
    payload: dict[str, object],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = PasskeyService(db)
    credential_id = str(payload.get("credential_id", ""))
    credential_data = payload.get("credential_data", {})
    registered = service.complete_registration(current_user, credential_id, credential_data if isinstance(credential_data, dict) else {})
    return {
        "registered": registered,
        "credential_id": credential_id,
    }


# ==========================================================
# SSO Providers
# ==========================================================


@router.post(
    "/sso/providers",
    status_code=status.HTTP_200_OK,
)
def create_sso_provider(
    payload: dict[str, object],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = SsoService(db)
    provider = service.create_provider(
        str(payload.get("name", "")),
        str(payload.get("provider_type", "")),
        payload.get("config", {}) if isinstance(payload.get("config", {}), dict) else {},
    )
    return {
        "name": provider.name,
        "provider_type": provider.provider_type,
        "enabled": provider.enabled,
        "config": provider.config,
    }


@router.get(
    "/sso/providers",
    status_code=status.HTTP_200_OK,
)
def list_sso_providers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = SsoService(db)
    return {
        "providers": [
            {
                "name": provider.name,
                "provider_type": provider.provider_type,
                "enabled": provider.enabled,
                "config": provider.config,
            }
            for provider in service.get_enabled_providers()
        ]
    }


# ==========================================================
# Secrets
# ==========================================================


@router.post(
    "/secrets",
    status_code=status.HTTP_200_OK,
)
def store_secret(
    payload: dict[str, object],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = SecretsService(db)
    entry = service.store_secret(
        str(payload.get("name", "")),
        str(payload.get("value", "")),
        category=str(payload.get("category", "")) or None,
    )
    return {
        "name": entry.name,
        "value": entry.value,
        "category": entry.category,
    }


@router.get(
    "/secrets/{name}",
    status_code=status.HTTP_200_OK,
)
def get_secret(
    name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = SecretsService(db)
    value = service.get_secret(name)
    if value is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")
    return {
        "name": name,
        "value": value,
    }


# ==========================================================
# Module Public API
# ==========================================================

__all__ = [
    "router",
]