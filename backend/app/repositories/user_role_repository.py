from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.user_role import UserRole
from app.models.role import Role


class UserRoleRepository:
    """
    Repository for user-role assignments.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_roles_for_user(self, user_id: uuid.UUID) -> list[UserRole]:
        return (
            self.db.query(UserRole)
            .filter(UserRole.user_id == user_id)
            .all()
        )
        
    def get_roles(
        self,
        user_id: uuid.UUID,
    ) -> list[Role]:
        """
        Return the Role objects assigned to a user.
        """

        assignments = self.get_roles_for_user(user_id)

        return [
            assignment.role
            for assignment in assignments
            if assignment.role is not None
        ]

    def exists(
        self,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
    ) -> bool:
        """
        Check whether the user already has the role.
        """

        return (
            self.db.query(UserRole)
            .filter(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id,
            )
            .first()
            is not None
        )
    def get_user_roles(
        self,
        user_id: uuid.UUID,
    ) -> list[UserRole]:
        """
        Compatibility wrapper used by AuthorizationService.
        """

        return self.get_roles_for_user(
            user_id,
        )

    def assign_role(
        self,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
    ) -> UserRole:
        assignment = UserRole(
            user_id=user_id,
            role_id=role_id,
        )

        self.db.add(assignment)
        self.db.flush()
        self.db.refresh(assignment)

        return assignment

    def remove_role(
        self,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
    ) -> bool:
        assignment = (
            self.db.query(UserRole)
            .filter(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id,
            )
            .first()
        )

        if assignment is None:
            return False

        self.db.delete(assignment)
        self.db.commit()

        return True

    def clear_roles(
        self,
        user_id: uuid.UUID,
    ) -> None:
        (
            self.db.query(UserRole)
            .filter(UserRole.user_id == user_id)
            .delete()
        )

        self.db.commit()