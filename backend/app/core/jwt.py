from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM = settings.JWT_ALGORITHM
SECRET_KEY = settings.JWT_SECRET_KEY


# ==========================================================
# Internal Helpers
# ==========================================================


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _create_token(
    *,
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    session_id: str | None = None,
    token_family: str | None = None,
    generation: int = 1,
    jwt_id: str | None = None,
) -> str:
    """
    Enterprise JWT creator.

    Access tokens contain:
        sub
        type
        jti
        iat
        exp

    Refresh tokens additionally contain:
        sid
        fam
        gen
    """

    now = _utcnow()

    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": jwt_id or str(uuid4()),
    }

    if token_type == "refresh":
        payload["sid"] = session_id or str(uuid4())
        payload["fam"] = token_family or str(uuid4())
        payload["gen"] = generation

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


# ==========================================================
# Token Creation
# ==========================================================


def create_access_token(
    *,
    subject: str,
) -> str:

    return _create_token(
        subject=subject,
        token_type="access",
        expires_delta=timedelta(
            minutes=settings.JWT_ACCESS_EXPIRE_MINUTES
        ),
    )


def create_refresh_token(
    *,
    subject: str,
    session_id: str | None = None,
    token_family: str | None = None,
    generation: int = 1,
) -> str:

    return _create_token(
        subject=subject,
        token_type="refresh",
        expires_delta=timedelta(
            days=settings.JWT_REFRESH_EXPIRE_DAYS
        ),
        session_id=session_id,
        token_family=token_family,
        generation=generation,
    )


def rotate_refresh_token(
    *,
    subject: str,
    session_id: str,
    token_family: str,
    generation: int,
) -> str:
    """
    Issue the next refresh token in an existing token family.
    """

    return create_refresh_token(
        subject=subject,
        session_id=session_id,
        token_family=token_family,
        generation=generation + 1,
    )


# ==========================================================
# Decode
# ==========================================================


def decode_token(
    token: str,
) -> dict[str, Any]:

    try:

        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

    except JWTError:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


# ==========================================================
# Validation
# ==========================================================


def get_subject(
    token: str,
) -> str:

    payload = decode_token(token)

    if payload.get("type") != "access":

        raise HTTPException(
            status_code=401,
            detail="Invalid access token",
        )

    subject = payload.get("sub")

    if not subject:

        raise HTTPException(
            status_code=401,
            detail="Invalid token subject",
        )

    return subject


def verify_refresh_token(
    token: str,
) -> dict[str, Any]:

    payload = decode_token(token)

    if payload.get("type") != "refresh":

        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token",
        )

    required = (
        "sub",
        "jti",
        "sid",
        "fam",
        "gen",
        "exp",
    )

    missing = [
        key
        for key in required
        if payload.get(key) is None
    ]

    if missing:

        raise HTTPException(
            status_code=401,
            detail=f"Refresh token missing claims: {', '.join(missing)}",
        )

    return payload


# ==========================================================
# Metadata
# ==========================================================


def get_refresh_token_details(
    token: str,
) -> dict[str, Any]:

    payload = verify_refresh_token(token)

    return {
        "user_id": payload["sub"],
        "jwt_id": payload["jti"],
        "session_id": payload["sid"],
        "token_family": payload["fam"],
        "generation": int(payload["gen"]),
        "expires": datetime.fromtimestamp(
            payload["exp"],
            tz=timezone.utc,
        ),
    }