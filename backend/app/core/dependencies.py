from __future__ import annotations

from uuid import UUID

from fastapi import (
    Depends,
    HTTPException,
    Request,
    status,
)

from sqlalchemy.orm import Session

from app.database.session import get_db

from app.core.jwt import (
    extract_access_token_subject,
)

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
    Standard authentication failure.

    Used consistently across
    dependency functions.
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
    Standard authorization failure.
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
    Extract access JWT.

    Supported clients:

    1. API clients

       Authorization:
       Bearer <token>


    2. Browser clients

       HttpOnly cookie:

       access_token


    Refresh tokens are rejected later
    during JWT validation.
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



    cookie_token = (
        request.cookies.get(
            "access_token"
        )
    )


    if cookie_token:

        return cookie_token



    raise authentication_error(
        "Authentication credentials missing"
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
    Resolve the authenticated Bhudi user.

    Validation flow:

        1. Extract bearer token
        2. Validate access JWT
        3. Extract user UUID
        4. Load user
        5. Verify active status
        6. Return User object


    Used by:

        Depends(get_current_user)
    """


    #
    # Validate JWT
    #
    # This ensures:
    #
    # - signature valid
    # - expiry valid
    # - issuer valid
    # - audience valid
    # - token type == access
    #

    try:

        user_id = (
            extract_access_token_subject(
                token
            )
        )


    except HTTPException:

        raise


    except Exception:

        raise authentication_error(
            "Invalid authentication credentials"
        )



    #
    # Convert database identifier
    #

    try:

        user_uuid = UUID(
            user_id
        )


    except ValueError:

        raise authentication_error(
            "Invalid user identifier"
        )



    #
    # Lookup user
    #

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



    #
    # Account status enforcement
    #

    if not user.active:

        raise authorization_error(
            "User account is disabled"
        )



    return user

# ==========================================================
# Optional Authentication
# ==========================================================


def get_optional_access_token(
    request: Request,
) -> str | None:
    """
    Returns an access token if present.
    Never raises authentication errors.
    """

    authorization = request.headers.get("Authorization")

    if authorization:
        scheme, _, token = authorization.partition(" ")

        if scheme.lower() == "bearer" and token.strip():
            return token.strip()

    cookie_token = request.cookies.get("access_token")

    return cookie_token


def get_optional_user(
    token: str | None = Depends(
        get_optional_access_token
    ),
    db: Session = Depends(
        get_db
    ),
):
    """
    Returns the authenticated user when
    credentials exist. Missing token returns None.
    """

    if token is None:
        return None

    try:
        user_id = extract_access_token_subject(token)
        user_uuid = UUID(user_id)
    except Exception:
        return None

    repository = UserRepository(db)
    user = repository.get_by_id(user_uuid)

    if user is None or not user.active:
        return None

    return user



# ==========================================================
# Role Authorization
# ==========================================================


def require_role(
    *allowed_roles: str,
):
    """
    Dependency factory for role checks.

    Example:

        @router.get("/admin")
        def admin_page(
            user=Depends(
                require_role("admin")
            )
        ):
            ...


    Supports future expansion:

        admin

        technician

        analyst
    """


    def role_checker(
        user = Depends(
            get_current_user
        ),
    ):

        user_role = (
            getattr(
                user,
                "role",
                None,
            )
        )


        if user_role not in allowed_roles:

            raise authorization_error(
                "Insufficient permissions"
            )


        return user


    return role_checker



# ==========================================================
# Administrator Dependency
# ==========================================================


def require_admin(
    user = Depends(
        require_role("admin")
    ),
):
    """
    Restricts access to administrators.

    Usage:

        Depends(require_admin)
    """

    return user



# ==========================================================
# Active User Dependency
# ==========================================================


def require_active_user(
    user = Depends(
        get_current_user
    ),
):
    """
    Explicit active-user dependency.

    Useful when endpoint intent
    should be obvious.
    """

    if not user.active:

        raise authorization_error(
            "Account disabled"
        )


    return user

# ==========================================================
# Tenant Authorization Helpers
# ==========================================================


def get_user_tenant_id(
    user,
):
    """
    Returns the tenant identifier
    associated with a user.

    Supports future multi-tenant
    authorization.

    Current Bhudi deployments may
    not yet enforce tenant isolation.
    """

    return getattr(
        user,
        "tenant_id",
        None,
    )



def require_tenant_user(
    user = Depends(
        get_current_user
    ),
):
    """
    Ensures authenticated user
    belongs to a tenant.

    Useful when enabling:

    - MSP isolation
    - customer separation
    - tenant-scoped assets
    """


    tenant_id = get_user_tenant_id(
        user
    )


    if tenant_id is None:

        raise authorization_error(
            "Tenant association required"
        )


    return user



# ==========================================================
# Permission Helpers
# ==========================================================


def has_permission(
    user,
    permission: str,
) -> bool:
    """
    Checks whether a user has
    a specific permission.

    Designed for future RBAC expansion.

    Example:

        devices.delete

        alerts.manage

        users.create
    """

    permissions = getattr(
        user,
        "permissions",
        [],
    )


    if permissions is None:

        return False


    return permission in permissions



def require_permission(
    permission: str,
):
    """
    Dependency factory for
    fine-grained permissions.

    Example:

        Depends(
            require_permission(
                "devices.delete"
            )
        )
    """


    def permission_checker(
        user = Depends(
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
):
    """
    Ensures the current user owns
    a resource.

    Useful for:

    - profiles
    - API keys
    - personal settings
    """


    if str(owner_id) != str(
        user.id
    ):

        raise authorization_error(
            "Resource access denied"
        )


    return True



# ==========================================================
# Security Context Helper
# ==========================================================


def get_security_context(
    user = Depends(
        get_current_user
    ),
):
    """
    Returns a normalized security
    context for services.

    Avoids passing raw User objects
    everywhere.

    Future extension point:

    {
        user_id,
        tenant_id,
        role,
        permissions
    }
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
# Common Dependency Aliases
# ==========================================================


def current_user(
    user = Depends(
        get_current_user
    ),
):
    """
    Alias dependency.

    Allows cleaner endpoint syntax.

    Example:

        user: User = Depends(
            current_user
        )
    """

    return user



def current_admin(
    user = Depends(
        require_admin
    ),
):
    """
    Administrator alias dependency.
    """

    return user



def current_tenant_user(
    user = Depends(
        require_tenant_user
    ),
):
    """
    Tenant-scoped user alias.
    """

    return user



# ==========================================================
# Authentication State Helpers
# ==========================================================


def is_authenticated(
    request: Request,
) -> bool:
    """
    Lightweight authentication check.

    Does not load the database user.

    Useful for:

    - middleware
    - logging
    - request tracing
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

    #
    # Token extraction
    #

    "get_access_token",


    #
    # User dependencies
    #

    "get_current_user",

    "get_optional_user",

    "require_active_user",


    #
    # Role authorization
    #

    "require_role",

    "require_admin",


    #
    # Permission authorization
    #

    "require_permission",

    "has_permission",


    #
    # Tenant authorization
    #

    "require_tenant_user",

    "get_user_tenant_id",


    #
    # Helpers
    #

    "verify_resource_owner",

    "get_security_context",

    "current_user",

    "current_admin",

    "current_tenant_user",
]