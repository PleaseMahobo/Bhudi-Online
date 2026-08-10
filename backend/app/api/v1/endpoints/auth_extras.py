"""Password reset endpoints under /auth."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, validate_password
from app.database.session import get_db
from app.schemas.auth import MessageResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth-extras"])

_password_reset_tokens: dict[str, dict] = {}


@router.post("/password-reset/request")
def password_reset_request(payload: dict, db: Session = Depends(get_db)):
    email = str(payload.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="email is required")
    service = AuthService(db)
    user = service.users.get_by_email(email)
    msg = "If an account exists for that email, password reset instructions were sent."
    if user is None:
        return {"message": msg}
    token = secrets.token_urlsafe(32)
    _password_reset_tokens[token] = {
        "email": email,
        "expires": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    out: dict = {"message": msg}
    if getattr(settings, "ALLOW_DEBUG_RESET_TOKEN", True):
        out["debug_token"] = token
        out["debug_reset_path"] = f"/reset-password?token={token}"
    return out


@router.post("/password-reset/confirm", response_model=MessageResponse)
def password_reset_confirm(payload: dict, db: Session = Depends(get_db)):
    token = str(payload.get("token") or "").strip()
    new_password = str(payload.get("new_password") or payload.get("password") or "")
    if not token or not new_password:
        raise HTTPException(status_code=400, detail="token and new_password are required")
    row = _password_reset_tokens.get(token)
    if not row or row["expires"] < datetime.now(timezone.utc):
        _password_reset_tokens.pop(token, None)
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    errors = validate_password(new_password)
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))
    service = AuthService(db)
    user = service.users.get_by_email(row["email"])
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    user.password_hash = hash_password(new_password)
    service.db.add(user)
    service.db.commit()
    _password_reset_tokens.pop(token, None)
    return MessageResponse(
        message="Password has been reset. You can sign in with your new password."
    )
