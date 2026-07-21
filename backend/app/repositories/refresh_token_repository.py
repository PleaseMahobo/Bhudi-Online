from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    """
    Repository responsible for persistence of refresh tokens.

    Responsibilities
    ----------------
    - Store refresh tokens
    - Query refresh tokens
    - Rotate refresh tokens
    - Detect token reuse
    - Revoke sessions
    - Revoke token families
    - Cleanup expired tokens

    No JWT creation or validation occurs here.
    """

    def __init__(
        self,
        db: Session,
    ):
        self.db = db

    # ==========================================================
    # CREATE
    # ==========================================================

    def create(
        self,
        token: RefreshToken,
    ) -> RefreshToken:

        self.db.add(token)
        self.db.flush()
        self.db.refresh(token)

        return token

    def save(self) -> None:
        self.db.flush()

    # ==========================================================
    # LOOKUPS
    # ==========================================================

    def get_by_id(
        self,
        token_id: UUID,
    ) -> RefreshToken | None:

        return (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.id == token_id
            )
            .first()
        )

    def get_by_hash(
        self,
        token_hash: str,
    ) -> RefreshToken | None:

        return (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.token_hash == token_hash
            )
            .first()
        )

    def get_by_jti(
        self,
        jwt_id: str,
    ) -> RefreshToken | None:

        return (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.jwt_id == jwt_id
            )
            .first()
        )
        
    # ==========================================================
    # ACTIVE TOKEN QUERIES
    # ==========================================================

    def get_active_token(
        self,
        token_hash: str,
    ) -> RefreshToken | None:
        """
        Returns an active refresh token matching the supplied
        SHA-256 hash.
        """

        return (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked.is_(False),
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
            .first()
        )

    def get_active_tokens_for_user(
        self,
        user_id: UUID,
    ) -> list[RefreshToken]:
        """
        Returns all currently active refresh tokens
        belonging to a user.
        """

        return (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked.is_(False),
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
            .order_by(
                RefreshToken.created_at.desc()
            )
            .all()
        )

    # ==========================================================
    # SESSION QUERIES
    # ==========================================================

    def get_session_tokens(
        self,
        session_id: str,
    ) -> list[RefreshToken]:
        """
        Returns every refresh token issued during
        a single login session.
        """

        return (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.session_id == session_id
            )
            .order_by(
                RefreshToken.generation.asc()
            )
            .all()
        )

    def get_active_session_tokens(
        self,
        session_id: str,
    ) -> list[RefreshToken]:
        """
        Returns only active refresh tokens
        belonging to a session.
        """

        return (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.session_id == session_id,
                RefreshToken.revoked.is_(False),
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
            .order_by(
                RefreshToken.generation.asc()
            )
            .all()
        )

    def get_latest_session_token(
        self,
        session_id: str,
    ) -> RefreshToken | None:
        """
        Returns the newest token issued for
        the session.
        """

        return (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.session_id == session_id
            )
            .order_by(
                RefreshToken.generation.desc()
            )
            .first()
        )

    # ==========================================================
    # TOKEN FAMILY QUERIES
    # ==========================================================

    def get_token_family(
        self,
        token_family: str,
    ) -> list[RefreshToken]:
        """
        Returns every token belonging
        to a rotation family.
        """

        return (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.token_family == token_family
            )
            .order_by(
                RefreshToken.generation.asc()
            )
            .all()
        )

    def get_active_family_tokens(
        self,
        token_family: str,
    ) -> list[RefreshToken]:
        """
        Returns active tokens in the family.
        Normally only one token should remain active.
        """

        return (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.token_family == token_family,
                RefreshToken.revoked.is_(False),
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
            .order_by(
                RefreshToken.generation.desc()
            )
            .all()
        )

    def get_latest_family_token(
        self,
        token_family: str,
    ) -> RefreshToken | None:
        """
        Returns the highest-generation token
        in the family.
        """

        return (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.token_family == token_family
            )
            .order_by(
                RefreshToken.generation.desc()
            )
            .first()
        )
        
    # ==========================================================
    # USAGE TRACKING
    # ==========================================================

    def update_last_used(
        self,
        token: RefreshToken,
    ) -> None:
        """
        Updates the last-used timestamp for a token.
        """

        token.mark_used()

        self.db.flush()

    # ==========================================================
    # TOKEN ROTATION
    # ==========================================================

    def rotate(
        self,
        *,
        old_token: RefreshToken,
        new_token: RefreshToken,
    ) -> RefreshToken:
        """
        Atomically rotates a refresh token.

        The old token is revoked, linked to its replacement,
        and the new token is persisted.

        NOTE:
        No commit occurs here. The service layer owns the
        transaction boundary.
        """

        old_token.revoke("token_rotated")

        self.db.add(new_token)

        self.db.flush()

        old_token.replaced_by_token_id = new_token.id

        old_token.updated_at = datetime.now(timezone.utc)

        self.db.flush()

        return new_token

    # ==========================================================
    # SINGLE TOKEN REVOCATION
    # ==========================================================

    def revoke(
        self,
        token: RefreshToken,
        reason: str | None = None,
    ) -> None:
        """
        Revokes a single refresh token.
        """

        if token.revoked:
            return

        token.revoke(reason)

        token.updated_at = datetime.now(timezone.utc)

        self.db.flush()

    def revoke_by_hash(
        self,
        token_hash: str,
        reason: str | None = None,
    ) -> bool:
        """
        Revokes a token by its SHA-256 hash.

        Returns True if a token was found.
        """

        token = self.get_by_hash(token_hash)

        if token is None:
            return False

        self.revoke(
            token,
            reason,
        )

        return True

    # ==========================================================
    # SESSION REVOCATION
    # ==========================================================

    def revoke_session(
        self,
        session_id: str,
        reason: str = "session_logout",
    ) -> int:
        """
        Revokes every active token
        belonging to a session.

        Returns the number revoked.
        """

        revoked = 0

        for token in self.get_active_session_tokens(session_id):

            token.revoke(reason)

            token.updated_at = datetime.now(timezone.utc)

            revoked += 1

        self.db.flush()

        return revoked

    # ==========================================================
    # TOKEN FAMILY REVOCATION
    # ==========================================================

    def revoke_token_family(
        self,
        token_family: str,
        reason: str = "token_reuse_detected",
    ) -> int:
        """
        Revokes every token in a rotation family.

        This is the primary defence against
        stolen refresh-token replay attacks.
        """

        revoked = 0

        for token in self.get_token_family(token_family):

            if token.revoked:
                continue

            token.revoke(reason)

            token.updated_at = datetime.now(timezone.utc)

            revoked += 1

        self.db.flush()

        return revoked

    # ==========================================================
    # USER REVOCATION
    # ==========================================================

    def revoke_all_for_user(
        self,
        user_id: UUID,
        reason: str = "logout_all",
    ) -> int:
        """
        Revokes every active refresh token
        owned by the user.

        Used for:

        - Logout all devices
        - Password change
        - Administrator forced logout
        - Account compromise
        """

        revoked = 0

        for token in self.get_active_tokens_for_user(user_id):

            token.revoke(reason)

            token.updated_at = datetime.now(timezone.utc)

            revoked += 1

        self.db.flush()

        return revoked
    
    # ==========================================================
    # TOKEN REUSE DETECTION
    # ==========================================================

    def is_token_reused(
        self,
        token: RefreshToken,
    ) -> bool:
        """
        Determines whether a presented refresh token represents
        a refresh-token replay attack.

        A revoked token that has already been replaced should
        never be presented again.

        If it is, we assume compromise.
        """

        return (
            token.revoked
            and token.replaced_by_token_id is not None
        )

    def detect_reuse(
        self,
        token: RefreshToken,
    ) -> bool:
        """
        Alias used by AuthService.

        Returns True if refresh-token reuse
        has been detected.
        """

        return self.is_token_reused(token)

    def revoke_family_on_reuse(
        self,
        token: RefreshToken,
    ) -> int:
        """
        Immediately revokes every token in the family.

        This follows OAuth 2.0 Security BCP guidance
        for refresh-token replay attacks.
        """

        return self.revoke_token_family(
            token_family=token.token_family,
            reason="refresh_token_reuse_detected",
        )

    # ==========================================================
    # TOKEN VALIDATION HELPERS
    # ==========================================================

    def is_active(
        self,
        token: RefreshToken,
    ) -> bool:
        """
        Repository-level validity check.
        """

        return (
            not token.revoked
            and token.expires_at > datetime.now(timezone.utc)
        )

    def is_expired(
        self,
        token: RefreshToken,
    ) -> bool:

        return (
            token.expires_at <= datetime.now(timezone.utc)
        )

    def has_successor(
        self,
        token: RefreshToken,
    ) -> bool:

        return (
            token.replaced_by_token_id
            is not None
        )

    # ==========================================================
    # HOUSEKEEPING
    # ==========================================================

    def delete_expired(self) -> int:
        """
        Permanently removes expired refresh tokens.

        Intended for scheduled background cleanup.
        """

        deleted = (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.expires_at < datetime.now(timezone.utc)
            )
            .delete(
                synchronize_session=False,
            )
        )

        self.db.flush()

        return deleted

    def delete_revoked(
        self,
        older_than: datetime,
    ) -> int:
        """
        Deletes revoked tokens older than the supplied date.

        Keeps the refresh_tokens table compact while
        preserving recent audit history.
        """

        deleted = (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.revoked.is_(True),
                RefreshToken.revoked_at < older_than,
            )
            .delete(
                synchronize_session=False,
            )
        )

        self.db.flush()

        return deleted

    # ==========================================================
    # METRICS
    # ==========================================================

    def count_active_for_user(
        self,
        user_id: UUID,
    ) -> int:

        return (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked.is_(False),
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
            .count()
        )

    def count_active_sessions(
        self,
        user_id: UUID,
    ) -> int:
        """
        Returns the number of active login sessions.

        A session is identified by its unique session_id.
        """

        return (
            self.db.query(
                RefreshToken.session_id
            )
            .filter(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked.is_(False),
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
            .distinct()
            .count()
        )