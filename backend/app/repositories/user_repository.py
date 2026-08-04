from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """
    Enterprise User Repository.

    Responsibilities
    ----------------
    • User persistence
    • User lookups
    • User lifecycle operations
    • Account status management
    • Login security state management

    Authentication logic never belongs here.
    JWT creation never belongs here.
    Password hashing never belongs here.
    """

    def __init__(
        self,
        session: Session,
    ) -> None:

        super().__init__(
            session,
            User,
        )


    # ==========================================================
    # CREATE
    # ==========================================================

    def create(
        self,
        user: User,
    ) -> User:

        self.session.add(user)

        self.session.flush()

        self.session.refresh(user)

        return user


    # ==========================================================
    # LOOKUPS
    # ==========================================================

    def get_by_id(
        self,
        user_id: UUID,
    ) -> User | None:

        return self.session.get(
            User,
            user_id,
        )


    def get_active_by_id(
        self,
        user_id: UUID,
    ) -> User | None:

        return self.session.scalar(
            select(User).where(
                User.id == user_id,
                User.active.is_(True),
            )
        )


    def get_by_email(
        self,
        email: str,
    ) -> User | None:

        return self.session.scalar(
            select(User).where(
                func.lower(User.email)
                == email.lower().strip()
            )
        )


    def exists_by_email(
        self,
        email: str,
    ) -> bool:

        return (
            self.get_by_email(email)
            is not None
        )


    def get_active_by_email(
        self,
        email: str,
    ) -> User | None:

        return self.session.scalar(
            select(User).where(
                func.lower(User.email)
                == email.lower().strip(),
                User.active.is_(True),
            )
        )


    # ==========================================================
    # STATUS
    # ==========================================================

    def activate(
        self,
        user: User,
    ) -> None:

        user.active = True

        self.session.flush()


    def deactivate(
        self,
        user: User,
    ) -> None:

        user.active = False

        self.session.flush()


    # ==========================================================
    # LOGIN SECURITY
    # ==========================================================

    def increment_failed_login_attempts(
        self,
        user: User,
    ) -> None:

        user.failed_login_attempts += 1

        self.session.flush()


    def reset_failed_login_attempts(
        self,
        user: User,
    ) -> None:

        user.failed_login_attempts = 0

        self.session.flush()


    def lock_account(
        self,
        user: User,
        until: datetime,
    ) -> None:

        user.locked_until = until

        self.session.flush()


    def unlock_account(
        self,
        user: User,
    ) -> None:

        user.locked_until = None

        user.failed_login_attempts = 0

        self.session.flush()


    def update_last_login(
        self,
        user: User,
    ) -> None:

        user.last_login_at = func.now()

        self.session.flush()


    # ==========================================================
    # PASSWORD
    # ==========================================================

    def update_password(
        self,
        user: User,
        password_hash: str,
    ) -> None:

        user.password_hash = password_hash

        user.password_changed_at = func.now()

        self.session.flush()


    # ==========================================================
    # PROFILE
    # ==========================================================

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


    # ==========================================================
    # ROLE
    # ==========================================================

    def set_role(
        self,
        user: User,
        role: str,
    ) -> None:

        user.role = role

        self.session.flush()


    def get_by_role(
        self,
        role: str,
    ) -> list[User]:

        return list(
            self.session.scalars(
                select(User).where(
                    User.role == role
                )
            ).all()
        )


    # ==========================================================
    # DELETE
    # ==========================================================

    def delete(
        self,
        user: User,
    ) -> None:

        self.session.delete(user)

        self.session.flush()


    # ==========================================================
    # METRICS
    # ==========================================================

    def count(self) -> int:

        return (
            self.session.scalar(
                select(func.count())
                .select_from(User)
            )
            or 0
        )


    def count_active(self) -> int:

        return (
            self.session.scalar(
                select(func.count())
                .select_from(User)
                .where(
                    User.active.is_(True)
                )
            )
            or 0
        )
