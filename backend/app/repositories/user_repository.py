from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, load_only

from app.models.user import User
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """Enterprise user repository with schema-tolerant create/lookup."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, User)

    def create(self, user: User) -> User:
        """Insert core columns so trial register works before full migrations."""
        user_id = user.id or uuid4()
        email = (user.email or "").strip().lower()
        password_hash = user.password_hash
        first_name = user.first_name
        last_name = user.last_name
        role = getattr(user, "role", None) or "trial"

        try:
            self.session.execute(
                text(
                    """
                    INSERT INTO users (
                        id, email, password_hash, first_name, last_name,
                        role, active, failed_login_attempts
                    )
                    VALUES (
                        :id, :email, :password_hash, :first_name, :last_name,
                        :role, true, 0
                    )
                    """
                ),
                {
                    "id": str(user_id),
                    "email": email,
                    "password_hash": password_hash,
                    "first_name": first_name,
                    "last_name": last_name,
                    "role": role,
                },
            )
            self.session.flush()
        except Exception:
            self.session.rollback()
            user.id = user_id
            self.session.add(user)
            self.session.flush()

        created = self.get_by_email(email)
        if created is None:
            self.session.add(user)
            self.session.flush()
            self.session.refresh(user)
            return user
        return created

    @staticmethod
    def _core_user_columns():
        return (
            User.id,
            User.email,
            User.password_hash,
            User.first_name,
            User.last_name,
            User.role,
            User.active,
            User.failed_login_attempts,
            User.locked_until,
            User.last_login_at,
            User.password_changed_at,
            User.created_at,
            User.updated_at,
        )

    def get_by_id(self, user_id: UUID) -> User | None:
        return self.session.scalar(
            select(User).options(load_only(*self._core_user_columns())).where(User.id == user_id)
        )

    def get_active_by_id(self, user_id: UUID) -> User | None:
        return self.session.scalar(
            select(User)
            .options(load_only(*self._core_user_columns()))
            .where(User.id == user_id, User.active.is_(True))
        )

    def get_by_email(self, email: str) -> User | None:
        email = (email or "").strip().lower()
        return self.session.scalar(
            select(User)
            .options(load_only(*self._core_user_columns()))
            .where(func.lower(User.email) == email)
        )

    def get_active_by_email(self, email: str) -> User | None:
        email = (email or "").strip().lower()
        return self.session.scalar(
            select(User)
            .options(load_only(*self._core_user_columns()))
            .where(func.lower(User.email) == email, User.active.is_(True))
        )

    def list_users(self, *, limit: int = 100, offset: int = 0) -> list[User]:
        return list(
            self.session.scalars(
                select(User)
                .options(load_only(*self._core_user_columns()))
                .order_by(User.created_at.desc())
                .limit(limit)
                .offset(offset)
            ).all()
        )

    def increment_failed_login_attempts(self, user: User) -> None:
        user.failed_login_attempts = int(user.failed_login_attempts or 0) + 1
        self.session.flush()

    def reset_failed_login_attempts(self, user: User) -> None:
        user.failed_login_attempts = 0
        user.locked_until = None
        self.session.flush()

    def lock_until(self, user: User, until: datetime) -> None:
        user.locked_until = until
        self.session.flush()

    def set_active(self, user: User, active: bool) -> None:
        user.active = active
        self.session.flush()

    def update_last_login(self, user: User) -> None:
        user.last_login_at = func.now()
        self.session.flush()

    def update_password(self, user: User, password_hash: str) -> None:
        user.password_hash = password_hash
        user.password_changed_at = func.now()
        self.session.flush()

    def update_profile(
        self,
        *,
        user: User,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> User:
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        self.session.flush()
        self.session.refresh(user)
        return user

    def set_role(self, user: User, role: str) -> None:
        user.role = role
        self.session.flush()

    def get_by_role(self, role: str) -> list[User]:
        return list(self.session.scalars(select(User).where(User.role == role)).all())

    def delete(self, user: User) -> None:
        self.session.delete(user)
        self.session.flush()

    def count(self) -> int:
        return self.session.scalar(select(func.count()).select_from(User)) or 0

    def count_active(self) -> int:
        return (
            self.session.scalar(
                select(func.count()).select_from(User).where(User.active.is_(True))
            )
            or 0
        )
