from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ==========================================================
# Registration
# ==========================================================

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    first_name: str
    last_name: str


# ==========================================================
# Login
# ==========================================================

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ==========================================================
# Refresh Token
# ==========================================================

class RefreshTokenRequest(BaseModel):
    refresh_token: str


# ==========================================================
# User Response
# ==========================================================

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    first_name: str
    last_name: str
    role: str
    active: bool

    model_config = ConfigDict(from_attributes=True)


# ==========================================================
# Login / Refresh Response
# ==========================================================

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


# ==========================================================
# Generic Success Response
# ==========================================================

class MessageResponse(BaseModel):
    message: str