from __future__ import annotations

from uuid import UUID

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    ConfigDict,
)


# ==========================================================
# Password Rules
# ==========================================================

PASSWORD_MIN_LENGTH = 12


# ==========================================================
# Registration
# ==========================================================


class RegisterRequest(BaseModel):
    """
    User registration payload.
    """

    email: EmailStr

    password: str = Field(
        min_length=PASSWORD_MIN_LENGTH,
        description="Minimum 12 character password",
    )

    first_name: str | None = Field(
        default=None,
        max_length=100,
    )

    last_name: str | None = Field(
        default=None,
        max_length=100,
    )



# ==========================================================
# Login
# ==========================================================


class LoginRequest(BaseModel):
    """
    Authentication request.
    """

    email: EmailStr

    password: str

    mfa_code: str | None = Field(
        default=None,
        description="Optional TOTP code when MFA is enabled",
    )



# ==========================================================
# Refresh Token
# ==========================================================


class RefreshTokenRequest(BaseModel):
    """
    Refresh token payload.

    Token may also arrive via
    HttpOnly cookie.
    """

    refresh_token: str | None = None



# ==========================================================
# User Response
# ==========================================================


class UserResponse(BaseModel):
    """
    Public user representation.

    Never exposes:
    - password_hash
    - internal security fields
    """

    id: UUID

    email: EmailStr

    first_name: str | None

    last_name: str | None

    role: str

    active: bool


    model_config = ConfigDict(
        from_attributes=True,
    )



# ==========================================================
# Token Response
# ==========================================================


class TokenResponse(BaseModel):
    """
    Authentication token response.
    """

    access_token: str

    refresh_token: str

    token_type: str = "bearer"

    user: UserResponse

    session_id: UUID | None = None

    token_family: UUID | None = None



# ==========================================================
# Generic Success Response
# ==========================================================


class MessageResponse(BaseModel):

    message: str
