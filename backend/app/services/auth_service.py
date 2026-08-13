from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from ipaddress import ip_address as ipaddress_ip

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.jwt import (
    create_access_token,
    create_refresh_token,
    get_refresh_token_details,
    verify_refresh_token,
)
from app.core.security import (
    hash_password,
    hash_refresh_token,
    validate_password,
    verify_and_upgrade_password,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository


class AuthService:
    """Enterprise authentication: register, login, refresh rotation, logout."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)

    def register(
        self,
        *,
        email: str,
        password: str,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> User:
        email = self._normalize_email(email)
        if self.users.get_by_email(email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
        self._validate_password(password)
        password_hash = hash_password(password)
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
        return self.users.get_by_email(email) or user

    def authenticate(self, email: str, password: str) -> User:
        email = self._normalize_email(email)
        user = self.users.get_by_email(email)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        self._ensure_active_user(user)
        password_valid, upgraded_hash = verify_and_upgrade_password(password, user.password_hash)
        if not password_valid:
            self._record_failed_login(user)
            try:
                self.users.increment_failed_login_attempts(user)
            except Exception:
                pass
            self.db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        if upgraded_hash is not None:
            user.password_hash = upgraded_hash
        self._update_successful_login(user)
        try:
            self.users.reset_failed_login_attempts(user)
        except Exception:
            pass
        self.db.commit()
        return user

    def login(
        self,
        user: User,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_name: str | None = None,
    ) -> dict[str, Any]:
        session_id = uuid.uuid4()
        family = uuid.uuid4()
        access_token = create_access_token(subject=str(user.id))
        refresh_token = create_refresh_token(
            subject=str(user.id),
            session_id=str(session_id),
            token_family=str(family),
            generation=1,
        )
        refresh_details = get_refresh_token_details(refresh_token)
        refresh_record = RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            jwt_id=refresh_details["jti"],
            session_id=session_id,
            token_family=str(family),
            generation=1,
            expires_at=refresh_details["expires_at"],
            ip_address=ip_address,
            user_agent=user_agent,
            device_name=device_name,
        )
        self.refresh_tokens.create(refresh_record)
        self.db.commit()
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
                "active": user.active,
            },
            "session_id": session_id,
            "token_family": family,
        }

    def refresh_access_token(
        self,
        refresh_token: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_name: str | None = None,
    ) -> dict[str, Any]:
        verify_refresh_token(refresh_token)
        token_hash = hash_refresh_token(refresh_token)
        current_token = self.refresh_tokens.get_by_token_hash(token_hash)
        if current_token is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not recognized")
        if getattr(current_token, "revoked", False):
            try:
                self.refresh_tokens.revoke_family(current_token.token_family, reason="refresh_token_replay")
                self.db.commit()
            except Exception:
                pass
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token replay detected")
        if getattr(current_token, "is_expired", False):
            try:
                current_token.revoke("refresh_token_expired")
                self.db.commit()
            except Exception:
                pass
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

        access_token = create_access_token(subject=str(current_token.user_id))
        new_refresh_token = create_refresh_token(
            subject=str(current_token.user_id),
            session_id=str(current_token.session_id),
            token_family=str(current_token.token_family),
            generation=int(getattr(current_token, "generation", 1) or 1) + 1,
        )
        new_claims = get_refresh_token_details(new_refresh_token)
        replacement = RefreshToken(
            user_id=current_token.user_id,
            token_hash=hash_refresh_token(new_refresh_token),
            jwt_id=new_claims["jti"],
            session_id=current_token.session_id,
            token_family=current_token.token_family,
            generation=int(getattr(current_token, "generation", 1) or 1) + 1,
            expires_at=new_claims["expires_at"],
            ip_address=getattr(current_token, "ip_address", None) or ip_address,
            user_agent=getattr(current_token, "user_agent", None) or user_agent,
            device_name=getattr(current_token, "device_name", None) or device_name,
        )
        self.refresh_tokens.create(replacement)
        try:
            if hasattr(current_token, "mark_used"):
                current_token.mark_used()
            if hasattr(current_token, "rotate_to"):
                current_token.rotate_to(replacement)
            elif hasattr(current_token, "revoke"):
                current_token.revoke("rotated")
        except Exception:
            pass
        self.db.commit()
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "session_id": str(current_token.session_id) if current_token.session_id else None,
            "token_family": str(current_token.token_family) if current_token.token_family else None,
        }

    def logout(self, refresh_token: str) -> None:
        token_hash = hash_refresh_token(refresh_token)
        token = self.refresh_tokens.get_by_token_hash(token_hash)
        if token is None:
            return
        if hasattr(token, "revoke"):
            token.revoke("user_logout")
        self.db.commit()

    def logout_all(self, user: User) -> int:
        revoked = self.refresh_tokens.revoke_all_for_user(user.id, reason="logout_all")
        self.db.commit()
        return revoked

    def revoke_session(self, session_id: str, *, reason: str = "session_revoked") -> int:
        revoked = self.refresh_tokens.revoke_session(session_id=session_id, reason=reason)
        self.db.commit()
        return revoked

    def get_active_sessions(self, user: User) -> list:
        return self.refresh_tokens.get_active_sessions(user.id)

    def get_current_user(self, user_id: uuid.UUID) -> User:
        user = self.users.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    @staticmethod
    def _normalize_email(email: str) -> str:
        return (email or "").strip().lower()

    @staticmethod
    def _validate_password(password: str) -> None:
        errors = validate_password(password)
        if errors:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=errors)

    @staticmethod
    def _ensure_active_user(user: User) -> None:
        if not getattr(user, "active", True):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled")
        locked_until = getattr(user, "locked_until", None)
        if locked_until is not None:
            now = datetime.now(timezone.utc)
            until = locked_until if getattr(locked_until, "tzinfo", None) else locked_until.replace(tzinfo=timezone.utc)
            if until > now:
                raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="User account is temporarily locked")

    @staticmethod
    def _update_successful_login(user: User) -> None:
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.now(timezone.utc)

    @staticmethod
    def _record_failed_login(user: User, *, max_attempts: int = 5, lockout_minutes: int = 15) -> None:
        user.failed_login_attempts = int(getattr(user, "failed_login_attempts", 0) or 0) + 1
        if user.failed_login_attempts >= max_attempts:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=lockout_minutes)


__all__ = ["AuthService"]
