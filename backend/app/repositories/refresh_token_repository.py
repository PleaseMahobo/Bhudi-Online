from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    """
    Enterprise Refresh Token Repository.

    Responsibilities
    ----------------
    - Persist refresh tokens
    - Query refresh tokens
    - Support rotation
    - Detect token reuse
    - Revoke sessions
    - Revoke token families
    - Cleanup expired tokens

    Authentication logic does NOT belong here.

    JWT generation does NOT belong here.

    Password handling does NOT belong here.
    """

    def __init__(
        self,
        db: Session,
    ) -> None:

        self.db = db


    # ==========================================================
    # Internal Helpers
    # ==========================================================

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(
            timezone.utc
        )


    # ==========================================================
    # CREATE
    # ==========================================================

    def create(
        self,
        token: RefreshToken,
    ) -> RefreshToken:
        """
        Persist a refresh token.

        Transaction ownership remains
        with the service layer.
        """

        self.db.add(token)

        self.db.flush()

        return token


    def save(self) -> None:
        """
        Flush pending repository changes.
        """

        self.db.flush()



    # ==========================================================
    # LOOKUPS
    # ==========================================================

    def get_by_id(
        self,
        token_id: UUID,
    ) -> RefreshToken | None:
        """
        Retrieve token by primary key.
        """

        return self.db.scalar(
            select(RefreshToken)
            .where(
                RefreshToken.id == token_id
            )
        )


    def get_by_hash(
        self,
        token_hash: str,
    ) -> RefreshToken | None:
        """
        Retrieve token by SHA-256 hash.
        """

        return self.db.scalar(
            select(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash
            )
        )


    def get_by_token_hash(
        self,
        token_hash: str,
    ) -> RefreshToken | None:
        """
        Compatibility alias.

        Older AuthService versions
        use this name.
        """

        return self.get_by_hash(
            token_hash
        )


    def get_by_jti(
        self,
        jwt_id: str,
    ) -> RefreshToken | None:
        """
        Retrieve token by JWT ID.
        """

        return self.db.scalar(
            select(RefreshToken)
            .where(
                RefreshToken.jwt_id == jwt_id
            )
        )
    def revoke_family(
        self,
        token_family: str,
        reason: str = "refresh token rotation",
    ) -> int:
        """
        Revoke every active refresh token belonging
        to the same token family.
        """

        tokens = (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.token_family == token_family,
                RefreshToken.revoked.is_(False),
            )
            .all()
        )

        for token in tokens:
            token.revoked = True
            token.revoked_at = datetime.now(timezone.utc)
            token.revoked_reason = reason

        return len(tokens)


    # ==========================================================
    # ACTIVE TOKEN QUERIES
    # ==========================================================

    def get_active_token(
        self,
        token_hash: str,
    ) -> RefreshToken | None:
        """
        Retrieve active refresh token.

        Active means:

        - not revoked
        - not expired
        """

        return self.db.scalar(
            select(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked.is_(False),
                RefreshToken.expires_at
                > self._utcnow(),
            )
        )


    def get_active_tokens_for_user(
        self,
        user_id: UUID,
    ) -> list[RefreshToken]:
        """
        Return active refresh tokens
        for a user.
        """

        return list(
            self.db.scalars(
                select(RefreshToken)
                .where(
                    RefreshToken.user_id == user_id,
                    RefreshToken.revoked.is_(False),
                    RefreshToken.expires_at
                    > self._utcnow(),
                )
                .order_by(
                    RefreshToken.created_at.desc()
                )
            )
        )



    # ==========================================================
    # SESSION QUERIES
    # ==========================================================

    def get_session_tokens(
        self,
        session_id: str,
    ) -> list[RefreshToken]:
        """
        Return all tokens in session.
        """

        return list(
            self.db.scalars(
                select(RefreshToken)
                .where(
                    RefreshToken.session_id == session_id
                )
                .order_by(
                    RefreshToken.generation.asc()
                )
            )
        )


    def get_active_session_tokens(
        self,
        session_id: str,
    ) -> list[RefreshToken]:
        """
        Return active tokens
        belonging to session.
        """

        return list(
            self.db.scalars(
                select(RefreshToken)
                .where(
                    RefreshToken.session_id == session_id,
                    RefreshToken.revoked.is_(False),
                    RefreshToken.expires_at
                    > self._utcnow(),
                )
                .order_by(
                    RefreshToken.generation.asc()
                )
            )
        )


    def get_active_session(
        self,
        *,
        user_id: UUID,
        session_id: str,
    ) -> RefreshToken | None:
        """
        Validate an active user session.
        """

        return self.db.scalar(
            select(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.session_id == session_id,
                RefreshToken.revoked.is_(False),
                RefreshToken.expires_at
                > self._utcnow(),
            )
            .order_by(
                RefreshToken.generation.desc()
            )
        )


    def get_latest_session_token(
        self,
        session_id: str,
    ) -> RefreshToken | None:

        return self.db.scalar(
            select(RefreshToken)
            .where(
                RefreshToken.session_id == session_id
            )
            .order_by(
                RefreshToken.generation.desc()
            )
        )
        
    # ==========================================================
    # TOKEN FAMILY QUERIES
    # ==========================================================

    def get_token_family(
        self,
        token_family: str,
    ) -> list[RefreshToken]:
        """
        Return all tokens belonging
        to a rotation family.
        """

        return list(
            self.db.scalars(
                select(RefreshToken)
                .where(
                    RefreshToken.token_family == token_family
                )
                .order_by(
                    RefreshToken.generation.asc()
                )
            )
        )


    def get_active_family_tokens(
        self,
        token_family: str,
    ) -> list[RefreshToken]:
        """
        Return active tokens in a family.

        Normally only one token should
        be active at any time.
        """

        return list(
            self.db.scalars(
                select(RefreshToken)
                .where(
                    RefreshToken.token_family == token_family,
                    RefreshToken.revoked.is_(False),
                    RefreshToken.expires_at
                    > self._utcnow(),
                )
                .order_by(
                    RefreshToken.generation.desc()
                )
            )
        )


    def get_latest_family_token(
        self,
        token_family: str,
    ) -> RefreshToken | None:
        """
        Return highest generation token
        in rotation family.
        """

        return self.db.scalar(
            select(RefreshToken)
            .where(
                RefreshToken.token_family == token_family
            )
            .order_by(
                RefreshToken.generation.desc()
            )
        )



    # ==========================================================
    # USAGE TRACKING
    # ==========================================================

    def update_last_used(
        self,
        token: RefreshToken,
    ) -> None:
        """
        Update token usage timestamp.
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
        Perform refresh token rotation.

        Flow:

        old token
             |
             | revoke
             v
        replacement token
             |
             | linked through replaced_by_token_id


        Transaction ownership remains
        with AuthService.
        """

        old_token.revoke(
            "token_rotated"
        )


        self.db.add(
            new_token
        )


        self.db.flush()


        if old_token.replaced_by_token_id is None:
            old_token.replaced_by_token_id = (
                new_token.id
            )

        old_token.updated_at = (
            self._utcnow()
        )


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
        Revoke one refresh token.
        """

        if token.revoked:

            return


        token.revoke(
            reason
        )


        token.updated_at = (
            self._utcnow()
        )


        self.db.flush()



    def revoke_by_hash(
        self,
        token_hash: str,
        reason: str | None = None,
    ) -> bool:
        """
        Revoke token using hash.

        Returns:

            True  -> token found
            False -> token missing
        """

        token = (
            self.get_by_hash(
                token_hash
            )
        )


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
        *,
        user_id: UUID,
        session_id: str,
        reason: str = "session_logout",
    ) -> int:
        """
        Revoke all tokens belonging
        to a specific user session.
        """

        revoked = 0


        tokens = (
            self.db.scalars(
                select(RefreshToken)
                .where(
                    RefreshToken.user_id == user_id,
                    RefreshToken.session_id == session_id,
                    RefreshToken.revoked.is_(False),
                )
            )
            .all()
        )


        for token in tokens:

            token.revoke(
                reason
            )

            token.updated_at = (
                self._utcnow()
            )

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
        Revoke all tokens in a family.

        Used for:

        - refresh token replay
        - suspected theft
        - compromise response
        """

        revoked = 0


        tokens = (
            self.get_token_family(
                token_family
            )
        )


        for token in tokens:

            if token.revoked:

                continue


            token.revoke(
                reason
            )


            token.updated_at = (
                self._utcnow()
            )


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
        Revoke every active refresh token
        owned by a user.

        Used for:

        - logout all devices
        - password change
        - account compromise
        - administrator action
        """

        revoked = 0


        tokens = (
            self.db.scalars(
                select(RefreshToken)
                .where(
                    RefreshToken.user_id == user_id,
                    RefreshToken.revoked.is_(False),
                )
            )
            .all()
        )


        for token in tokens:

            token.revoke(
                reason
            )

            token.updated_at = (
                self._utcnow()
            )

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
        Determine whether a refresh token
        was previously rotated.

        A rotated token being presented again
        indicates possible token theft.
        """

        return (
            token.revoked
            and token.replaced_by_token_id
            is not None
        )



    def detect_reuse(
        self,
        token: RefreshToken,
    ) -> bool:
        """
        Compatibility wrapper used by
        AuthService.
        """

        return self.is_token_reused(
            token
        )



    def revoke_family_on_reuse(
        self,
        token: RefreshToken,
    ) -> int:
        """
        Revoke entire token family after
        refresh token replay detection.
        """

        return self.revoke_token_family(
            token_family=token.token_family,
            reason="refresh_token_reuse_detected",
        )



    # ==========================================================
    # VALIDATION HELPERS
    # ==========================================================

    def is_active(
        self,
        token: RefreshToken,
    ) -> bool:
        """
        Repository-level token validity check.
        """

        return (
            not token.revoked
            and token.expires_at
            > self._utcnow()
        )



    def is_expired(
        self,
        token: RefreshToken,
    ) -> bool:
        """
        Determine token expiry state.
        """

        return (
            token.expires_at
            <= self._utcnow()
        )



    def has_successor(
        self,
        token: RefreshToken,
    ) -> bool:
        """
        Returns True when token has
        already been rotated.
        """

        return (
            token.replaced_by_token_id
            is not None
        )



    # ==========================================================
    # HOUSEKEEPING
    # ==========================================================

    def delete_expired(
        self,
    ) -> int:
        """
        Permanently remove expired tokens.

        Intended for scheduled cleanup jobs.
        """

        result = self.db.execute(
            delete(RefreshToken)
            .where(
                RefreshToken.expires_at
                < self._utcnow()
            )
        )


        self.db.flush()


        return result.rowcount or 0



    def delete_revoked(
        self,
        older_than: datetime,
    ) -> int:
        """
        Remove revoked tokens older than
        supplied retention period.
        """

        result = self.db.execute(
            delete(RefreshToken)
            .where(
                RefreshToken.revoked.is_(True),
                RefreshToken.revoked_at
                < older_than,
            )
        )


        self.db.flush()


        return result.rowcount or 0



    def cleanup(
        self,
    ) -> dict[str, int]:
        """
        Repository maintenance.

        Removes:

        - expired tokens
        - old revoked tokens
        """

        now = self._utcnow()


        expired = self.delete_expired()


        revoked = self.delete_revoked(
            now - timedelta(days=90)
        )


        return {
            "expired_deleted": expired,
            "revoked_deleted": revoked,
        }
        
    # ==========================================================
    # METRICS
    # ==========================================================

    def count_active_for_user(
        self,
        user_id: UUID,
    ) -> int:
        """
        Count active refresh tokens
        belonging to a user.
        """

        return (
            self.db.scalar(
                select(
                    RefreshToken
                )
                .where(
                    RefreshToken.user_id == user_id,
                    RefreshToken.revoked.is_(False),
                    RefreshToken.expires_at
                    > self._utcnow(),
                )
                .count()
            )
            or 0
        )



    def count_active_sessions(
        self,
        user_id: UUID,
    ) -> int:
        """
        Count active login sessions.

        A session is identified by
        session_id.
        """

        sessions = (
            self.db.execute(
                select(
                    RefreshToken.session_id
                )
                .where(
                    RefreshToken.user_id == user_id,
                    RefreshToken.revoked.is_(False),
                    RefreshToken.expires_at
                    > self._utcnow(),
                )
                .distinct()
            )
            .all()
        )


        return len(
            sessions
        )



    # ==========================================================
    # AUDIT HELPERS
    # ==========================================================

    def get_recent_tokens(
        self,
        user_id: UUID,
        limit: int = 20,
    ) -> list[RefreshToken]:
        """
        Return recent refresh tokens.

        Used for:

        - security dashboard
        - active sessions UI
        - incident response
        """

        return list(
            self.db.scalars(
                select(RefreshToken)
                .where(
                    RefreshToken.user_id == user_id
                )
                .order_by(
                    RefreshToken.created_at.desc()
                )
                .limit(limit)
            )
        )



    def get_revoked_tokens(
        self,
        user_id: UUID,
    ) -> list[RefreshToken]:
        """
        Return revoked tokens for audit.
        """

        return list(
            self.db.scalars(
                select(RefreshToken)
                .where(
                    RefreshToken.user_id == user_id,
                    RefreshToken.revoked.is_(True),
                )
                .order_by(
                    RefreshToken.revoked_at.desc()
                )
            )
        )



    def get_expired_tokens(
        self,
        user_id: UUID,
    ) -> list[RefreshToken]:
        """
        Return expired tokens.
        """

        return list(
            self.db.scalars(
                select(RefreshToken)
                .where(
                    RefreshToken.user_id == user_id,
                    RefreshToken.expires_at
                    <= self._utcnow(),
                )
                .order_by(
                    RefreshToken.expires_at.desc()
                )
            )
        )



    # ==========================================================
    # DEVICE LOOKUPS
    # ==========================================================

    def get_tokens_for_device(
        self,
        user_id: UUID,
        device_name: str,
    ) -> list[RefreshToken]:
        """
        Return tokens issued to
        a specific device.
        """

        return list(
            self.db.scalars(
                select(RefreshToken)
                .where(
                    RefreshToken.user_id == user_id,
                    RefreshToken.device_name == device_name,
                )
                .order_by(
                    RefreshToken.created_at.desc()
                )
            )
        )



    def revoke_device(
        self,
        *,
        user_id: UUID,
        device_name: str,
        reason: str = "device_logout",
    ) -> int:
        """
        Revoke all tokens belonging
        to a device.
        """

        revoked = 0


        tokens = (
            self.db.scalars(
                select(RefreshToken)
                .where(
                    RefreshToken.user_id == user_id,
                    RefreshToken.device_name == device_name,
                    RefreshToken.revoked.is_(False),
                )
            )
            .all()
        )


        for token in tokens:

            token.revoke(
                reason
            )

            token.updated_at = (
                self._utcnow()
            )

            revoked += 1


        self.db.flush()


        return revoked
    
    # ==========================================================
    # SECURITY OPERATIONS
    # ==========================================================

    def revoke_all_except_session(
        self,
        *,
        user_id: UUID,
        session_id: str,
        reason: str = "logout_other_devices",
    ) -> int:
        """
        Revoke all active sessions except
        the supplied session.

        Used by:

            "Log out other devices"
        """

        revoked = 0


        tokens = (
            self.db.scalars(
                select(RefreshToken)
                .where(
                    RefreshToken.user_id == user_id,
                    RefreshToken.revoked.is_(False),
                )
            )
            .all()
        )


        for token in tokens:

            if token.session_id == session_id:
                continue


            token.revoke(
                reason
            )

            token.updated_at = (
                self._utcnow()
            )

            revoked += 1


        self.db.flush()


        return revoked



    # ==========================================================
    # EXPORT / SERIALIZATION HELPERS
    # ==========================================================

    def get_user_sessions(
        self,
        user_id: UUID,
    ) -> list[dict]:
        """
        Returns simplified active session
        information for security dashboards.
        """

        tokens = (
            self.get_active_tokens_for_user(
                user_id
            )
        )


        sessions: dict[str, dict] = {}


        for token in tokens:

            if token.session_id not in sessions:

                sessions[token.session_id] = {
                    "session_id": token.session_id,
                    "device_name": token.device_name,
                    "ip_address": token.ip_address,
                    "user_agent": token.user_agent,
                    "created_at": (
                        token.created_at.isoformat()
                    ),
                    "last_used_at": (
                        token.last_used_at.isoformat()
                        if token.last_used_at
                        else None
                    ),
                    "trusted_device": (
                        token.trusted_device
                    ),
                }


        return list(
            sessions.values()
        )



    # ==========================================================
    # DEBUG / ADMIN HELPERS
    # ==========================================================

    def count_all(
        self,
    ) -> int:
        """
        Count all stored refresh tokens.
        """

        return (
            self.db.scalar(
                select(
                    RefreshToken
                )
                .count()
            )
            or 0
        )



    def purge_user_tokens(
        self,
        user_id: UUID,
    ) -> int:
        """
        Administrative hard delete.

        Intended for:

        - GDPR deletion workflows
        - tenant removal
        - account destruction

        Normal logout should use revoke.
        """

        result = self.db.execute(
            delete(RefreshToken)
            .where(
                RefreshToken.user_id == user_id
            )
        )


        self.db.flush()


        return result.rowcount or 0



    # ==========================================================
    # REPRESENTATION
    # ==========================================================

    def __repr__(self) -> str:

        return (
            "<RefreshTokenRepository("
            f"db={self.db!r}"
            ")>"
        )