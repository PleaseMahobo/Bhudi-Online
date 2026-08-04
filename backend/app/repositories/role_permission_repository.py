from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.role_permission import RolePermission


class RolePermissionRepository:
    """
    Repository for Role ↔ Permission assignments.

    Responsibilities:
    - Create role permission mappings
    - Remove mappings
    - Query permissions assigned to roles
    - Check if a role has a specific permission

    Authorization logic does NOT belong here.
    That will live inside AuthorizationService.
    """

    def __init__(self, db: Session):
        self.db = db

    # ==========================================================
    # Create
    # ==========================================================

    def assign_permission(
        self,
        role_id: UUID,
        permission_id: UUID,
    ) -> RolePermission:
        """
        Assign a permission to a role.
        """

        role_permission = RolePermission(
            role_id=role_id,
            permission_id=permission_id,
        )

        self.db.add(role_permission)
        self.db.commit()
        self.db.refresh(role_permission)

        return role_permission

    # ==========================================================
    # Delete
    # ==========================================================

    def remove_permission(
        self,
        role_id: UUID,
        permission_id: UUID,
    ) -> bool:
        """
        Remove a permission from a role.
        """

        mapping = (
            self.db.query(RolePermission)
            .filter(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == permission_id,
            )
            .first()
        )

        if not mapping:
            return False

        self.db.delete(mapping)
        self.db.commit()

        return True

    # ==========================================================
    # Queries
    # ==========================================================

    def get_by_id(
        self,
        role_permission_id: UUID,
    ) -> Optional[RolePermission]:
        """
        Retrieve mapping by primary key.
        """

        return (
            self.db.query(RolePermission)
            .filter(
                RolePermission.id == role_permission_id
            )
            .first()
        )

    def get_role_permissions(
        self,
        role_id: UUID,
    ) -> List[RolePermission]:
        """
        Get all permissions assigned to a role.
        """

        return (
            self.db.query(RolePermission)
            .filter(
                RolePermission.role_id == role_id
            )
            .all()
        )

    def exists(
        self,
        role_id: UUID,
        permission_id: UUID,
    ) -> bool:
        """
        Check whether a permission is already assigned.
        """

        return (
            self.db.query(RolePermission)
            .filter(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == permission_id,
            )
            .first()
            is not None
        )

    # ==========================================================
    # Bulk Operations
    # ==========================================================

    def remove_all_role_permissions(
        self,
        role_id: UUID,
    ) -> int:
        """
        Remove all permissions assigned to a role.

        Returns number of deleted rows.
        """

        deleted = (
            self.db.query(RolePermission)
            .filter(
                RolePermission.role_id == role_id
            )
            .delete(
                synchronize_session=False
            )
        )

        self.db.commit()

        return deleted