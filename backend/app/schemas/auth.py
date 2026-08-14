from __future__ import annotations

from uuid import UUID

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    ConfigDict,
)


PASSWORD_MIN_LENGTH = 12


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(
        min_length=PASSWORD_MIN_LENGTH,
        description="Minimum 12 character password",
    )
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    mfa_code: str | None = Field(
        default=None,
        description="TOTP code only when the account already has MFA enabled",
    )


class RefreshTokenRequest(BaseModel):
    refresh_token: str | None = None


class UserResponse(BaseModel):
    """Public user — never expose password_hash."""

    id: UUID
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    role: str = "trial"
    active: bool = True
    mfa_enabled: bool = False

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    user: dict | None = None
    session_id: UUID | str | None = None
    token_family: UUID | str | None = None

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message: str
