"""
backend/app/core/jwt.py

Production JWT utilities for Bhudi.

Part 1
- Configuration
- Exceptions
- Typed payload model
- Internal helpers

"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from jose import JWTError, ExpiredSignatureError, jwt

load_dotenv()

# ==========================================================
# Configuration
# ==========================================================

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is not configured.")

ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

ISSUER = os.getenv("JWT_ISSUER", "bhudi")

AUDIENCE = os.getenv("JWT_AUDIENCE", "bhudi-api")

TOKEN_VERSION = int(
    os.getenv("JWT_VERSION", "1")
)

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(
        "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
        "15",
    )
)

REFRESH_TOKEN_EXPIRE_DAYS = int(
    os.getenv(
        "JWT_REFRESH_TOKEN_EXPIRE_DAYS",
        "30",
    )
)

CLOCK_SKEW_SECONDS = int(
    os.getenv(
        "JWT_CLOCK_SKEW_SECONDS",
        "30",
    )
)

# ==========================================================
# Exceptions
# ==========================================================


class TokenError(Exception):
    """Base JWT exception."""


class InvalidTokenError(TokenError):
    """Token failed validation."""


class TokenExpiredError(TokenError):
    """Token has expired."""


class InvalidTokenTypeError(TokenError):
    """Access token used as refresh token or vice versa."""


class InvalidIssuerError(TokenError):
    """Unexpected issuer."""


class InvalidAudienceError(TokenError):
    """Unexpected audience."""


class InvalidTokenVersionError(TokenError):
    """Unsupported token version."""


# ==========================================================
# Typed Payload
# ==========================================================


@dataclass(slots=True, frozen=True)
class TokenPayload:
    sub: str
    token_type: str
    exp: datetime
    iat: datetime
    jti: str
    sid: str
    iss: str
    aud: str
    ver: int

    @property
    def is_access_token(self) -> bool:
        return self.token_type == "access"

    @property
    def is_refresh_token(self) -> bool:
        return self.token_type == "refresh"

    @property
    def expires_in(self) -> int:
        return max(
            0,
            int(
                (self.exp - utcnow()).total_seconds()
            ),
        )

    @property
    def is_expired(self) -> bool:
        return utcnow() >= self.exp

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TokenPayload":
        return cls(
            sub=str(payload["sub"]),
            token_type=str(payload["type"]),
            exp=datetime.fromtimestamp(
                payload["exp"],
                tz=timezone.utc,
            ),
            iat=datetime.fromtimestamp(
                payload["iat"],
                tz=timezone.utc,
            ),
            jti=str(payload["jti"]),
            sid=str(payload["sid"]),
            iss=str(payload["iss"]),
            aud=str(payload["aud"]),
            ver=int(payload["ver"]),
        )


# ==========================================================
# Internal Helpers
# ==========================================================


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def generate_jti() -> str:
    return str(uuid4())


def generate_session_id() -> str:
    return str(uuid4())


def access_token_expiry() -> datetime:
    return utcnow() + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )


def refresh_token_expiry() -> datetime:
    return utcnow() + timedelta(
        days=REFRESH_TOKEN_EXPIRE_DAYS
    )


def _build_payload(
    *,
    user_id: str,
    token_type: str,
    expires_at: datetime,
    session_id: str | None = None,
    jti: str | None = None,
) -> dict[str, Any]:
    """
    Internal helper used by all token creation methods.
    """

    issued = utcnow()

    return {
        "sub": user_id,
        "type": token_type,
        "iat": int(issued.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": jti or generate_jti(),
        "sid": session_id or generate_session_id(),
        "iss": ISSUER,
        "aud": AUDIENCE,
        "ver": TOKEN_VERSION,
}

def _encode(payload: dict[str, Any]) -> str:
    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    # ==========================================================
# Token Creation
# ==========================================================


def create_access_token(
    user_id: str,
    *,
    session_id: str | None = None,
    ) -> str:
    """
    Create a signed access token.

    Returns the encoded JWT.
    """

    payload = _build_payload(
        user_id=user_id,
        token_type="access",
        expires_at=access_token_expiry(),
        session_id=session_id,
    )

    return _encode(payload)


def create_refresh_token(
    user_id: str,
    *,
    session_id: str | None = None,
    jwt_id: str | None = None,
) -> str:
    """
    Create a signed refresh token.

    Returns the encoded JWT.
    """

    payload = _build_payload(
        user_id=user_id,
        token_type="refresh",
        expires_at=refresh_token_expiry(),
        session_id=session_id,
    )

    return _encode(payload)


# ==========================================================
# Decoding
# ==========================================================


def decode_token(
    token: str,
) -> dict[str, Any]:
    """
    Decode a JWT and validate its
    signature, issuer and audience.

    Raises TokenError subclasses on failure.
    """

    try:

        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            issuer=ISSUER,
            audience=AUDIENCE,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_aud": True,
                "verify_iss": True,
            },
            leeway=CLOCK_SKEW_SECONDS,
        )

    except ExpiredSignatureError as exc:
        raise TokenExpiredError(
            "Token has expired."
        ) from exc

    except JWTError as exc:
        raise InvalidTokenError(
            "Token validation failed."
        ) from exc


# ==========================================================
# Validation
# ==========================================================


def _validate_payload(
    payload: dict[str, Any],
    *,
    expected_type: str,
) -> TokenPayload:
    """
    Validate payload fields that are
    application specific.
    """

    if payload.get("type") != expected_type:
        raise InvalidTokenTypeError(
            f"Expected {expected_type} token."
        )

    if payload.get("iss") != ISSUER:
        raise InvalidIssuerError(
            "Invalid issuer."
        )

    if payload.get("aud") != AUDIENCE:
        raise InvalidAudienceError(
            "Invalid audience."
        )

    if int(payload.get("ver", 0)) != TOKEN_VERSION:
        raise InvalidTokenVersionError(
            "Unsupported token version."
        )

    return TokenPayload.from_dict(payload)


# ==========================================================
# Verification
# ==========================================================


def verify_access_token(
    token: str,
) -> TokenPayload:
    """
    Decode and validate an access token.
    """

    payload = decode_token(token)

    return _validate_payload(
        payload,
        expected_type="access",
    )


def verify_refresh_token(
    token: str,
    ) -> TokenPayload:
    """
    Decode and validate a refresh token.
    """

    payload = decode_token(token)

    return _validate_payload(
        payload,
        expected_type="refresh",
    )


# ==========================================================
# Metadata Helpers
# ==========================================================


def get_token_metadata(
    token: str,
    ) -> dict[str, str]:
    """
    Extract commonly used metadata.

    Useful for session tracking,
    logging and refresh-token storage.
    """

    payload = decode_token(token)

    return {
        "user_id": str(payload["sub"]),
        "jti": str(payload["jti"]),
        "session_id": str(payload["sid"]),
        "token_type": str(payload["type"]),
    }


def get_jti(
    token: str,
    ) -> str:
    """
    Return the token JTI.
    """

    return get_token_metadata(token)["jti"]


def get_session_id(
    token: str,
) -> str:
    """
    Return the session identifier.
    """

    return get_token_metadata(token)["session_id"]


def get_subject(
    token: str,
) -> str:
    """
    Return the subject (user id).
    """

    return get_token_metadata(token)["user_id"]

def get_refresh_token_details(
    token: str,
) -> dict[str, Any]:
    """
    Return refresh-token metadata required by AuthService.

    This helper exposes the information needed to persist,
    rotate and validate refresh tokens without requiring
    AuthService to understand JWT internals.
    """

    payload = verify_refresh_token(token)

    return {
        "user_id": payload.sub,
        "jwt_id": payload.jti,
        "session_id": payload.sid,
        "expires_at": payload.exp.replace(tzinfo=None),
    }

__all__ = [
    "TokenPayload",
    "TokenError",
    "InvalidTokenError",
    "TokenExpiredError",
    "InvalidTokenTypeError",
    "InvalidIssuerError",
    "InvalidAudienceError",
    "InvalidTokenVersionError",
    "create_access_token",
    "create_refresh_token",
    "verify_access_token",
    "verify_refresh_token",
    "decode_token",
    "get_refresh_token_details",
    "get_token_metadata",
    "get_jti",
    "get_session_id",
    "get_subject",
]