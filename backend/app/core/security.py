from __future__ import annotations

import hashlib

from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.
    """
    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """
    Verify a plaintext password against a bcrypt hash.
    Returns False instead of raising if the stored hash is invalid.
    """
    try:
        return pwd_context.verify(
            plain_password,
            hashed_password,
        )
    except Exception:
        return False


def hash_refresh_token(token: str) -> str:
    """
    Returns a SHA-256 hash of a refresh token.

    The plaintext refresh token is never stored in the database.
    """
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()