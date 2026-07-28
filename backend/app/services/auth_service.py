from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.jwt import (
    create_access_token,
    create_refresh_token,
    extract_refresh_token_subject,
    get_refresh_token_details,
    verify_refresh_token,
)
from app.core.security import (
    hash_password,
    verify_and_upgrade_password,
    validate_password,
    hash_refresh_token,
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
    • Authentication
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

        email = email.strip().lower()

        if self.users.get_by_email(email):

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        password_errors = validate_password(password)

        if password_errors:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=password_errors,
            )

        user = User(
            email=email,
            password_hash=hash_password(password),
            first_name=first_name,
            last_name=last_name,
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

        email = email.strip().lower()

        user = self.users.get_by_email(email)

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

        password_valid, upgraded_hash = (
            verify_and_upgrade_password(
                password,
                user.password_hash,
            )
        )

        if not password_valid:

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        #
        # Transparent bcrypt → Argon2 migration
        #

        if upgraded_hash is not None:

            user.password_hash = upgraded_hash

        user.last_login_at = datetime.now(
            timezone.utc
        )

        user.failed_login_attempts = 0

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

        session_id = uuid.uuid4().hex

        token_family = uuid.uuid4().hex

        access_token = create_access_token(
            subject=str(user.id),
        )

        refresh_token = create_refresh_token(
            subject=str(user.id),
            session_id=session_id,
            token_family=token_family,
            generation=1,
        )

        refresh_details = get_refresh_token_details(
            refresh_token
        )

        refresh_record = RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(
                refresh_token
            ),
            jwt_id=refresh_details["jti"],
            session_id=session_id,
            token_family=token_family,
            generation=1,
            expires_at=refresh_details["expires_at"],
            ip_address=ip_address,
            user_agent=user_agent,
            device_name=device_name,
        )

        self.refresh_tokens.create(
            refresh_record
        )

        self.db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }
        
    # =====================================================
    # Refresh Token Rotation
    # =====================================================

    def refresh_access_token(
        self,
        refresh_token: str,
    ) -> dict[str, Any]:
        """
        Validate a refresh token, perform replay detection,
        rotate the token, and issue a new access/refresh pair.
        """

        #
        # Validate JWT signature, issuer, audience,
        # expiry, and token type.
        #
        verify_refresh_token(refresh_token)

        claims = get_refresh_token_details(
            refresh_token
        )

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

        #
        # Replay attack detection
        #
        if current_token.revoked:

            #
            # If a revoked refresh token is ever used
            # again we immediately revoke the entire
            # token family.
            #
            self.refresh_tokens.revoke_family(
                current_token.token_family,
                reason="refresh_token_replay",
            )

            self.db.commit()

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token replay detected",
            )

        if current_token.is_expired:

            current_token.revoke(
                "refresh_token_expired"
            )

            self.db.commit()

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired",
            )

        #
        # Create replacement session token
        #

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
            new_refresh_token
        )

        replacement = RefreshToken(
            user_id=current_token.user_id,
            token_hash=hash_refresh_token(
                new_refresh_token
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
            replacement
        )

        current_token.mark_used()

        current_token.rotate_to(
            replacement
        )

        self.db.commit()

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        }

    # =====================================================
    # Logout
    # =====================================================

    def logout(
        self,
        refresh_token: str,
    ) -> None:
        """
        Revoke the current refresh token.
        """

        token_hash = hash_refresh_token(
            refresh_token
        )

        token = self.refresh_tokens.get_by_token_hash(
            token_hash
        )

        if token is None:
            return

        token.revoke(
            "user_logout"
        )

        self.db.commit()

    # =====================================================
    # Logout All Sessions
    # =====================================================

    def logout_all(
        self,
        user: User,
    ) -> int:
        """
        Revoke every active refresh token
        belonging to the user.

        Returns the number of revoked sessions.
        """

        revoked = (
            self.refresh_tokens.revoke_all_for_user(
                user.id,
                reason="logout_all",
            )
        )

        self.db.commit()

        return revoked
    
    # =====================================================
    # Session Management
    # =====================================================

    def revoke_session(
        self,
        session_id: str,
        *,
        reason: str = "session_revoked",
    ) -> int:
        """
        Revoke every refresh token belonging to a session.

        Returns the number of revoked tokens.
        """

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
        """
        Revoke an entire refresh-token family.

        Used for replay detection, credential compromise,
        and administrative security actions.
        """

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
        """
        Return active session roots (generation 1)
        for the supplied user.
        """

        return self.refresh_tokens.get_active_sessions(
            user.id
        )

    # =====================================================
    # Account Helpers
    # =====================================================

    def change_password(
        self,
        *,
        user: User,
        current_password: str,
        new_password: str,
    ) -> None:
        """
        Change a user's password and invalidate
        all active refresh-token sessions.
        """

        valid, _ = verify_and_upgrade_password(
            current_password,
            user.password_hash,
        )

        if not valid:

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect",
            )

        errors = validate_password(
            new_password
        )

        if errors:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=errors,
            )

        user.password_hash = hash_password(
            new_password
        )

        user.password_changed_at = datetime.now(
            timezone.utc
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
            user_id
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
            email.strip().lower()
        )

    # =====================================================
    # Health
    # =====================================================

    @staticmethod
    def service_name() -> str:
        return "AuthService"

    @staticmethod
    def version() -> str:
        return "2.0.0-enterprise"
    
    # =====================================================
    # Internal Helpers
    # =====================================================

    @staticmethod
    def _normalize_email(
        email: str,
    ) -> str:
        """
        Normalize email addresses before storage
        and lookup.
        """

        return email.strip().lower()

    @staticmethod
    def _validate_password(
        password: str,
    ) -> None:
        """
        Validate password against the configured
        enterprise password policy.
        """

        errors = validate_password(
            password
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
        """
        Ensure the account is active and not locked.
        """

        if not user.active:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled",
            )

        if (
            user.locked_until
            and user.locked_until > datetime.now(timezone.utc)
        ):

            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="User account is temporarily locked",
            )

    @staticmethod
    def _update_successful_login(
        user: User,
    ) -> None:
        """
        Reset failed login counters after a
        successful authentication.
        """

        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.now(
            timezone.utc
        )

    @staticmethod
    def _record_failed_login(
        user: User,
        *,
        max_attempts: int = 5,
        lockout_minutes: int = 15,
    ) -> None:
        """
        Record a failed login attempt and lock the
        account when the configured threshold is
        exceeded.
        """

        user.failed_login_attempts += 1

        if user.failed_login_attempts >= max_attempts:

            user.locked_until = (
                datetime.now(timezone.utc)
                + timedelta(minutes=lockout_minutes)
            )

    # =====================================================
    # Cleanup
    # =====================================================

    def purge_expired_refresh_tokens(
        self,
    ) -> int:
        """
        Remove expired refresh tokens from the
        database.

        Returns the number of deleted rows.
        """

        deleted = (
            self.refresh_tokens.delete_expired()
        )

        self.db.commit()

        return deleted

    # =====================================================
    # Public Metadata
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

# ==========================================================
# Refresh Token Hashing
# ==========================================================

def hash_refresh_token(
    refresh_token: str,
) -> RefreshTokenHash:
    """
    Hash a refresh token prior to persistence.

    Refresh tokens already contain high entropy,
    therefore SHA-256 is appropriate for
    deterministic lookup without storing the
    plaintext token.
    """

    if not refresh_token:
        raise ValueError(
            "Refresh token cannot be empty."
        )

    return hashlib.sha256(
        refresh_token.encode("utf-8")
    ).hexdigest()


def verify_refresh_token_hash(
    refresh_token: str,
    stored_hash: RefreshTokenHash,
) -> bool:
    """
    Constant-time refresh token verification.
    """

    if not refresh_token or not stored_hash:
        return False

    calculated_hash = hash_refresh_token(
        refresh_token
    )

    return secrets.compare_digest(
        calculated_hash,
        stored_hash,
    )


# ==========================================================
# Secure Comparison Helpers
# ==========================================================

def secure_compare(
    left: str,
    right: str,
) -> bool:
    """
    Constant-time comparison helper.

    Suitable for API keys, verification
    codes and other secrets.
    """

    if not left or not right:
        return False

    return secrets.compare_digest(
        left,
        right,
    )


# ==========================================================
# Password Hash Inspection
# ==========================================================

def get_password_hash_algorithm(
    password_hash: PasswordHash,
) -> str | None:
    """
    Identify the algorithm used by a stored
    password hash.
    """

    if not password_hash:
        return None

    try:
        return pwd_context.identify(
            password_hash
        )
    except Exception:
        return None


def is_valid_password_hash(
    password_hash: PasswordHash,
) -> bool:
    """
    Returns True when the supplied hash
    is recognised by the configured
    password context.
    """

    return (
        get_password_hash_algorithm(
            password_hash
        )
        is not None
    )
    
# ==========================================================
# Refresh Token Hashing
# ==========================================================

def hash_refresh_token(
    refresh_token: str,
) -> RefreshTokenHash:
    """
    Hash a refresh token before database storage.

    Refresh tokens already contain high entropy, so a SHA-256
    digest is sufficient for deterministic lookup while ensuring
    the plaintext token is never persisted.
    """

    if not refresh_token:
        raise ValueError("Refresh token cannot be empty.")

    return hashlib.sha256(
        refresh_token.encode("utf-8")
    ).hexdigest()


def verify_refresh_token_hash(
    refresh_token: str,
    stored_hash: RefreshTokenHash,
) -> bool:
    """
    Constant-time verification of a refresh token.
    """

    if not refresh_token or not stored_hash:
        return False

    calculated_hash = hash_refresh_token(refresh_token)

    return hmac.compare_digest(
        calculated_hash,
        stored_hash,
    )


# ==========================================================
# Constant-Time Comparison
# ==========================================================

def secure_compare(
    first_value: str,
    second_value: str,
) -> bool:
    """
    Generic constant-time comparison helper.

    Suitable for API keys, verification codes,
    CSRF secrets, etc.
    """

    if not first_value or not second_value:
        return False

    return hmac.compare_digest(
        first_value,
        second_value,
    )


# ==========================================================
# Secure Token Generation
# ==========================================================

def generate_secure_token(
    length: int = 64,
) -> str:
    """
    Generate a cryptographically secure token.
    """

    if length <= 0:
        raise ValueError(
            "Token length must be greater than zero."
        )

    alphabet = (
        string.ascii_letters
        + string.digits
    )

    return "".join(
        secrets.choice(alphabet)
        for _ in range(length)
    )


def generate_api_key(
    prefix: str = API_KEY_PREFIX,
    secret_bytes: int = DEFAULT_SECRET_BYTES,
) -> APIKey:
    """
    Generate a Bhudi API key.

    Example:

        bhudi_xxxxxxxxxxxxxxxxxxxxxxxxx
    """

    if secret_bytes < 16:
        raise ValueError(
            "API key entropy is too low."
        )

    secret = secrets.token_urlsafe(secret_bytes)

    return f"{prefix}_{secret}"


# ==========================================================
# Secure Password Generation
# ==========================================================

def generate_password(
    length: int = DEFAULT_PASSWORD_LENGTH,
) -> str:
    """
    Generate a password that satisfies
    the Bhudi password policy.
    """

    if length < MIN_PASSWORD_LENGTH:
        raise ValueError(
            "Password length below minimum policy."
        )

    alphabet = (
        string.ascii_uppercase
        + string.ascii_lowercase
        + string.digits
        + string.punctuation
    )

    while True:

        candidate = "".join(
            secrets.choice(alphabet)
            for _ in range(length)
        )

        if password_is_valid(candidate):
            return candidate


# ==========================================================
# Module Public Interface
# ==========================================================

__all__ = [

    #
    # Password hashing
    #

    "hash_password",
    "verify_password",
    "password_needs_rehash",
    "verify_and_upgrade_password",

    #
    # Password validation
    #

    "validate_password",
    "password_is_valid",
    "password_score",
    "password_strength",

    #
    # Password generation
    #

    "generate_password",

    #
    # Refresh tokens
    #

    "hash_refresh_token",
    "verify_refresh_token_hash",

    #
    # Generic secrets
    #

    "generate_secure_token",
    "generate_api_key",

    #
    # Utilities
    #

    "secure_compare",
]

# ==========================================================
# Refresh Token Hashing
# ==========================================================

def hash_refresh_token(
    refresh_token: str,
) -> RefreshTokenHash:
    """
    Deterministically hash a refresh token using SHA-256.

    Refresh tokens already contain sufficient entropy, so a
    cryptographic hash is appropriate for indexed lookups while
    ensuring plaintext tokens are never persisted.
    """

    if not refresh_token:
        raise ValueError("Refresh token cannot be empty.")

    return hashlib.sha256(
        refresh_token.encode("utf-8")
    ).hexdigest()


def verify_refresh_token_hash(
    refresh_token: str,
    stored_hash: RefreshTokenHash,
) -> bool:
    """
    Constant-time verification of a refresh token hash.
    """

    if not refresh_token or not stored_hash:
        return False

    calculated = hash_refresh_token(
        refresh_token,
    )

    return secrets.compare_digest(
        calculated,
        stored_hash,
    )


# ==========================================================
# Secure Comparison Helpers
# ==========================================================

def secure_compare(
    first: str,
    second: str,
) -> bool:
    """
    Constant-time comparison helper for sensitive values.
    """

    if not first or not second:
        return False

    return secrets.compare_digest(
        first,
        second,
    )


# ==========================================================
# Secure Token Generation
# ==========================================================

def generate_secure_token(
    length: int = 64,
) -> str:
    """
    Generate a cryptographically secure random token.

    Suitable for:

    • password reset tokens
    • email verification
    • API secrets
    • CSRF secrets
    """

    if length < 16:
        raise ValueError(
            "Secure token length must be at least 16 characters."
        )

    alphabet = (
        string.ascii_letters
        + string.digits
    )

    return "".join(
        secrets.choice(alphabet)
        for _ in range(length)
    )


def generate_api_key() -> APIKey:
    """
    Generate a Bhudi API key.

    Example:

        bhudi_ab12cd34...
    """

    return (
        f"{API_KEY_PREFIX}_"
        f"{generate_secure_token(48)}"
    )
    
# ==========================================================
# Secure Password Generation
# ==========================================================

def generate_password(
    length: int = DEFAULT_PASSWORD_LENGTH,
) -> str:
    """
    Generate a cryptographically secure password that
    satisfies the Bhudi enterprise password policy.
    """

    if length < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password length must be at least {MIN_PASSWORD_LENGTH}."
        )

    alphabet = (
        string.ascii_uppercase
        + string.ascii_lowercase
        + string.digits
        + string.punctuation
    )

    while True:

        password = "".join(
            secrets.choice(alphabet)
            for _ in range(length)
        )

        if password_is_valid(password):
            return password


# ==========================================================
# Secret Generation
# ==========================================================

def generate_secret(
    bytes_length: int = DEFAULT_SECRET_BYTES,
) -> str:
    """
    Generate a cryptographically secure hexadecimal secret.
    """

    if bytes_length < 16:
        raise ValueError(
            "Secret length must be at least 16 bytes."
        )

    return secrets.token_hex(bytes_length)


# ==========================================================
# Module Public Interface
# ==========================================================

__all__ = [
    # Type aliases
    "PasswordHash",
    "RefreshTokenHash",
    "APIKey",

    # Password hashing
    "hash_password",
    "verify_password",
    "needs_password_rehash",
    "verify_and_upgrade_password",

    # Password policy
    "validate_password",
    "password_is_valid",
    "password_score",
    "password_strength",
    "normalize_password",

    # Password hash helpers
    "get_password_hash_algorithm",
    "is_valid_password_hash",

    # Refresh token hashing
    "hash_refresh_token",
    "verify_refresh_token_hash",

    # Secure comparison
    "secure_compare",

    # Generators
    "generate_password",
    "generate_secure_token",
    "generate_api_key",
    "generate_secret",
]