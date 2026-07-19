from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    # =====================================================
    # Queries
    # =====================================================

    def get_by_email(
        self,
        email: str,
    ) -> Optional[User]:

        return (
            self.db.query(User)
            .filter(User.email == email)
            .first()
        )

    def get_by_id(
        self,
        user_id: UUID,
    ) -> Optional[User]:

        return (
            self.db.query(User)
            .filter(User.id == user_id)
            .first()
        )

    def exists_by_email(
        self,
        email: str,
    ) -> bool:

        return (
            self.get_by_email(email)
            is not None
        )

    # =====================================================
    # Persistence
    # =====================================================

    def create(
        self,
        user: User,
    ) -> User:

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user

    def update(
        self,
        user: User,
    ) -> User:

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user

    def save(
        self,
        user: User,
    ) -> User:

        return self.update(user)

    def delete(
        self,
        user: User,
    ) -> None:

        self.db.delete(user)
        self.db.commit()