from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import string
from dataclasses import dataclass

from passlib.context import CryptContext


# ==========================================================
# Password Hashing
# ==========================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


# ==========================================================
# Password Policy
# ==========================================================

@dataclass(slots=True, frozen=True)
class PasswordPolicy:
    min_length: int = int(
        os.getenv("PASSWORD_MIN_LENGTH", "12")
    )

    require_uppercase: bool = True
    require_lowercase: bool = True
    require_number: bool = True
    require_special: bool = True


PASSWORD_POLICY = PasswordPolicy()

SPECIAL_CHARACTER_REGEX = re.compile(
    r"[!@#$%^&*()_\-+=\[\]{};:'\",.<>/?\\|`~]"
)


def validate_password(
    password: str,
    policy: PasswordPolicy = PASSWORD_POLICY,
) -> None:

    if len(password) < policy.min_length:
        raise PasswordPolicyError(
            f"Password must be at least "
            f"{policy.min_length} characters."
        )

    if (
        policy.require_uppercase
        and not any(c.isupper() for c in password)
    ):
        raise PasswordPolicyError(
            "Password must contain an uppercase character."
        )

    if (
        policy.require_lowercase
        and not any(c.islower() for c in password)
    ):
        raise PasswordPolicyError(
            "Password must contain a lowercase character."
        )

    if (
        policy.require_number
        and not any(c.isdigit() for c in password)
    ):
        raise PasswordPolicyError(
            "Password must contain a number."
        )

    if (
        policy.require_special
        and not SPECIAL_CHARACTER_REGEX.search(password)
    ):
        raise PasswordPolicyError(
            "Password must contain a special character."
        )

# ==========================================================
# Exceptions
# ==========================================================

class SecurityError(Exception):
    pass


class PasswordPolicyError(SecurityError):
    pass


# ==========================================================
# Agent API Keys
# ==========================================================

def hash_password(password: str) -> str:

    validate_password(password)

    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:

    return pwd_context.verify(
        plain_password,
        hashed_password,
    )

def sha256(value: str) -> str:

    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def hash_refresh_token(
    token: str,
) -> str:

    return sha256(token)


def constant_time_compare(
    left: str,
    right: str,
) -> bool:

    return hmac.compare_digest(
        left,
        right,
    )


def hash_api_key(
    api_key: str,
) -> str:

    return sha256(api_key)


def verify_api_key(
    provided_key: str,
    stored_hash: str,
) -> bool:

    return constant_time_compare(
        hash_api_key(provided_key),
        stored_hash,
    )

def generate_secure_token(
    length: int = 64,
) -> str:

    return secrets.token_urlsafe(length)


def generate_random_string(
    length: int = 32,
) -> str:

    alphabet = (
        string.ascii_letters
        + string.digits
    )

    return "".join(
        secrets.choice(alphabet)
        for _ in range(length)
    )


def generate_recovery_codes(
    count: int = 10,
) -> list[str]:

    codes = []

    for _ in range(count):

        code = (
            generate_random_string(4)
            + "-"
            + generate_random_string(4)
            + "-"
            + generate_random_string(4)
        )

        codes.append(code)

    return codes


__all__ = [
    "PasswordPolicy",
    "PasswordPolicyError",
    "validate_password",
    "hash_password",
    "verify_password",
    "hash_refresh_token",
    "hash_api_key",
    "verify_api_key",
    "generate_secure_token",
    "generate_random_string",
    "generate_recovery_codes",
    "constant_time_compare",
]