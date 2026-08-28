from __future__ import annotations

from typing import Iterable
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.role_repository import RoleRepository
from app.repositories.role_permission_repository import RolePermissionRepository
from app.repositories.permission_repository import PermissionRepository
from app.repositories.user_role_repository import UserRoleRepository


def _normalize_role_name(name: str | None) -> str:
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


class AuthorizationService:
    """Centralized RBAC authorization engine."""

    ADMIN_ROLES = frozenset(
        {
            "admin",
            "super_admin",
            "system_admin",
            "enterprise_admin",
            "msp_admin",
            "administrator",
        }
    )

    def __init__(self, db: Session):
        self.db = db
        self.role_repository = RoleRepository(db)
        self.role_permission_repository = RolePermissionRepository(db)
        self.permission_repository = PermissionRepository(db)
        self.user_role_repository = UserRoleRepository(db)

    def get_user_roles(self, user_id: UUID):
        """Return Role entities, not UserRole assignment rows."""
        return self.user_role_repository.get_roles(user_id)

    def get_role_permissions(self, role_id: UUID):
        return self.role_permission_repository.get_role_permissions(role_id)

    def get_user_permissions(self, user_id: UUID) -> set[str]:
        permissions: set[str] = set()
        for role in self.get_user_roles(user_id):
            for role_permission in self.get_role_permissions(role.id):
                permission = self.permission_repository.get_by_id(role_permission.permission_id)
                if permission:
                    permissions.add(permission.name)
        return permissions

    def has_permission(self, user_id: UUID, permission_name: str) -> bool:
        return permission_name in self.get_user_permissions(user_id)

    def require_permission(self, user_id: UUID, permission_name: str) -> None:
        if not self.has_permission(user_id, permission_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission_name}",
            )

    def has_role(self, user_id: UUID, role_name: str) -> bool:
        target = _normalize_role_name(role_name)
        return any(_normalize_role_name(role.name) == target for role in self.get_user_roles(user_id))

    def require_role(self, user_id: UUID, role_name: str) -> None:
        if not self.has_role(user_id, role_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required role: {role_name}",
            )

    def is_admin(self, user_id: UUID) -> bool:
        # System Admin / Enterprise Admin are production platform operator roles.
        return any(
            _normalize_role_name(role.name) in self.ADMIN_ROLES
            for role in self.get_user_roles(user_id)
        )

    def require_admin(self, user_id: UUID) -> None:
        if not self.is_admin(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrator privileges required",
            )

    def has_any_permission(self, user_id: UUID, permissions: Iterable[str]) -> bool:
        user_permissions = self.get_user_permissions(user_id)
        return any(permission in user_permissions for permission in permissions)

    def require_any_permission(self, user_id: UUID, permissions: Iterable[str]) -> None:
        if not self.has_any_permission(user_id, permissions):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    def has_all_permissions(self, user_id: UUID, permissions: Iterable[str]) -> bool:
        user_permissions = self.get_user_permissions(user_id)
        return all(permission in user_permissions for permission in permissions)

    def require_all_permissions(self, user_id: UUID, permissions: Iterable[str]) -> None:
        if not self.has_all_permissions(user_id, permissions):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing required permissions")
