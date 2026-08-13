from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_and_upgrade_password
from app.models.user import User
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    def _normalize_email(self, email: str) -> str:
        return (email or "").strip().lower()

    def _validate_password(self, password: str) -> None:
        if not password or len(password) < 12:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 12 characters",
            )

    def _ensure_active_user(self, user: User) -> None:
        if not getattr(user, "active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled",
            )
        locked_until = getattr(user, "locked_until", None)
        if locked_until is not None:
            now = datetime.now(timezone.utc)
            until = locked_until
            if until.tzinfo is None:
                until = until.replace(tzinfo=timezone.utc)
            if until > now:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is temporarily locked",
                )

    def register(
        self,
        email: str,
        password: str,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> User:
        email = self._normalize_email(email)

        if self.users.get_by_email(email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        self._validate_password(password)
        password_hash = hash_password(password)

        # Core fields only — enterprise columns may be missing until schema SQL is applied.
        user = User(
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
        )

        try:
            self.users.create(user)
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Registration failed due to database schema. "
                    "Run backend/scripts/ensure_auth_and_metrics_schema.sql "
                    f"in Supabase SQL Editor. ({type(exc).__name__})"
                ),
            ) from exc

        created = self.users.get_by_email(email)
        return created or user

    def authenticate(self, email: str, password: str) -> User:
        email = self._normalize_email(email)
        user = self.users.get_by_email(email)

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        self._ensure_active_user(user)

        password_valid, upgraded_hash = verify_and_upgrade_password(
            password,
            user.password_hash,
        )

        if not password_valid:
            self._record_failed_login(user)
            self.users.increment_failed_login_attempts(user)
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if upgraded_hash is not None:
            user.password_hash = upgraded_hash

        self._update_successful_login(user)
        self.users.reset_failed_login_attempts(user)
        self.db.commit()
        return user

    def _record_failed_login(self, user: User) -> None:
        attempts = int(getattr(user, "failed_login_attempts", 0) or 0) + 1
        user.failed_login_attempts = attempts
        if attempts >= 5:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)

    def _update_successful_login(self, user: User) -> None:
        user.last_login_at = datetime.now(timezone.utc)
        user.failed_login_attempts = 0
        user.locked_until = None
