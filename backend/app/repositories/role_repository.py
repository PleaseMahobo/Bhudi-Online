from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.role import Role


class RoleRepository:
    """
    Repository for Role records.
    """

    def __init__(self, db: Session):
        self.db = db

    def get(self, role_id: uuid.UUID) -> Role | None:
        return (
            self.db.query(Role)
            .filter(Role.id == role_id)
            .first()
        )

    def get_by_name(self, name: str) -> Role | None:
        return (
            self.db.query(Role)
            .filter(Role.name == name)
            .first()
        )

    def list(self) -> list[Role]:
        return (
            self.db.query(Role)
            .order_by(Role.name)
            .all()
        )

    def create(self, role: Role) -> Role:
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        return role

    def update(self, role: Role) -> Role:
        self.db.commit()
        self.db.refresh(role)
        return role

    def delete(self, role: Role) -> None:
        self.db.delete(role)
        self.db.commit()