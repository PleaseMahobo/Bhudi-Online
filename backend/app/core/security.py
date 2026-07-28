from __future__ import annotations

import hashlib
import hmac
import secrets
import string
from typing import Final

from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerifyMismatchError,
)
from passlib.context import CryptContext

from app.core.config import settings

# ==========================================================
# Type Aliases
# ==========================================================

PasswordHash = str
RefreshTokenHash = str
APIKey = str

# ==========================================================
# Password Policy
# ==========================================================

MIN_PASSWORD_LENGTH: Final[int] = 12
MAX_PASSWORD_LENGTH: Final[int] = 128
DEFAULT_PASSWORD_LENGTH: Final[int] = 20

# ==========================================================
# Secret Defaults
# ==========================================================

DEFAULT_SECRET_BYTES: Final[int] = 32
API_KEY_PREFIX: Final[str] = "bhudi"

# ==========================================================
# Argon2 Configuration
# ==========================================================

password_hasher = PasswordHasher(
    memory_cost=settings.ARGON2_MEMORY_COST,
    time_cost=settings.ARGON2_TIME_COST,
    parallelism=settings.ARGON2_PARALLELISM,
    hash_len=settings.ARGON2_HASH_LENGTH,
    salt_len=settings.ARGON2_SALT_LENGTH,
)

# ==========================================================
# Legacy bcrypt Support
# ==========================================================

legacy_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)

# ==========================================================
# Password Hashing
# ==========================================================


def hash_password(
    password: str,
) -> PasswordHash:
    password = normalize_password(password)

    errors = validate_password(password)

    if errors:
        raise ValueError(
            "; ".join(errors)
        )

    return password_hasher.hash(password)


# ==========================================================
# Password Verification
# ==========================================================


def verify_password(
    plain_password: str,
    stored_hash: PasswordHash,
) -> bool:

    if not plain_password or not stored_hash:
        return False

    if len(plain_password) > MAX_PASSWORD_LENGTH:
        return False

    plain_password = normalize_password(
        plain_password
    )

    #
    # First attempt Argon2 verification
    #

    try:

        return password_hasher.verify(
            stored_hash,
            plain_password,
        )

    except VerifyMismatchError:

        return False

    except InvalidHashError:

        #
        # Not Argon2
        #

        pass

    #
    # Legacy bcrypt verification
    #

    try:

        return legacy_context.verify(
            plain_password,
            stored_hash,
        )

    except Exception:

        return False


# ==========================================================
# Password Migration
# ==========================================================


def needs_password_rehash(
    stored_hash: PasswordHash,
) -> bool:

    if not stored_hash:
        return False

    try:

        return password_hasher.check_needs_rehash(
            stored_hash
        )

    except InvalidHashError:

        #
        # bcrypt or unknown
        #

        return True


def verify_and_upgrade_password(
    plain_password: str,
    stored_hash: PasswordHash,
) -> tuple[
    bool,
    PasswordHash | None,
]:

    if not verify_password(
        plain_password,
        stored_hash,
    ):
        return (
            False,
            None,
        )

    if needs_password_rehash(
        stored_hash
    ):
        return (
            True,
            hash_password(
                plain_password
            ),
        )

    return (
        True,
        None,
    )


# ==========================================================
# Password Validation
# ==========================================================


def validate_password(
    password: str,
) -> list[str]:

    errors: list[str] = []

    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(
            f"Password must contain at least {MIN_PASSWORD_LENGTH} characters."
        )

    if len(password) > MAX_PASSWORD_LENGTH:
        errors.append(
            f"Password may not exceed {MAX_PASSWORD_LENGTH} characters."
        )

    if not any(
        c.isupper()
        for c in password
    ):
        errors.append(
            "Password must contain an uppercase letter."
        )

    if not any(
        c.islower()
        for c in password
    ):
        errors.append(
            "Password must contain a lowercase letter."
        )

    if not any(
        c.isdigit()
        for c in password
    ):
        errors.append(
            "Password must contain a numeric digit."
        )

    if not any(
        c in string.punctuation
        for c in password
    ):
        errors.append(
            "Password must contain a special character."
        )

    return errors


def password_is_valid(
    password: str,
) -> bool:

    return not validate_password(
        password
    )


# ==========================================================
# Password Quality
# ==========================================================


def password_score(
    password: str,
) -> int:

    score = 0

    score += min(
        len(password) * 4,
        40,
    )

    if any(c.isupper() for c in password):
        score += 15

    if any(c.islower() for c in password):
        score += 15

    if any(c.isdigit() for c in password):
        score += 15

    if any(c in string.punctuation for c in password):
        score += 15

    return min(
        score,
        100,
    )


password_strength = password_score


# ==========================================================
# Password Normalization
# ==========================================================


def normalize_password(
    password: str,
) -> str:

    if not password:
        return ""

    return password.strip()
    
# ==========================================================
# Refresh Token Hashing
# ==========================================================

def hash_refresh_token(
    refresh_token: str,
) -> RefreshTokenHash:
    """
    Hash a refresh token using an application secret.

    The plaintext refresh token is never stored.
    """

    if not refresh_token:
        raise ValueError(
            "Refresh token cannot be empty."
        )

    secret = settings.REFRESH_TOKEN_HASH_KEY

    return hmac.new(
        secret.encode("utf-8"),
        refresh_token.encode("utf-8"),
        hashlib.sha256,
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

    calculated_hash = hash_refresh_token(
        refresh_token
    )

    return hmac.compare_digest(
        calculated_hash,
        stored_hash,
    )


# ==========================================================
# Secure Comparison
# ==========================================================

def secure_compare(
    first: str,
    second: str,
) -> bool:
    """
    Constant-time comparison helper.
    """

    if not first or not second:
        return False

    return hmac.compare_digest(
        first,
        second,
    )


# ==========================================================
# Password Hash Inspection
# ==========================================================

def get_password_hash_algorithm(
    password_hash: str,
) -> str | None:
    """
    Identify the password hash algorithm.
    """

    if not password_hash:
        return None

    if password_hash.startswith("$argon2"):
        return "argon2"

    if (
        password_hash.startswith("$2a$")
        or password_hash.startswith("$2b$")
        or password_hash.startswith("$2y$")
    ):
        return "bcrypt"

    return None


def is_valid_password_hash(
    password_hash: str,
) -> bool:
    """
    Validate that a stored password hash is supported.
    """

    return (
        get_password_hash_algorithm(
            password_hash
        )
        is not None
    )


# ==========================================================
# Secure Password Generation
# ==========================================================

def generate_password(
    length: int = DEFAULT_PASSWORD_LENGTH,
) -> str:
    """
    Generate a password satisfying the Bhudi
    enterprise password policy.
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
# Secure Token Generation
# ==========================================================

def generate_secure_token(
    length: int = 64,
) -> str:
    """
    Generate a cryptographically secure random token.
    """

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
    Generate an API key.
    """

    return (
        f"{API_KEY_PREFIX}_"
        f"{secrets.token_urlsafe(32)}"
    )


def generate_secret(
    bytes_length: int = DEFAULT_SECRET_BYTES,
) -> str:
    """
    Generate a hexadecimal secret.
    """

    return secrets.token_hex(
        bytes_length
    )


# ==========================================================
# Module Public Interface
# ==========================================================

__all__ = [
    # Types
    "PasswordHash",
    "RefreshTokenHash",
    "APIKey",

    # Password hashing
    "hash_password",
    "verify_password",
    "needs_password_rehash",
    "verify_and_upgrade_password",

    # Password validation
    "validate_password",
    "password_is_valid",
    "password_score",
    "password_strength",
    "normalize_password",

    # Password inspection
    "get_password_hash_algorithm",
    "is_valid_password_hash",

    # Refresh tokens
    "hash_refresh_token",
    "verify_refresh_token_hash",

    # Secure utilities
    "secure_compare",
    "generate_password",
    "generate_secure_token",
    "generate_api_key",
    "generate_secret",
]