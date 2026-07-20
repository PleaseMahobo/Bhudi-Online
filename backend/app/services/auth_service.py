from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.jwt import (
    create_access_token,
    create_refresh_token,
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

    Responsibilities:
    - User registration
    - Credential validation
    - JWT issuance
    - Refresh token rotation
    - Logout/revocation

    Does NOT:
    - Manage JWT internals
    - Manage password hashing algorithms
    - Execute raw SQL
    """

    def __init__(self, db: Session):

        self.db = db

        self.user_repository = UserRepository(db)

        self.refresh_repository = RefreshTokenRepository(db)


    # ---------------------------------------------------------
    # REGISTER
    # ---------------------------------------------------------

    def register(
        self,
        email: str,
        password: str,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> User:

        existing_user = (
            self.user_repository
            .get_by_email(email)
        )

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is already registered",
            )


        user = User(
            id=uuid.uuid4(),
            email=email.lower().strip(),
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



    # ---------------------------------------------------------
    # AUTHENTICATE
    # ---------------------------------------------------------

    def authenticate(
        self,
        email: str,
        password: str,
    ) -> User:


        user = (
            self.user_repository
            .get_by_email(email.lower().strip())
        )


        if not user:

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



    # ---------------------------------------------------------
    # LOGIN TOKEN CREATION
    # ---------------------------------------------------------

    def login(
        self,
        user: User,
    ) -> dict:


        access_token = create_access_token(
            subject=str(user.id),
        )


        refresh_token = create_refresh_token(
            subject=str(user.id),
        )


        refresh_details = get_refresh_token_details(
            refresh_token
        )


        token_record = RefreshToken(

            id=uuid.uuid4(),

            user_id=user.id,

            token_hash=hash_refresh_token(
                refresh_token
            ),

            expires_at=refresh_details["expires"],

            revoked=False,

        )


        try:

            self.refresh_repository.create(
                token_record
            )

            self.db.commit()


        except Exception:

            self.db.rollback()

            raise



        return {

            "access_token": access_token,

            "refresh_token": refresh_token,

            "token_type": "bearer",

            "user": user,

        }



    # ---------------------------------------------------------
    # REFRESH TOKEN ROTATION
    # ---------------------------------------------------------

    def refresh_access_token(
        self,
        refresh_token: str,
    ) -> dict:


        payload = verify_refresh_token(
            refresh_token
        )


        user_id = payload.get("sub")


        if not user_id:

            raise HTTPException(
                status_code=401,
                detail="Invalid refresh token",
            )



        stored = (
            self.refresh_repository
            .get_by_hash(
                hash_refresh_token(refresh_token)
            )
        )


        if not stored:

            raise HTTPException(
                status_code=401,
                detail="Invalid refresh token",
            )


        if stored.revoked:

            raise HTTPException(
                status_code=401,
                detail="Refresh token revoked",
            )


        if stored.expires_at < datetime.now(
            timezone.utc
        ):

            raise HTTPException(
                status_code=401,
                detail="Refresh token expired",
            )


        user = (
            self.user_repository
            .get_by_id(
                uuid.UUID(user_id)
            )
        )


        if not user:

            raise HTTPException(
                status_code=401,
                detail="User not found",
            )


        # Rotate token

        stored.revoked = True

        new_tokens = self.login(user)


        self.db.commit()


        return new_tokens



    # ---------------------------------------------------------
    # LOGOUT
    # ---------------------------------------------------------

    def logout(
        self,
        refresh_token: str,
    ) -> None:


        token_hash = hash_refresh_token(
            refresh_token
        )


        stored = (
            self.refresh_repository
            .get_by_hash(token_hash)
        )


        if stored:

            stored.revoked = True

            stored.revoked_at = (
                datetime.now(timezone.utc)
            )

            self.db.commit()