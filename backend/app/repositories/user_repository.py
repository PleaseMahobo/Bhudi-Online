from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """
    Repository responsible only for User persistence.
    """

    def __init__(self, session: Session) -> None:
        super().__init__(session, User)

    # ---------------------------------------------------------
    # Queries
    # ---------------------------------------------------------

    def get_by_id(
        self,
        user_id: UUID,
    ) -> User | None:
        return self.session.get(User, user_id)

    def get_by_email(
        self,
        email: str,
    ) -> User | None:
        return self.session.scalar(
            select(User).where(User.email == email)
        )

    def exists_by_email(
        self,
        email: str,
    ) -> bool:
        return self.get_by_email(email) is not None