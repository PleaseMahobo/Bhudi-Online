from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt, JWTError

from fastapi import HTTPException, status

from app.core.config import settings



ALGORITHM = settings.JWT_ALGORITHM

SECRET_KEY = settings.JWT_SECRET_KEY



# --------------------------------------------------
# Internal token creator
# --------------------------------------------------

def _create_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
) -> str:


    now = datetime.now(
        timezone.utc
    )


    payload: dict[str, Any] = {

        "sub": subject,

        "type": token_type,

        "iat": now,

        "exp": now + expires_delta,

        "jti": subject + "-" + str(
            int(now.timestamp())
        ),
    }


    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )



# --------------------------------------------------
# Access token
# --------------------------------------------------

def create_access_token(
    subject: str,
) -> str:


    return _create_token(
        subject=subject,
        token_type="access",
        expires_delta=timedelta(
            minutes=settings.JWT_ACCESS_EXPIRE_MINUTES
        ),
    )



# --------------------------------------------------
# Refresh token
# --------------------------------------------------

def create_refresh_token(
    subject: str,
) -> str:


    return _create_token(
        subject=subject,
        token_type="refresh",
        expires_delta=timedelta(
            days=settings.JWT_REFRESH_EXPIRE_DAYS
        ),
    )



# --------------------------------------------------
# Decode JWT
# --------------------------------------------------

def decode_token(
    token: str,
) -> dict[str, Any]:

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[
                ALGORITHM
            ],
        )


        return payload


    except JWTError:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )



# --------------------------------------------------
# Extract user ID
# --------------------------------------------------

def get_subject(
    token: str,
) -> str:


    payload = decode_token(
        token
    )


    token_type = payload.get(
        "type"
    )


    if token_type != "access":

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )


    subject = payload.get(
        "sub"
    )


    if not subject:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )


    return subject



# --------------------------------------------------
# Refresh token validation
# --------------------------------------------------

def verify_refresh_token(
    token: str,
) -> dict[str, Any]:


    payload = decode_token(
        token
    )


    if payload.get(
        "type"
    ) != "refresh":


        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )


    if not payload.get(
        "sub"
    ):


        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )


    return payload



# --------------------------------------------------
# Refresh token metadata
# --------------------------------------------------

def get_refresh_token_details(
    token: str,
) -> dict[str, Any]:


    payload = verify_refresh_token(
        token
    )


    return {

        "user_id": payload["sub"],

        "expires": datetime.fromtimestamp(
            payload["exp"],
            tz=timezone.utc,
        ),

        "jti": payload.get(
            "jti"
        ),

    }