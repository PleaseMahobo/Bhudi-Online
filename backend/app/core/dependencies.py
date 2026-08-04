from __future__ import annotations

from uuid import UUID
from typing import Callable

from app.services.authorization_service import AuthorizationService
from fastapi import (
    Depends,
    HTTPException,
    Request,
    status,
)
from sqlalchemy.orm import Session

from app.core.jwt import (
    extract_access_token_subject,
)
from app.database.session import get_db
from app.repositories.user_repository import (
    UserRepository,
)


# ==========================================================
# Authentication Exceptions
# ==========================================================


def authentication_error(
    detail: str = "Not authenticated",
) -> HTTPException:
    """
    Standard authentication exception.
    """

    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )


def authorization_error(
    detail: str = "Insufficient permissions",
) -> HTTPException:
    """
    Standard authorization exception.
    """

    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail,
    )


# ==========================================================
# Access Token Extraction
# ==========================================================


def get_access_token(
    request: Request,
) -> str:
    """
    Extract an access token from either:

    • Authorization header
    • HttpOnly cookie
    """

    authorization = request.headers.get(
        "Authorization"
    )

    if authorization:

        scheme, _, token = (
            authorization.partition(" ")
        )

        if (
            scheme.lower() == "bearer"
            and token.strip()
        ):
            return token.strip()

    cookie_token = request.cookies.get(
        "access_token"
    )

    if cookie_token:
        return cookie_token

    raise authentication_error(
        "Authentication credentials missing"
    )


# ==========================================================
# Optional Access Token
# ==========================================================


def get_optional_access_token(
    request: Request,
) -> str | None:

    authorization = request.headers.get(
        "Authorization"
    )

    if authorization:

        scheme, _, token = (
            authorization.partition(" ")
        )

        if (
            scheme.lower() == "bearer"
            and token.strip()
        ):
            return token.strip()

    return request.cookies.get(
        "access_token"
    )


# ==========================================================
# Current User Dependency
# ==========================================================


def get_current_user(
    token: str = Depends(
        get_access_token
    ),
    db: Session = Depends(
        get_db
    ),
):
    """
    Resolve the authenticated user.
    """

    try:

        user_id = (
            extract_access_token_subject(
                token
            )
        )

        user_uuid = UUID(
            user_id
        )

    except HTTPException:
        raise

    except Exception:

        raise authentication_error(
            "Invalid authentication credentials"
        )

    repository = UserRepository(
        db
    )

    user = repository.get_by_id(
        user_uuid
    )

    if user is None:

        raise authentication_error(
            "User account not found"
        )

    if not user.active:

        raise authorization_error(
            "User account is disabled"
        )

    return user

# ==========================================================
# Optional User Dependency
# ==========================================================


def get_optional_user(
    token: str | None = Depends(
        get_optional_access_token
    ),
    db: Session = Depends(
        get_db
    ),
):
    """
    Return the authenticated user when credentials
    exist. Missing or invalid credentials return None.
    """

    if token is None:
        return None

    try:

        user_id = extract_access_token_subject(
            token
        )

        user_uuid = UUID(
            user_id
        )

    except Exception:
        return None

    repository = UserRepository(
        db
    )

    user = repository.get_by_id(
        user_uuid
    )

    if user is None:
        return None

    if not user.active:
        return None

    return user


# ==========================================================
# Role Authorization
# ==========================================================


def require_role(
    *allowed_roles: str,
):
    """
    Dependency factory for role-based authorization.
    """

    def role_checker(
        user=Depends(
            get_current_user
        ),
    ):

        role = getattr(
            user,
            "role",
            None,
        )

        if role not in allowed_roles:

            raise authorization_error(
                "Insufficient permissions"
            )

        return user

    return role_checker


# ==========================================================
# Administrator Dependency
# ==========================================================


def require_admin(
    user=Depends(
        require_role(
            "admin",
        )
    ),
):
    """
    Restrict endpoint access to administrators.
    """

    return user


# ==========================================================
# Active User Dependency
# ==========================================================


def require_active_user(
    user=Depends(
        get_current_user
    ),
):
    """
    Explicit active-user dependency.
    """

    if not user.active:

        raise authorization_error(
            "Account disabled"
        )

    return user

# ==========================================================
# Tenant Authorization
# ==========================================================


def get_user_tenant_id(
    user,
):
    """
    Return the tenant identifier associated
    with the authenticated user.
    """

    return getattr(
        user,
        "tenant_id",
        None,
    )


def require_tenant_user(
    user=Depends(
        get_current_user
    ),
):
    """
    Require the authenticated user to belong
    to a tenant.
    """

    if (
        get_user_tenant_id(
            user
        )
        is None
    ):

        raise authorization_error(
            "Tenant association required"
        )

    return user


# ==========================================================
# Permission Authorization
# ==========================================================


def has_permission(
    user,
    permission: str,
) -> bool:
    """
    Determine whether the user possesses
    the requested permission.
    """

    permissions = getattr(
        user,
        "permissions",
        None,
    )

    if not permissions:
        return False

    return permission in permissions


def require_permission(
    permission: str,
):
    """
    Dependency factory for fine-grained
    permission checks.
    """

    def permission_checker(
        user=Depends(
            get_current_user
        ),
    ):

        if not has_permission(
            user,
            permission,
        ):

            raise authorization_error(
                "Permission denied"
            )

        return user

    return permission_checker


# ==========================================================
# Ownership Validation
# ==========================================================


def verify_resource_owner(
    owner_id,
    user,
) -> bool:
    """
    Ensure the authenticated user owns
    the requested resource.
    """

    if str(owner_id) != str(user.id):

        raise authorization_error(
            "Resource access denied"
        )

    return True

# ==========================================================
# Security Context
# ==========================================================


def get_security_context(
    user=Depends(
        get_current_user
    ),
):
    """
    Return a normalized security context for
    downstream services.
    """

    return {
        "user_id": user.id,
        "tenant_id": getattr(
            user,
            "tenant_id",
            None,
        ),
        "role": getattr(
            user,
            "role",
            None,
        ),
        "permissions": getattr(
            user,
            "permissions",
            [],
        ),
    }


# ==========================================================
# Dependency Aliases
# ==========================================================


def current_user(
    user=Depends(
        get_current_user
    ),
):
    return user


def current_admin(
    user=Depends(
        require_admin
    ),
):
    return user


def current_tenant_user(
    user=Depends(
        require_tenant_user
    ),
):
    return user


# ==========================================================
# Authentication State
# ==========================================================


def is_authenticated(
    request: Request,
) -> bool:
    """
    Lightweight authentication check.
    """

    try:

        get_access_token(
            request
        )

        return True

    except HTTPException:

        return False


# ==========================================================
# Public Module API
# ==========================================================

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

# ==========================================================
# RBAC Authorization Dependencies
# ==========================================================


def require_permission(
    permission_name: str,
) -> Callable:
    """
    FastAPI dependency factory.

    Usage:

        Depends(
            require_permission(
                "device.read"
            )
        )
    """

    def permission_checker(
        current_user=Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        authorization_service = AuthorizationService(
            db
        )

        authorization_service.require_permission(
            current_user.id,
            permission_name,
        )

        return current_user

    return permission_checker



def require_role(
    role_name: str,
) -> Callable:
    """
    Require a specific role.

    Usage:

        Depends(
            require_role(
                "admin"
            )
        )
    """

    def role_checker(
        current_user=Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        authorization_service = AuthorizationService(
            db
        )

        authorization_service.require_role(
            current_user.id,
            role_name,
        )

        return current_user

    return role_checker



def require_admin():
    """
    Require administrator privileges.

    Usage:

        Depends(require_admin())
    """

    def admin_checker(
        current_user=Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        authorization_service = AuthorizationService(
            db
        )

        authorization_service.require_admin(
            current_user.id,
        )

        return current_user

    return admin_checker