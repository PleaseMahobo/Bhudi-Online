from __future__ import annotations

from uuid import UUID
from typing import Callable

from app.services.authorization_service import AuthorizationService
from app.services.supabase_identity import SupabaseIdentityError, resolve_supabase_user
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.jwt import extract_access_token_subject
from app.database.session import get_db
from app.repositories.user_repository import UserRepository


def authentication_error(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers={"WWW-Authenticate": "Bearer"})


def authorization_error(detail: str = "Insufficient permissions") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def get_access_token(request: Request) -> str:
    authorization = request.headers.get("Authorization")
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token.strip():
            return token.strip()
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token
    raise authentication_error("Authentication credentials missing")


def get_optional_access_token(request: Request) -> str | None:
    authorization = request.headers.get("Authorization")
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token.strip():
            return token.strip()
    return request.cookies.get("access_token")


def get_current_user(
    token: str = Depends(get_access_token),
    db: Session = Depends(get_db),
):
    """Resolve a Bhudi user from the legacy JWT or a Supabase access token."""
    try:
        user_id = UUID(extract_access_token_subject(token))
        user = UserRepository(db).get_by_id(user_id)
        if user is not None:
            if not user.active:
                raise authorization_error("User account is disabled")
            return user
    except HTTPException:
        raise
    except Exception:
        pass

    try:
        return resolve_supabase_user(db, token)
    except SupabaseIdentityError:
        raise authentication_error("Invalid authentication credentials")


def get_optional_user(
    token: str | None = Depends(get_optional_access_token),
    db: Session = Depends(get_db),
):
    if token is None:
        return None
    try:
        return get_current_user(token, db)
    except Exception:
        return None


def require_role(*allowed_roles: str):
    """Return a FastAPI dependency backed by the canonical AuthorizationService."""
    if not allowed_roles:
        raise ValueError("At least one role is required")

    def role_checker(
        current_user=Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        authz = AuthorizationService(db)
        for role in allowed_roles:
            if authz.has_role(current_user.id, role):
                return current_user
        raise authorization_error("Insufficient permissions")

    return role_checker


def require_admin():
    """Canonical administrator dependency using AuthorizationService."""
    def admin_checker(
        current_user=Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        AuthorizationService(db).require_admin(current_user.id)
        return current_user

    return admin_checker


def require_active_user(user=Depends(get_current_user)):
    if not user.active:
        raise authorization_error("Account disabled")
    return user


def get_user_tenant_id(user):
    return getattr(user, "tenant_id", None)


def require_tenant_user(user=Depends(get_current_user)):
    if get_user_tenant_id(user) is None:
        raise authorization_error("Tenant association required")
    return user


def has_permission(user, permission: str) -> bool:
    return bool(getattr(user, "permissions", None) and permission in user.permissions)


def require_permission(permission: str) -> Callable:
    def permission_checker(
        current_user=Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        AuthorizationService(db).require_permission(current_user.id, permission)
        return current_user

    return permission_checker


def verify_resource_owner(owner_id, user) -> bool:
    if str(owner_id) != str(user.id):
        raise authorization_error("Resource access denied")
    return True


def get_security_context(user=Depends(get_current_user)):
    return {
        "user_id": user.id,
        "tenant_id": getattr(user, "tenant_id", None),
        "role": getattr(user, "role", None),
        "permissions": getattr(user, "permissions", []),
    }


def current_user(user=Depends(get_current_user)):
    return user


def current_admin(user=Depends(require_admin())):
    return user


def current_tenant_user(user=Depends(require_tenant_user)):
    return user


def is_authenticated(request: Request) -> bool:
    try:
        get_access_token(request)
        return True
    except HTTPException:
        return False


__all__ = [
    "authentication_error", "authorization_error", "get_access_token",
    "get_optional_access_token", "get_current_user", "get_optional_user",
    "require_active_user", "require_role", "require_admin", "require_permission",
    "has_permission", "require_tenant_user", "get_user_tenant_id",
    "verify_resource_owner", "get_security_context", "current_user",
    "current_admin", "current_tenant_user", "is_authenticated",
]
