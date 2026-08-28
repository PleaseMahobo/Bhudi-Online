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
    """Resolve a Bhudi user from a Supabase access token or legacy Bhudi JWT."""
    # Supabase tokens are JWTs, but they do not carry Bhudi's legacy JWT
    # claims. Resolve them first so the legacy decoder cannot reject a valid
    # Supabase token before the Supabase identity fallback is attempted.
    try:
        return resolve_supabase_user(db, token)
    except SupabaseIdentityError:
        pass

    # Preserve compatibility with existing Bhudi-issued JWT sessions.
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


def _normalize_role(name: str | None) -> str:
    if not name:
        return ""
    return (
        str(name)
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
        .replace("__", "_")
    )


_ADMIN_ROLES_FOR_TENANT = frozenset(
    {
        "admin",
        "super_admin",
        "system_admin",
        "enterprise_admin",
        "msp_admin",
        "operator",
        "administrator",
    }
)


def _user_looks_admin(user) -> bool:
    role = _normalize_role(getattr(user, "role", None))
    if role in _ADMIN_ROLES_FOR_TENANT:
        return True
    try:
        for ur in getattr(user, "user_roles", None) or []:
            rname = getattr(getattr(ur, "role", None), "name", None) or getattr(ur, "name", None)
            if _normalize_role(rname) in _ADMIN_ROLES_FOR_TENANT:
                return True
    except Exception:
        pass
    return False


def ensure_user_has_tenant(user, db: Session):
    """If tenant_id is null, create and attach a personal tenant (bootstrap admins).

    Bootstrap historically created security@ / BHUDI_ADMIN without a tenant.
    Enrollment, billing entitlement, and agent download all require tenant_id.
    """
    if get_user_tenant_id(user) is not None:
        return user

    from app.models.tenant import Tenant

    email = (getattr(user, "email", None) or "platform").strip()
    label = email.split("@", 1)[0] if email else "platform"
    tenant_name = f"{label} workspace".strip() or "Bhudi Admin Workspace"

    tenant = Tenant(name=tenant_name[:200])
    db.add(tenant)
    db.flush()
    user.tenant_id = tenant.id
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise authorization_error("Could not provision tenant for account")
    return user


def require_tenant_user(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if get_user_tenant_id(user) is None:
        # Auto-heal platform admins created by bootstrap without a tenant.
        if _user_looks_admin(user):
            user = ensure_user_has_tenant(user, db)
        else:
            raise authorization_error("Tenant association required")
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
    "ensure_user_has_tenant", "verify_resource_owner", "get_security_context",
    "current_user", "current_admin", "current_tenant_user", "is_authenticated",
]
