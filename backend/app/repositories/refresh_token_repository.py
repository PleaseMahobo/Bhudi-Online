from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, db: Session):
        self.db = db

    # =====================================================
    # Create / Save
    # =====================================================

    def create(
        self,
        token: RefreshToken,
    ) -> RefreshToken:

        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)

        return token

    def save(self):

        self.db.commit()

    # =====================================================
    # Queries
    # =====================================================

    def get_by_id(
        self,
        token_id: UUID,
    ) -> Optional[RefreshToken]:

        return (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.id == token_id,
            )
            .first()
        )

    def get_by_token_hash(
        self,
        token_hash: str,
    ) -> Optional[RefreshToken]:

        return (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.token_hash == token_hash,
            )
            .first()
        )

    def get_by_jwt_id(
        self,
        jwt_id: str,
    ) -> Optional[RefreshToken]:

        return (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.jwt_id == jwt_id,
            )
            .first()
        )

    def get_active_token(
        self,
        token_hash: str,
    ) -> Optional[RefreshToken]:

        return (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked.is_(False),
                RefreshToken.expires_at > datetime.utcnow(),
            )
            .first()
        )

    def get_active_tokens_for_user(
        self,
        user_id: UUID,
    ) -> list[RefreshToken]:

        return (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked.is_(False),
                RefreshToken.expires_at > datetime.utcnow(),
            )
            .order_by(
                RefreshToken.created_at.desc(),
            )
            .all()
        )

    def get_session_tokens(
        self,
        session_id: str,
    ) -> list[RefreshToken]:

        return (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.session_id == session_id,
            )
            .order_by(
                RefreshToken.generation.desc(),
            )
            .all()
        )

    def get_token_family(
        self,
        family: str,
    ) -> list[RefreshToken]:

        return (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.token_family == family,
            )
            .order_by(
                RefreshToken.generation.asc(),
            )
            .all()
        )

    # =====================================================
    # Usage Tracking
    # =====================================================

    def update_last_used(
        self,
        token: RefreshToken,
    ):

        token.mark_used()

        self.db.commit()

    # =====================================================
    # Revocation
    # =====================================================

    def revoke(
        self,
        token: RefreshToken,
        reason: str | None = None,
    ):

        token.revoke(reason)

        self.db.commit()

    def revoke_by_hash(
        self,
        token_hash: str,
        reason: str | None = None,
    ):

        token = self.get_by_token_hash(token_hash)

        if token:

            self.revoke(
                token,
                reason,
            )

    def revoke_session(
        self,
        session_id: str,
        reason: str = "session_logout",
    ):

        tokens = self.get_session_tokens(session_id)

        for token in tokens:
            token.revoke(reason)

        self.db.commit()

    def revoke_token_family(
        self,
        family: str,
        reason: str = "reuse_detected",
    ):

        tokens = self.get_token_family(family)

        for token in tokens:
            token.revoke(reason)

        self.db.commit()

    def revoke_all_for_user(
        self,
        user_id: UUID,
        reason: str = "logout_all",
    ):

        tokens = self.get_active_tokens_for_user(user_id)

        for token in tokens:
            token.revoke(reason)

        self.db.commit()

    # =====================================================
    # Rotation
    # =====================================================

    def rotate(
        self,
        old_token: RefreshToken,
        new_token: RefreshToken,
    ) -> RefreshToken:

        old_token.revoke("token_rotated")

        self.db.add(new_token)

        self.db.flush()

        old_token.replaced_by_token_id = new_token.id

        self.db.commit()

        self.db.refresh(new_token)

        return new_token

    # =====================================================
    # Cleanup
    # =====================================================

    def delete_expired(self) -> int:

        deleted = (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.expires_at < datetime.utcnow(),
            )
            .delete(
                synchronize_session=False,
            )
        )

        self.db.commit()

        return deleted