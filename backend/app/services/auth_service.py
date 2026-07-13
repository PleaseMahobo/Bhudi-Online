from __future__ import annotations

import uuid

from jose import JWTError

from app.core.jwt import (
    create_access_token,
    create_refresh_token,
    get_refresh_token_details,
    verify_refresh_token,
)

from app.core.security import (
    hash_password,
    hash_refresh_token,
    verify_password,
)

from app.models.refresh_token import RefreshToken
from app.models.user import User

from app.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, db):
        self.db = db
        self.users = UserRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)

    # =====================================================
    # Internal helpers
    # =====================================================

    def _build_refresh_record(
        self,
        *,
        user: User,
        refresh_token: str,
        token_family: str,
        generation: int = 1,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_name: str | None = None,
    ) -> RefreshToken:

        details = get_refresh_token_details(refresh_token)

        return RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            jwt_id=details["jwt_id"],
            session_id=details["session_id"],
            token_family=token_family,
            generation=generation,
            expires_at=details["expires_at"],
            ip_address=ip_address,
            user_agent=user_agent,
            device_name=device_name,
        )

    def _issue_token_pair(
        self,
        user: User,
    ):

        refresh = create_refresh_token(
            str(user.id),
        )

        access = create_access_token(
            str(user.id),
        )

        family = str(uuid.uuid4())

        refresh_record = self._build_refresh_record(
            user=user,
            refresh_token=refresh,
            token_family=family,
            generation=1,
        )

        self.refresh_tokens.create(refresh_record)

        return {
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "bearer",
            "user": user,
        }

    # =====================================================
    # Register
    # =====================================================

    def register(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
    ) -> User:

        email = email.lower().strip()

        existing = self.users.get_by_email(email)

        if existing:
            raise ValueError("Email already exists")

        user = User(
            email=email,
            password_hash=hash_password(password),
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            role="admin",
            active=True,
        )

        return self.users.create(user)

    # =====================================================
    # Login
    # =====================================================

    def authenticate(
        self,
        email: str,
        password: str,
    ):

        email = email.lower().strip()

        user = self.users.get_by_email(email)

        if user is None:
            return None

        if not user.active:
            return None

        if not verify_password(
            password,
            user.password_hash,
        ):
            return None

        return self._issue_token_pair(user)
    
        # =====================================================
    # Current User
    # =====================================================

    def get_current_user(
        self,
        user_id: str,
    ):

        user = self.users.get_by_id(user_id)

        if user is None:
            return None

        if not user.active:
            return None

        return user
    
    # =====================================================
    # Refresh Token Rotation
    # =====================================================

    def refresh_access_token(
        self,
        refresh_token: str,
    ):

        try:
            verify_refresh_token(refresh_token)

        except JWTError:
            return None

        token_hash = hash_refresh_token(refresh_token)

        stored = self.refresh_tokens.get_by_token_hash(
            token_hash
        )

        if stored is None:
            return None

        if stored.revoked:

            # Reuse detection
            self.refresh_tokens.revoke_token_family(
                stored.token_family,
                reason="refresh_token_reuse",
            )

            return None

        if stored.is_expired:
            return None

        user = self.get_current_user(
            str(stored.user_id)
        )

        if user is None:
            return None

        access = create_access_token(
            str(user.id),
            session_id=stored.session_id,
        )

        refresh = create_refresh_token(
            str(user.id),
            session_id=stored.session_id,
        )

        new_record = self._build_refresh_record(
            user=user,
            refresh_token=refresh,
            token_family=stored.token_family,
            generation=stored.generation + 1,
            ip_address=stored.ip_address,
            user_agent=stored.user_agent,
            device_name=stored.device_name,
        )

        self.refresh_tokens.rotate(
            stored,
            new_record,
        )

        return {
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "bearer",
            "user": user,
        }
    # =====================================================
    # Logout
    # =====================================================

    def logout(
        self,
        refresh_token: str,
    ) -> bool:

        token_hash = hash_refresh_token(
            refresh_token
        )

        token = self.refresh_tokens.get_by_token_hash(
            token_hash
        )

        if token is None:
            return False

        self.refresh_tokens.revoke(
            token,
            reason="logout",
        )

        return True

    # =====================================================
    # Logout All Sessions
    # =====================================================

    def logout_all(
        self,
        user_id: str,
    ) -> bool:

        user = self.get_current_user(user_id)

        if user is None:
            return False

        self.refresh_tokens.revoke_all_for_user(
            user.id,
            reason="logout_all",
        )

        return True