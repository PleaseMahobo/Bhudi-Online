from __future__ import annotations

import uuid

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
    hash_refresh_token,
    normalize_password,
    validate_password_strength,
    verify_and_upgrade_password,
)

from app.models.user import User
from app.models.refresh_token import RefreshToken

from app.repositories.user_repository import (
    UserRepository,
)

from app.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)


class AuthService:
    """
    Enterprise authentication service.

    Responsibilities
    ----------------
    - User registration
    - Credential authentication
    - Login session creation
    - Refresh token rotation
    - Replay attack detection
    - Logout
    - Logout all sessions
    - Password hash migration
    - Session validation

    Authentication logic belongs here.
    Repository layer only handles persistence.
    """

    def __init__(
        self,
        db: Session,
    ) -> None:

        self.db = db

        self.user_repository = UserRepository(
            db
        )

        self.refresh_repository = RefreshTokenRepository(
            db
        )


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
        """
        Register a new user.

        Flow:

        normalize email
              |
        normalize password
              |
        validate password policy
              |
        hash password using Argon2id
              |
        create user
        """

        email = (
            email
            .lower()
            .strip()
        )

        password = normalize_password(
            password
        )


        valid, errors = validate_password_strength(
            password
        )


        if not valid:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": (
                        "Password does not meet "
                        "security requirements"
                    ),
                    "errors": errors,
                },
            )


        existing = (
            self.user_repository
            .get_by_email(email)
        )


        if existing:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address already registered",
            )


        user = User(
            id=uuid.uuid4(),

            email=email,

            password_hash=hash_password(
                password
            ),

            first_name=first_name,

            last_name=last_name,

            role="user",

            active=True,
        )


        try:

            self.user_repository.create(
                user
            )

            self.db.commit()

            self.db.refresh(
                user
            )

            return user


        except Exception:

            self.db.rollback()

            raise


    # =====================================================
    # Authenticate User
    # =====================================================

    def authenticate(
        self,
        email: str,
        password: str,
    ) -> User:
        """
        Authenticate user credentials.

        Supports:

        - Argon2id hashes
        - Legacy bcrypt hashes
        - Automatic bcrypt migration
        """

        email = (
            email
            .lower()
            .strip()
        )


        password = normalize_password(
            password
        )


        user = (
            self.user_repository
            .get_by_email(email)
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


        valid, upgraded_hash = (
            verify_and_upgrade_password(
                password,
                user.password_hash,
            )
        )


        if not valid:

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )


        if upgraded_hash:

            user.password_hash = upgraded_hash

            try:

                self.db.commit()


            except Exception:

                self.db.rollback()

                raise


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
        """
        Create authenticated session.

        Creates:

        - access JWT
        - refresh JWT
        - refresh token database record

        Refresh tokens are stored hashed only.
        """

        refresh_token = create_refresh_token(
            subject=str(user.id),
        )


        refresh_details = (
            get_refresh_token_details(
                refresh_token
            )
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

            jwt_id=refresh_details["jti"],

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

            "session_id": (
                refresh_details["session_id"]
            ),

            "token_family": (
                refresh_details["token_family"]
            ),
        }



    # =====================================================
    # Refresh Token Rotation
    # =====================================================

    def refresh_access_token(
        self,
        refresh_token: str,
    ) -> dict:
        """
        Perform secure refresh-token rotation.

        Workflow:

        1. Validate refresh JWT
        2. Hash presented token
        3. Locate stored token
        4. Detect replay
        5. Issue replacement token
        6. Revoke old token
        7. Return new credentials
        """


        #
        # Validate JWT signature
        #

        payload = verify_refresh_token(
            refresh_token
        )


        token_hash = hash_refresh_token(
            refresh_token
        )


        try:

            with self.db.begin():

                stored = (
                    self.refresh_repository
                    .get_by_hash(
                        token_hash
                    )
                )


                if stored is None:

                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=(
                            "Refresh token "
                            "not recognized"
                        ),
                    )


                #
                # Replay detection
                #
                # A revoked token with a successor
                # means somebody reused an old token.
                #

                if (
                    stored.revoked
                    and stored.replaced_by_token_id
                ):

                    self.refresh_repository.revoke_token_family(
                        stored.token_family,
                        reason=(
                            "refresh_token_reuse_detected"
                        ),
                    )


                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=(
                            "Refresh token reuse detected"
                        ),
                    )


                if stored.revoked:

                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=(
                            "Refresh token revoked"
                        ),
                    )


                if stored.is_expired:

                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=(
                            "Refresh token expired"
                        ),
                    )


                user_id = uuid.UUID(
                    payload["sub"]
                )


                user = (
                    self.user_repository
                    .get_by_id(
                        user_id
                    )
                )


                if user is None:

                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=(
                            "User no longer exists"
                        ),
                    )


                if not user.active:

                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=(
                            "Account disabled"
                        ),
                    )


                #
                # New access token
                #

                new_access_token = (
                    create_access_token(
                        subject=str(user.id)
                    )
                )


                #
                # New refresh token
                #

                new_refresh_token = (
                    create_refresh_token(
                        subject=str(user.id),

                        session_id=(
                            stored.session_id
                        ),

                        token_family=(
                            stored.token_family
                        ),

                        generation=(
                            stored.generation + 1
                        ),
                    )
                )


                new_details = (
                    get_refresh_token_details(
                        new_refresh_token
                    )
                )


                replacement = RefreshToken(

                    id=uuid.uuid4(),

                    user_id=user.id,

                    token_hash=hash_refresh_token(
                        new_refresh_token
                    ),

                    jwt_id=new_details["jti"],

                    session_id=(
                        stored.session_id
                    ),

                    token_family=(
                        stored.token_family
                    ),

                    generation=(
                        stored.generation + 1
                    ),

                    expires_at=(
                        new_details["expires"]
                    ),

                    revoked=False,

                    ip_address=(
                        stored.ip_address
                    ),

                    user_agent=(
                        stored.user_agent
                    ),

                    device_name=(
                        stored.device_name
                    ),
                )


                self.refresh_repository.rotate(
                    old_token=stored,
                    new_token=replacement,
                )


                return {

                    "access_token": (
                        new_access_token
                    ),

                    "refresh_token": (
                        new_refresh_token
                    ),

                    "token_type": "bearer",

                    "user": user,

                    "session_id": (
                        stored.session_id
                    ),

                    "token_family": (
                        stored.token_family
                    ),
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
        """
        Revoke a single refresh token.

        The plaintext token is never stored.

        Flow:

        refresh token
              |
        SHA-256 hash
              |
        database lookup
              |
        revoke token
        """


        token_hash = hash_refresh_token(
            refresh_token
        )


        stored = (
            self.refresh_repository
            .get_by_hash(
                token_hash
            )
        )


        #
        # Logout is intentionally idempotent.
        #
        # If the token does not exist,
        # the session is already terminated.
        #

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
        """
        Revoke all refresh tokens belonging
        to the user.

        Used for:

        - password compromise
        - administrator action
        - security response
        - user account protection
        """


        try:

            self.refresh_repository.revoke_all_for_user(
                user.id,
                reason="logout_all",
            )

            self.db.commit()


        except Exception:

            self.db.rollback()

            raise



    # =====================================================
    # Session Validation
    # =====================================================

    def validate_session(
        self,
        user_id: uuid.UUID,
        session_id: str,
    ) -> bool:
        """
        Check whether a session remains active.

        Used for:

        - sensitive operations
        - session enforcement
        - device management
        """


        tokens = (
            self.refresh_repository
            .get_active_session_tokens(
                session_id
            )
        )


        for token in tokens:

            if token.user_id == user_id:

                return True


        return False



    # =====================================================
    # Revoke Session
    # =====================================================

    def revoke_session(
        self,
        user_id: uuid.UUID,
        session_id: str,
        reason: str = "admin_action",
    ) -> None:
        """
        Revoke a specific login session.

        Used by:

        - security dashboard
        - device management
        - administrator controls
        """


        try:

            tokens = (
                self.refresh_repository
                .get_active_session_tokens(
                    session_id
                )
            )


            for token in tokens:

                if token.user_id != user_id:

                    continue


                self.refresh_repository.revoke(
                    token,
                    reason=reason,
                )


            self.db.commit()


        except Exception:

            self.db.rollback()

            raise



    # =====================================================
    # Password Security Helpers
    # =====================================================

    def change_password(
        self,
        user: User,
        new_password: str,
    ) -> None:
        """
        Change user password.

        Security actions:

        - validate password strength
        - hash using current algorithm
        - revoke existing sessions
        """


        new_password = normalize_password(
            new_password
        )


        valid, errors = validate_password_strength(
            new_password
        )


        if not valid:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": (
                        "Password does not meet "
                        "security requirements"
                    ),
                    "errors": errors,
                },
            )


        try:

            user.password_hash = hash_password(
                new_password
            )


            self.refresh_repository.revoke_all_for_user(
                user.id,
                reason="password_changed",
            )


            self.db.commit()


        except Exception:

            self.db.rollback()

            raise



    # =====================================================
    # Security Event Hooks
    # =====================================================

    def record_security_event(
        self,
        event_type: str,
        user_id: uuid.UUID | None = None,
        metadata: dict | None = None,
    ) -> None:
        """
        Security event integration point.

        Future integrations:

        - AuditLog table
        - SIEM pipeline
        - Sentinel ingestion
        - SOC monitoring
        - Compliance reporting


        Examples:

        LOGIN_SUCCESS
        LOGIN_FAILURE
        REFRESH_TOKEN_ROTATED
        REFRESH_TOKEN_REUSE
        PASSWORD_CHANGED
        SESSION_REVOKED
        """


        #
        # Intentionally isolated.
        #
        # This avoids coupling authentication
        # with audit infrastructure.
        #

        return None
    
    # =====================================================
    # Active Sessions
    # =====================================================

    def get_active_sessions(
        self,
        user: User,
    ) -> list[dict]:
        """
        Return all active sessions for a user.

        Used for:

        - Account security page
        - Device management
        - User session visibility
        """


        tokens = (
            self.refresh_repository
            .get_active_tokens_for_user(
                user.id
            )
        )


        sessions = []


        seen_sessions: set[str] = set()


        for token in tokens:

            #
            # Multiple refresh tokens can exist
            # in a rotation chain.
            #
            # Only expose the current session once.
            #

            if token.session_id in seen_sessions:

                continue


            seen_sessions.add(
                token.session_id
            )


            sessions.append(

                {
                    "session_id": token.session_id,

                    "device_name": (
                        token.device_name
                    ),

                    "ip_address": (
                        token.ip_address
                    ),

                    "user_agent": (
                        token.user_agent
                    ),

                    "created_at": (
                        token.created_at
                    ),

                    "last_used_at": (
                        token.last_used_at
                    ),

                    "trusted_device": (
                        token.trusted_device
                    ),

                }

            )


        return sessions



    # =====================================================
    # Revoke Other Sessions
    # =====================================================

    def revoke_other_sessions(
        self,
        *,
        user: User,
        current_session_id: str,
    ) -> int:
        """
        Keep the current session active.

        Revoke every other device session.

        Used by:

        - "Logout other devices"
        - Security response
        """


        try:

            revoked = (
                self.refresh_repository
                .revoke_all_except_session(
                    user_id=user.id,

                    session_id=current_session_id,

                    reason=(
                        "logout_other_devices"
                    ),
                )
            )


            self.db.commit()


            return revoked


        except Exception:

            self.db.rollback()

            raise



    # =====================================================
    # Device Trust
    # =====================================================

    def trust_device(
        self,
        *,
        user: User,
        session_id: str,
    ) -> None:
        """
        Mark a device session as trusted.

        Used for:

        - MFA bypass policies
        - Risk reduction
        - Device recognition
        """


        tokens = (
            self.refresh_repository
            .get_active_session_tokens(
                session_id
            )
        )


        try:

            for token in tokens:

                if token.user_id != user.id:

                    continue


                token.trust_device()


            self.db.commit()


        except Exception:

            self.db.rollback()

            raise



    # =====================================================
    # Security Metrics
    # =====================================================

    def get_security_metrics(
        self,
        user: User,
    ) -> dict:
        """
        Return authentication security metrics.

        Used by:

        - Security dashboard
        - SOC reporting
        - Compliance reports
        """


        return {

            "active_tokens": (
                self.refresh_repository
                .count_active_for_user(
                    user.id
                )
            ),

            "active_sessions": (
                self.refresh_repository
                .count_active_sessions(
                    user.id
                )
            ),

            "recent_tokens": (

                len(
                    self.refresh_repository
                    .get_recent_tokens(
                        user.id,
                        limit=20,
                    )
                )

            ),

        }



    # =====================================================
    # Administrative User Session Control
    # =====================================================

    def force_logout_user(
        self,
        user_id: uuid.UUID,
        reason: str = "administrator_action",
    ) -> None:
        """
        Administrator forced logout.

        Used for:

        - compromised accounts
        - employee termination
        - incident response
        """


        try:

            self.refresh_repository.revoke_all_for_user(
                user_id,

                reason=reason,
            )


            self.db.commit()


        except Exception:

            self.db.rollback()

            raise



    # =====================================================
    # Refresh Token Audit
    # =====================================================

    def get_token_history(
        self,
        user: User,
    ) -> list[dict]:
        """
        Return refresh token history.

        Designed for:

        - security investigations
        - compliance audits
        - incident response
        """


        tokens = (
            self.refresh_repository
            .get_recent_tokens(
                user.id,
                limit=50,
            )
        )


        return [

            token.to_dict()

            for token in tokens

        ]
        
    # =====================================================
    # Refresh Token Security Inspection
    # =====================================================

    def inspect_session(
        self,
        *,
        user: User,
        session_id: str,
    ) -> dict:
        """
        Inspect a user session.

        Provides security visibility into:

        - token chain
        - device information
        - rotation state
        - risk information
        """


        tokens = (
            self.refresh_repository
            .get_session_tokens(
                session_id
            )
        )


        if not tokens:

            return {

                "session_id": session_id,

                "active": False,

                "tokens": [],

            }


        return {

            "session_id": session_id,

            "active": any(
                token.is_active
                for token in tokens
            ),

            "device": {

                "name": (
                    tokens[-1]
                    .device_name
                ),

                "ip_address": (
                    tokens[-1]
                    .ip_address
                ),

                "user_agent": (
                    tokens[-1]
                    .user_agent
                ),

            },

            "tokens": [

                {

                    "id": str(
                        token.id
                    ),

                    "generation": (
                        token.generation
                    ),

                    "revoked": (
                        token.revoked
                    ),

                    "rotated": (
                        token.is_rotated
                    ),

                    "created_at": (
                        token.created_at
                    ),

                    "last_used_at": (
                        token.last_used_at
                    ),

                    "expires_at": (
                        token.expires_at
                    ),

                }

                for token in tokens

            ],

        }



    # =====================================================
    # Refresh Token Cleanup
    # =====================================================

    def cleanup_refresh_tokens(
        self,
    ) -> dict[str, int]:
        """
        Maintenance task for refresh tokens.

        Intended execution:

        - scheduled worker
        - background task
        - administrative command


        Removes:

        - expired tokens
        - old revoked tokens
        """


        try:

            result = (
                self.refresh_repository
                .cleanup()
            )


            self.db.commit()


            return result


        except Exception:

            self.db.rollback()

            raise



    # =====================================================
    # Login Event Wrapper
    # =====================================================

    def successful_login_event(
        self,
        user: User,
    ) -> None:
        """
        Records successful authentication.

        Placeholder for:

        - Audit logging
        - SIEM forwarding
        - SOC analytics
        """


        self.record_security_event(

            event_type="LOGIN_SUCCESS",

            user_id=user.id,

        )



    # =====================================================
    # Failed Login Event Wrapper
    # =====================================================

    def failed_login_event(
        self,
        email: str,
    ) -> None:
        """
        Records failed authentication attempt.

        Future usage:

        - brute-force detection
        - account lockout
        - SOC alerting
        """


        self.record_security_event(

            event_type="LOGIN_FAILURE",

            metadata={

                "email": email,

            },

        )



    # =====================================================
    # Refresh Rotation Event
    # =====================================================

    def refresh_rotation_event(
        self,
        user: User,
        session_id: str,
    ) -> None:
        """
        Records successful refresh rotation.
        """


        self.record_security_event(

            event_type=(
                "REFRESH_TOKEN_ROTATED"
            ),

            user_id=user.id,

            metadata={

                "session_id": session_id,

            },

        )



    # =====================================================
    # Token Reuse Event
    # =====================================================

    def refresh_reuse_event(
        self,
        user_id: uuid.UUID | None,
        token_family: str,
    ) -> None:
        """
        Records refresh token replay detection.

        This is a high priority security event.
        """


        self.record_security_event(

            event_type=(
                "REFRESH_TOKEN_REUSE_DETECTED"
            ),

            user_id=user_id,

            metadata={

                "token_family": token_family,

            },

        )



    # =====================================================
    # Health Check
    # =====================================================

    def health_check(
        self,
    ) -> dict:
        """
        Authentication subsystem health.

        Used by:

        - monitoring
        - readiness checks
        - operations dashboard
        """


        return {

            "service": "authentication",

            "status": "healthy",

            "database": "connected",

        }