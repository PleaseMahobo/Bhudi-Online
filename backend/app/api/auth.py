from fastapi import APIRouter
from pydantic import BaseModel

from app.services.auth_service import AuthService


router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str


@router.post("/login")
def login(payload: LoginRequest):
    return AuthService.login(payload.username)