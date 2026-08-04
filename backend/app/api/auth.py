from fastapi import APIRouter, HTTPException

from pydantic import BaseModel, EmailStr

from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/login")
def login(payload: LoginRequest):
    user = AuthService.login(payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {
        "access_token": "bhudi-demo-token",
        "token_type": "bearer",
        "user": user
    }