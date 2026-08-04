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
    token_family,
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
from app.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)
from app.repositories.user_repository import (
    UserRepository,
)


class AuthService:
    """
    Enterprise authentication service.

    Responsibilities
    ----------------
    • User registration
    • User authentication
    • Password migration
    • JWT issuance
    • Refresh-token rotation
    • Session management
    • Logout
    • Logout-all
    • Replay attack detection
    """

    def __init__(
        self,
        db: Session,
    ) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)

    # =====================================================
    # Registration
    # =====================================================

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
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        self._validate_password(password)

        password_hash = hash_password(password)
        user = User(
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            password_history=[password_hash],
        )

        self.users.create(user)

        self.db.commit()
        self.db.refresh(user)

        return user

    # =====================================================
    # Authentication
    # =====================================================

    def authenticate(
        self,
        email: str,
        password: str,
    ) -> User:

        email = self._normalize_email(email)

        user = self.users.get_by_email(email)

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        self._ensure_active_user(user)

        password_valid, upgraded_hash = (
            verify_and_upgrade_password(
                password,
                user.password_hash,
            )
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

    # =====================================================
    # Login
    # =====================================================

    def login(
        self,
        user: User,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_name: str | None = None,
    ) -> dict[str, Any]:

        session_id = uuid.uuid4()
        token_family = uuid.uuid4()
        risk_score = self._assess_login_risk(
            ip_address=ip_address,
            user_agent=user_agent,
            device_name=device_name,
            previous_login_at=user.last_login_at,
            current_login_at=datetime.now(timezone.utc),
            password_history=getattr(user, "password_history", None) or [],
        )

        access_token = create_access_token(
            subject=str(user.id),
        )

        refresh_token = create_refresh_token(
            subject=str(user.id),
            session_id=str(session_id),
            token_family=str(token_family),
            generation=1,
        )

        refresh_details = get_refresh_token_details(
            refresh_token
        )

        refresh_record = RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            jwt_id=refresh_details["jti"],
            session_id=session_id,
            token_family=str(token_family),
            generation=1,
            expires_at=refresh_details["expires_at"],
            ip_address=ip_address,
            user_agent=user_agent,
            device_name=device_name,
            trusted_device=bool(device_name and device_name.lower() in {"trusted-device", "known-device", "laptop"}),
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
            "token_family": token_family,
        }

    # =====================================================
    # Refresh Token Rotation
    # =====================================================

    def refresh_access_token(
        self,
        refresh_token: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_name: str | None = None,
    ) -> dict[str, Any]:

        verify_refresh_token(refresh_token)

        token_hash = hash_refresh_token(
            refresh_token
        )

        current_token = (
            self.refresh_tokens.get_by_token_hash(
                token_hash
            )
        )

        if current_token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not recognized",
            )

        if current_token.revoked:

            self.refresh_tokens.revoke_family(
                current_token.token_family,
                reason="refresh_token_replay",
            )

            self.db.commit()

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token replay detected",
            )

        if self._is_session_anomalous(
            current_token,
            ip_address=ip_address,
            user_agent=user_agent,
            device_name=device_name,
        ):
            self.refresh_tokens.revoke_family(
                current_token.token_family,
                reason="session_context_mismatch",
            )

            self.db.commit()

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token replay detected",
            )

        if current_token.is_expired:

            current_token.revoke(
                "refresh_token_expired",
            )

            self.db.commit()

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired",
            )
            
        access_token = create_access_token(
            subject=str(current_token.user_id),
        )

        new_refresh_token = create_refresh_token(
            subject=str(current_token.user_id),
            session_id=current_token.session_id,
            token_family=current_token.token_family,
            generation=current_token.generation + 1,
        )

        new_claims = get_refresh_token_details(
            new_refresh_token,
        )

        replacement = RefreshToken(
            user_id=current_token.user_id,
            token_hash=hash_refresh_token(
                new_refresh_token,
            ),
            jwt_id=new_claims["jti"],
            session_id=current_token.session_id,
            token_family=current_token.token_family,
            generation=current_token.generation + 1,
            expires_at=new_claims["expires_at"],
            ip_address=current_token.ip_address,
            user_agent=current_token.user_agent,
            device_name=current_token.device_name,
            device_id=current_token.device_id,
            operating_system=current_token.operating_system,
            browser=current_token.browser,
            browser_version=current_token.browser_version,
            country=current_token.country,
            city=current_token.city,
            login_method=current_token.login_method,
            trusted_device=current_token.trusted_device,
            risk_score=current_token.risk_score,
        )

        self.refresh_tokens.create(
            replacement,
        )

        current_token.mark_used()

        current_token.rotate_to(
            replacement,
        )

        self.db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user,
            "session_id": session_id,
            "token_family": token_family,
        }

    # =====================================================
    # Logout
    # =====================================================

    def logout(
        self,
        refresh_token: str,
    ) -> None:

        token_hash = hash_refresh_token(
            refresh_token
        )

        token = self.refresh_tokens.get_by_token_hash(
            token_hash,
        )

        if token is None:
            return

        token.revoke(
            "user_logout",
        )

        self.db.commit()

    # =====================================================
    # Logout All Sessions
    # =====================================================

    def logout_all(
        self,
        user: User,
    ) -> int:

        revoked = (
            self.refresh_tokens.revoke_all_for_user(
                user.id,
                reason="logout_all",
            )
        )

        self.db.commit()

        return revoked

    # =====================================================
    # Session Revocation
    # =====================================================

    def revoke_session(
        self,
        session_id: str,
        *,
        reason: str = "session_revoked",
    ) -> int:

        revoked = (
            self.refresh_tokens.revoke_session(
                session_id=session_id,
                reason=reason,
            )
        )

        self.db.commit()

        return revoked

    def revoke_token_family(
        self,
        token_family: str,
        *,
        reason: str = "token_family_revoked",
    ) -> int:

        revoked = (
            self.refresh_tokens.revoke_family(
                token_family=token_family,
                reason=reason,
            )
        )

        self.db.commit()

        return revoked

    def get_active_sessions(
        self,
        user: User,
    ) -> list[RefreshToken]:

        return self.refresh_tokens.get_active_sessions(
            user.id,
        )

    # =====================================================
    # Password Management
    # =====================================================

    def change_password(
        self,
        *,
        user: User,
        current_password: str,
        new_password: str,
    ) -> None:

        valid, _ = verify_and_upgrade_password(
            current_password,
            user.password_hash,
        )

        if not valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect",
            )

        self._validate_password(
            new_password,
        )

        if self._is_password_reused(user, new_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password has already been used recently",
            )

        new_hash = hash_password(new_password)
        history = list(getattr(user, "password_history", []) or [])
        history.insert(0, new_hash)
        history = history[:5]

        user.password_hash = new_hash
        user.password_history = history
        user.password_changed_at = datetime.now(
            timezone.utc,
        )

        self.refresh_tokens.revoke_all_for_user(
            user.id,
            reason="password_changed",
        )

        self.db.commit()

    # =====================================================
    # Lookup Helpers
    # =====================================================

    def get_current_user(
        self,
        user_id: uuid.UUID,
    ) -> User:

        user = self.users.get_by_id(
            user_id,
        )

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return user

    def get_user_by_email(
        self,
        email: str,
    ) -> User | None:

        return self.users.get_by_email(
            self._normalize_email(
                email,
            )
        )

    # =====================================================
    # Maintenance
    # =====================================================

    def purge_expired_refresh_tokens(
        self,
    ) -> int:

        deleted = (
            self.refresh_tokens.delete_expired()
        )

        self.db.commit()

        return deleted
    
    # =====================================================
    # Internal Helpers
    # =====================================================

    @staticmethod
    def _normalize_email(
        email: str,
    ) -> str:

        return email.strip().lower()

    @staticmethod
    def _validate_password(
        password: str,
    ) -> None:

        errors = validate_password(
            password,
        )

        if errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=errors,
            )

    @staticmethod
    def _ensure_active_user(
        user: User,
    ) -> None:

        if not user.active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled",
            )

        if (
            user.locked_until is not None
            and user.locked_until > datetime.now(
                timezone.utc,
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="User account is temporarily locked",
            )

    @staticmethod
    def _update_successful_login(
        user: User,
    ) -> None:

        user.failed_login_attempts = 0
        user.locked_until = None

        user.last_login_at = datetime.now(
            timezone.utc,
        )

    @staticmethod
    def _record_failed_login(
        user: User,
        *,
        max_attempts: int = 5,
        lockout_minutes: int = 15,
    ) -> None:

        user.failed_login_attempts += 1

        if user.failed_login_attempts >= max_attempts:

            user.locked_until = (
                datetime.now(
                    timezone.utc,
                )
                + timedelta(
                    minutes=lockout_minutes,
                )
            )

    @staticmethod
    def _is_password_reused(user: User, new_password: str) -> bool:
        history = getattr(user, "password_history", None) or []
        normalized_candidate = new_password.strip().lower()

        for candidate in history:
            if candidate is None:
                continue
            if isinstance(candidate, str) and candidate.strip().lower() == normalized_candidate:
                return True
            if verify_password(new_password, candidate):
                return True
        return False

    @staticmethod
    def _is_session_anomalous(
        token: RefreshToken,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_name: str | None = None,
    ) -> bool:
        if not token:
            return False

        if ip_address and token.ip_address and ip_address != token.ip_address:
            return True

        if user_agent and token.user_agent and user_agent != token.user_agent:
            return True

        if device_name and token.device_name and device_name != token.device_name:
            return True

        return False

    @staticmethod
    def _assess_login_risk(
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_name: str | None = None,
        previous_login_at: datetime | None = None,
        current_login_at: datetime | None = None,
        password_history: list[str] | None = None,
    ) -> int:
        score = 0

        if ip_address:
            try:
                parsed = ipaddress_ip(ip_address)
                if parsed.is_private:
                    score += 10
                else:
                    score += 20
            except ValueError:
                score += 15

        if user_agent and "bot" in user_agent.lower():
            score += 30

        if device_name:
            score += 5

        if previous_login_at and current_login_at:
            delta_hours = max(0, int((current_login_at - previous_login_at).total_seconds() // 3600))
            if delta_hours < 2:
                score += 25
            elif delta_hours > 24:
                score -= 10

        if password_history:
            score += min(20, len(password_history) * 5)

        return max(0, min(100, score))

    # =====================================================
    # Service Metadata
    # =====================================================

    @staticmethod
    def service_name() -> str:
        return "AuthService"

    @staticmethod
    def version() -> str:
        return "2.0.0-enterprise"

    # =====================================================
    # Health / Maintenance
    # =====================================================

    def health(
        self,
    ) -> dict[str, Any]:

        return {
            "service": self.service_name(),
            "version": self.version(),
            "database": "connected",
        }

    def cleanup(
        self,
    ) -> int:

        deleted = self.refresh_tokens.delete_expired()

        self.db.commit()

        return deleted

    # =====================================================
    # Statistics
    # =====================================================

    def active_session_count(
        self,
        user: User,
    ) -> int:

        return len(
            self.refresh_tokens.get_active_sessions(
                user.id,
            )
        )

    # =====================================================
    # Representation
    # =====================================================

    def __repr__(
        self,
    ) -> str:

        return (
            f"{self.__class__.__name__}("
            f"db={type(self.db).__name__}"
            ")"
        )


__all__ = [
    "AuthService",
]