from __future__ import annotations

from uuid import UUID

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
from app.core.supabase_auth import get_supabase_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    MfaLoginRequest,
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

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
ACCESS_COOKIE_MAX_AGE = 60 * 15
REFRESH_COOKIE_MAX_AGE = 60 * 60 * 24 * 30
COOKIE_SECURE = getattr(settings, "COOKIE_SECURE", True)
COOKIE_SAMESITE = getattr(settings, "COOKIE_SAMESITE", "lax")
COOKIE_DOMAIN = getattr(settings, "COOKIE_DOMAIN", None)


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(key=ACCESS_COOKIE, value=access_token, httponly=True, secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE, domain=COOKIE_DOMAIN, path="/", max_age=ACCESS_COOKIE_MAX_AGE)
    response.set_cookie(key=REFRESH_COOKIE, value=refresh_token, httponly=True, secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE, domain=COOKIE_DOMAIN, path="/", max_age=REFRESH_COOKIE_MAX_AGE)


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(key=ACCESS_COOKIE, domain=COOKIE_DOMAIN, path="/")
    response.delete_cookie(key=REFRESH_COOKIE, domain=COOKIE_DOMAIN, path="/")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    return AuthService(db).register(
        email=request.email,
        password=request.password,
        first_name=request.first_name,
        last_name=request.last_name,
        company=request.company,
    )


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(
    request: MfaLoginRequest,
    response: Response,
    http_request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_supabase_user),
):
    """Promote a verified Supabase session into a Bhudi session after MFA.

    Supabase is the sole password authority. This endpoint deliberately does
    not accept or verify a second Bhudi password hash. The Supabase access
    token proves password authentication; Bhudi then enforces its local MFA
    policy before issuing the application session cookies.
    """
    service = AuthService(db)
    if bool(getattr(user, "mfa_enabled", False)):
        code = (request.mfa_code or "").strip()
        if not code:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="mfa_required")
        try:
            from app.services.mfa_service import MfaService
            if not MfaService(db).verify_code(user, code):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authenticator code")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"MFA verification unavailable: {exc}") from exc

    ip_address = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("user-agent")
    device_name = http_request.headers.get("x-device-name")
    tokens = service.login(user, ip_address=ip_address, user_agent=user_agent, device_name=device_name)
    set_auth_cookies(response, access_token=tokens["access_token"], refresh_token=tokens["refresh_token"])
    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def refresh(request: Request, response: Response, body: RefreshTokenRequest | None = Body(default=None), db: Session = Depends(get_db)):
    service = AuthService(db)
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    if refresh_token is None and body is not None:
        refresh_token = body.refresh_token
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing", headers={"WWW-Authenticate": "Bearer"})
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    device_name = request.headers.get("x-device-name")
    tokens = service.refresh_access_token(
        refresh_token,
        ip_address=ip_address,
        user_agent=user_agent,
        device_name=device_name,
    )
    set_auth_cookies(response, access_token=tokens["access_token"], refresh_token=tokens["refresh_token"])
    return TokenResponse(**tokens)


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    service = AuthService(db)
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    if refresh_token:
        service.logout(refresh_token)
    clear_auth_cookies(response)
    return MessageResponse(message="Logged out successfully")


@router.post("/logout-all", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def logout_all(response: Response, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    revoked = AuthService(db).logout_all(current_user)
    clear_auth_cookies(response)
    return MessageResponse(message=f"Logged out from {revoked} active session(s).")


@router.post("/sessions/{session_id}/revoke", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def revoke_session(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    revoked = AuthService(db).revoke_session(current_user, session_id=session_id)
    if revoked == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return MessageResponse(message=f"Revoked {revoked} token(s) for the specified session.")


@router.get("/sessions", status_code=status.HTTP_200_OK)
def active_sessions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AuthService(db).get_active_sessions(current_user)


@router.post("/passkeys/register", status_code=status.HTTP_200_OK)
def register_passkey(payload: dict[str, object], current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.passkey_service import PasskeyService
    service = PasskeyService(db)
    credential_id = str(payload.get("credential_id", ""))
    credential_data = payload.get("credential_data", {})
    registered = service.complete_registration(current_user, credential_id, credential_data if isinstance(credential_data, dict) else {})
    return {"registered": registered, "credential_id": credential_id}


@router.post("/sso/providers", status_code=status.HTTP_200_OK)
def create_sso_provider(payload: dict[str, object], current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.sso_service import SsoService
    service = SsoService(db)
    provider = service.create_provider(str(payload.get("name", "")), str(payload.get("provider_type", "")), payload.get("config", {}) if isinstance(payload.get("config", {}), dict) else {})
    return {"name": provider.name, "provider_type": provider.provider_type, "enabled": provider.enabled, "config": provider.config}


@router.get("/sso/providers", status_code=status.HTTP_200_OK)
def list_sso_providers(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.sso_service import SsoService
    service = SsoService(db)
    return {"providers": [{"name": provider.name, "provider_type": provider.provider_type, "enabled": provider.enabled, "config": provider.config} for provider in service.get_enabled_providers()]}


@router.post("/secrets", status_code=status.HTTP_200_OK)
def store_secret(payload: dict[str, object], current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.secrets_service import SecretsService
    service = SecretsService(db)
    entry = service.store_secret(str(payload.get("name", "")), str(payload.get("value", "")), category=str(payload.get("category", "")) or None)
    return {"name": entry.name, "value": entry.value, "category": entry.category}


@router.get("/secrets/{name}", status_code=status.HTTP_200_OK)
def get_secret(name: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.secrets_service import SecretsService
    service = SecretsService(db)
    value = service.get_secret(name)
    if value is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")
    return {"name": name, "value": value}


__all__ = ["router"]
