from __future__ import annotations

from typing import Callable
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.jwt import extract_access_token_subject
from app.database.session import get_db
from app.repositories.user_repository import UserRepository
from app.services.authorization_service import AuthorizationService


# ==========================================================
# Authentication / Authorization Exceptions
# ==========================================================


def authentication_error(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def authorization_error(detail: str = "Insufficient permissions") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail,
    )


# ==========================================================
# Access Token Dependencies
# ==========================================================


def get_access_token(request: Request) -> str:
    """Extract a bearer token from the Authorization header or access_token cookie."""
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
    """Return an access token when supplied; otherwise return None."""
    authorization = request.headers.get("Authorization")
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token.strip():
            return token.strip()

    return request.cookies.get("access_token")


# ==========================================================
# Current User Dependencies
# ==========================================================


def get_current_user(
    token: str = Depends(get_access_token),
    db: Session = Depends(get_db),
):
    """Resolve and validate the authenticated active user."""
    try:
        user_id = UUID(extract_access_token_subject(token))
    except HTTPException:
        raise
    except Exception:
        raise authentication_error("Invalid authentication credentials")

    user = UserRepository(db).get_by_id(user_id)
    if user is None:
        raise authentication_error("User account not found")

    if not user.active:
        raise authorization_error("User account is disabled")

    return user


def get_optional_user(
    token: str | None = Depends(get_optional_access_token),
    db: Session = Depends(get_db),
):
    """Resolve an optional authenticated user; invalid/missing credentials return None."""
    if token is None:
        return None

    try:
        user_id = UUID(extract_access_token_subject(token))
    except Exception:
        return None

    user = UserRepository(db).get_by_id(user_id)
    if user is None or not user.active:
        return None

    return user


# ==========================================================
# Canonical RBAC Dependencies
# ==========================================================


def require_permission(permission_name: str) -> Callable:
    """Require a permission through the centralized AuthorizationService."""

    def permission_checker(
        current_user=Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        AuthorizationService(db).require_permission(
            current_user.id,
            permission_name,
        )
        return current_user

    return permission_checker


def require_role(role_name: str) -> Callable:
    """Require a specific role through the centralized AuthorizationService."""

    def role_checker(
        current_user=Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        AuthorizationService(db).require_role(
            current_user.id,
            role_name,
        )
        return current_user

    return role_checker


def require_admin() -> Callable:
    """Require administrator privileges through AuthorizationService."""

    def admin_checker(
        current_user=Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        AuthorizationService(db).require_admin(current_user.id)
        return current_user

    return admin_checker


def require_active_user(user=Depends(get_current_user)):
    """Explicit active-user dependency."""
    if not user.active:
        raise authorization_error("Account disabled")
    return user


def require_tenant_user(user=Depends(get_current_user)):
    """Require the authenticated user to be associated with a tenant."""
    if getattr(user, "tenant_id", None) is None:
        raise authorization_error("Tenant association required")
    return user


def get_user_tenant_id(user):
    return getattr(user, "tenant_id", None)


# ==========================================================
# Compatibility / Security Helpers
# ==========================================================


def has_permission(user, permission: str) -> bool:
    """Compatibility helper; canonical RBAC checks use AuthorizationService."""
    permissions = getattr(user, "permissions", None)
    return bool(permissions and permission in permissions)


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
    "authentication_error",
    "authorization_error",
    "get_access_token",
    "get_optional_access_token",
    "get_current_user",
    "get_optional_user",
    "require_active_user",
    "require_role",
    "require_admin",
    "require_permission",
    "has_permission",
    "require_tenant_user",
    "get_user_tenant_id",
    "verify_resource_owner",
    "get_security_context",
    "current_user",
    "current_admin",
    "current_tenant_user",
    "is_authenticated",
]
