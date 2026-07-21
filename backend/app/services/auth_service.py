from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.jwt import (
    create_access_token,
    create_refresh_token,
    rotate_refresh_token,
    verify_refresh_token,
    get_refresh_token_details,
)

from app.core.security import (
    hash_password,
    verify_password,
    hash_refresh_token,
)

from app.models.user import User
from app.models.refresh_token import RefreshToken

from app.repositories.user_repository import UserRepository
from app.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)


class AuthService:
    """
    Enterprise authentication service.

    Responsibilities
    ----------------
    • User registration
    • Authentication
    • Login
    • Refresh token rotation
    • Replay detection
    • Logout
    • Logout-all
    """

    def __init__(self, db: Session):

        self.db = db

        self.user_repository = UserRepository(db)

        self.refresh_repository = RefreshTokenRepository(db)

    # =====================================================
    # Registration
    # =====================================================

    def register(
        self,
        email: str,
        password: str,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> User:

        email = email.lower().strip()

        existing = self.user_repository.get_by_email(email)

        if existing:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is already registered",
            )

        user = User(

            id=uuid.uuid4(),

            email=email,

            password_hash=hash_password(password),

            first_name=first_name,

            last_name=last_name,

            role="user",

            active=True,
        )

        try:

            self.user_repository.create(user)

            self.db.commit()

            self.db.refresh(user)

            return user

        except Exception:

            self.db.rollback()

            raise

    # =====================================================
    # Authentication
    # =====================================================

    def authenticate(
        self,
        email: str,
        password: str,
    ) -> User:

        user = self.user_repository.get_by_email(
            email.lower().strip()
        )

        if user is None:

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not user.active:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account disabled",
            )

        if not verify_password(
            password,
            user.password_hash,
        ):

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

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
    ) -> dict:

        #
        # First login in a new session
        #

        refresh_token = create_refresh_token(
            subject=str(user.id),
        )

        refresh_details = get_refresh_token_details(
            refresh_token
        )

        access_token = create_access_token(
            subject=str(user.id),
        )

        token_record = RefreshToken(

            id=uuid.uuid4(),

            user_id=user.id,

            token_hash=hash_refresh_token(
                refresh_token
            ),

            jwt_id=refresh_details["jwt_id"],

            session_id=refresh_details["session_id"],

            token_family=refresh_details["token_family"],

            generation=refresh_details["generation"],

            expires_at=refresh_details["expires"],

            revoked=False,

            ip_address=ip_address,

            user_agent=user_agent,

            device_name=device_name,
        )

        try:

            #
            # Repository persists the token.
            #

            self.refresh_repository.create(
                token_record
            )

            #
            # Repository refreshes the entity,
            # so only one commit is required.
            #

            self.db.commit()

        except Exception:

            self.db.rollback()

            raise

        return {

            "access_token": access_token,

            "refresh_token": refresh_token,

            "token_type": "bearer",

            "user": user,

            "session_id": refresh_details["session_id"],

            "token_family": refresh_details["token_family"],
        }

    # =====================================================
    # Refresh Token Rotation
    # =====================================================

    def refresh_access_token(
        self,
        refresh_token: str,
    ) -> dict:
        """
        Enterprise refresh token rotation.

        Workflow
        --------
        1. Verify JWT signature and expiry.
        2. Lookup stored refresh token.
        3. Detect replay/reuse.
        4. Rotate refresh token.
        5. Issue new access token.
        6. Commit atomically.
        """

        payload = verify_refresh_token(refresh_token)

        token_details = get_refresh_token_details(
            refresh_token
        )

        token_hash = hash_refresh_token(
            refresh_token
        )

        try:

            with self.db.begin():

                stored = (
                    self.refresh_repository
                    .get_active_token(token_hash)
                )

                if stored is None:

                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Refresh token not recognized",
                    )

                #
                # Replay detection
                #

                if stored.revoked:

                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Refresh token revoked",
                    )

                if stored.is_expired:

                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Refresh token expired",
                    )

                #
                # Rotation replay detection
                #

                if stored.replaced_by_token_id is not None:

                    self.refresh_repository.revoke_token_family(
                        stored.token_family,
                        reason="refresh_token_reuse_detected",
                    )

                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Refresh token reuse detected",
                    )

                #
                # Load user
                #

                user = (
                    self.user_repository
                    .get_by_id(
                        uuid.UUID(payload["sub"])
                    )
                )

                if user is None:

                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="User no longer exists",
                    )

                if not user.active:

                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Account disabled",
                    )

                #
                # Update usage timestamp
                #

                self.refresh_repository.update_last_used(
                    stored
                )

                #
                # Create replacement tokens
                #

                new_access_token = create_access_token(
                    subject=str(user.id),
                )

                new_refresh_token = create_refresh_token(
                    subject=str(user.id),
                    session_id=stored.session_id,
                    token_family=stored.token_family,
                    generation=stored.generation + 1,
                )

                new_details = get_refresh_token_details(
                    new_refresh_token
                )
                
                                #
                # Persist replacement token
                #

                replacement = RefreshToken(

                    id=uuid.uuid4(),

                    user_id=user.id,

                    token_hash=hash_refresh_token(
                        new_refresh_token
                    ),

                    jwt_id=new_details["jti"],

                    session_id=stored.session_id,

                    token_family=stored.token_family,

                    generation=stored.generation + 1,

                    expires_at=new_details["expires"],

                    revoked=False,

                    ip_address=stored.ip_address,

                    user_agent=stored.user_agent,

                    device_name=stored.device_name,
                )

                self.refresh_repository.rotate(
                    old_token=stored,
                    new_token=replacement,
                )

                return {

                    "access_token": new_access_token,

                    "refresh_token": new_refresh_token,

                    "token_type": "bearer",

                    "user": user,
                }

        except HTTPException:
            raise

        except Exception:

            self.db.rollback()

            raise

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

        stored = (
            self.refresh_repository
            .get_by_token_hash(token_hash)
        )

        if stored is None:
            return

        try:

            self.refresh_repository.revoke(
                stored,
                reason="logout",
            )

            self.db.commit()

        except Exception:

            self.db.rollback()

            raise

    # =====================================================
    # Logout All Sessions
    # =====================================================

    def logout_all(
        self,
        user: User,
    ) -> None:

        try:

            self.refresh_repository.revoke_all_for_user(
                user.id,
                reason="logout_all",
            )

            self.db.commit()

        except Exception:

            self.db.rollback()

            raise