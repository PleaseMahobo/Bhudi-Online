from __future__ import annotations

from typing import Iterable, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.role_repository import RoleRepository
from app.repositories.role_permission_repository import RolePermissionRepository
from app.repositories.permission_repository import PermissionRepository
from app.repositories.user_role_repository import UserRoleRepository


class AuthorizationService:
    """
    Centralized RBAC authorization engine.

    Responsibilities:
    - Resolve user roles
    - Resolve role permissions
    - Check permissions
    - Enforce authorization rules

    API endpoints should never implement RBAC logic directly.
    """

    def __init__(
        self,
        db: Session,
    ):
        self.db = db

        self.role_repository = RoleRepository(db)
        self.role_permission_repository = RolePermissionRepository(db)
        self.permission_repository = PermissionRepository(db)
        self.user_role_repository = UserRoleRepository(db)

    # ==========================================================
    # Role Resolution
    # ==========================================================

    def get_user_roles(
        self,
        user_id: UUID,
    ):
        """
        Return all roles assigned to a user.
        """

        return self.user_role_repository.get_user_roles(
            user_id
        )

    # ==========================================================
    # Permission Resolution
    # ==========================================================

    def get_role_permissions(
        self,
        role_id: UUID,
    ):
        """
        Return permissions assigned to a role.
        """

        return self.role_permission_repository.get_role_permissions(
            role_id
        )

    def get_user_permissions(
        self,
        user_id: UUID,
    ) -> set[str]:
        """
        Resolve all permissions for a user.

        Example output:

        {
            "device.read",
            "device.write",
            "user.manage"
        }
        """

        permissions: set[str] = set()

        roles = self.get_user_roles(user_id)

        for role in roles:

            role_permissions = (
                self.get_role_permissions(
                    role.id
                )
            )

            for role_permission in role_permissions:

                permission = (
                    self.permission_repository.get_by_id(
                        role_permission.permission_id
                    )
                )

                if permission:
                    permissions.add(
                        permission.name
                    )

        return permissions

    # ==========================================================
    # Permission Checks
    # ==========================================================

    def has_permission(
        self,
        user_id: UUID,
        permission_name: str,
    ) -> bool:
        """
        Check whether a user has a permission.
        """

        permissions = (
            self.get_user_permissions(
                user_id
            )
        )

        return permission_name in permissions

    def require_permission(
        self,
        user_id: UUID,
        permission_name: str,
    ) -> None:
        """
        Raise HTTP 403 if permission missing.
        """

        if not self.has_permission(
            user_id,
            permission_name,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Missing permission: "
                    f"{permission_name}"
                ),
            )
            
        # ==========================================================
    # Role Checks
    # ==========================================================

    def has_role(
        self,
        user_id: UUID,
        role_name: str,
    ) -> bool:
        """
        Check whether a user has a specific role.
        """

        roles = self.get_user_roles(user_id)

        return any(
            role.name == role_name
            for role in roles
        )

    def require_role(
        self,
        user_id: UUID,
        role_name: str,
    ) -> None:
        """
        Require a user to have a role.
        """

        if not self.has_role(
            user_id,
            role_name,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Missing required role: "
                    f"{role_name}"
                ),
            )


    # ==========================================================
    # Administrative Access
    # ==========================================================

    def is_admin(
        self,
        user_id: UUID,
    ) -> bool:
        """
        Determine whether user has administrative access.

        Supported roles:
        - admin
        - super_admin
        """

        admin_roles = {
            "admin",
            "super_admin",
        }

        roles = self.get_user_roles(
            user_id
        )

        return any(
            role.name in admin_roles
            for role in roles
        )


    def require_admin(
        self,
        user_id: UUID,
    ) -> None:
        """
        Require administrator privileges.
        """

        if not self.is_admin(
            user_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrator privileges required",
            )


    # ==========================================================
    # Permission Groups
    # ==========================================================

    def has_any_permission(
        self,
        user_id: UUID,
        permissions: Iterable[str],
    ) -> bool:
        """
        Check if user has at least one permission.
        """

        user_permissions = (
            self.get_user_permissions(
                user_id
            )
        )

        return any(
            permission in user_permissions
            for permission in permissions
        )


    def require_any_permission(
        self,
        user_id: UUID,
        permissions: Iterable[str],
    ) -> None:
        """
        Require at least one permission.
        """

        if not self.has_any_permission(
            user_id,
            permissions,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )


    def has_all_permissions(
        self,
        user_id: UUID,
        permissions: Iterable[str],
    ) -> bool:
        """
        Check if user has every supplied permission.
        """

        user_permissions = (
            self.get_user_permissions(
                user_id
            )
        )

        return all(
            permission in user_permissions
            for permission in permissions
        )


    def require_all_permissions(
        self,
        user_id: UUID,
        permissions: Iterable[str],
    ) -> None:
        """
        Require all permissions.
        """

        if not self.has_all_permissions(
            user_id,
            permissions,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing required permissions",
            )