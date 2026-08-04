from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.permission import Permission


class PermissionRepository:
    """
    Repository for Permission records.
    """

    def __init__(self, db: Session):
        self.db = db

    def get(self, permission_id: uuid.UUID) -> Permission | None:
        return (
            self.db.query(Permission)
            .filter(Permission.id == permission_id)
            .first()
        )

    def get_by_name(self, name: str) -> Permission | None:
        return (
            self.db.query(Permission)
            .filter(Permission.name == name)
            .first()
        )

    def list(self) -> list[Permission]:
        return (
            self.db.query(Permission)
            .order_by(Permission.name)
            .all()
        )

    def create(self, permission: Permission) -> Permission:
        self.db.add(permission)
        self.db.commit()
        self.db.refresh(permission)
        return permission

    def delete(self, permission: Permission) -> None:
        self.db.delete(permission)
        self.db.commit()