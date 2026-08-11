"""Password reset endpoints under /auth."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.password_reset_service import PasswordResetService

router = APIRouter(prefix="/auth", tags=["auth-extras"])


@router.post("/password-reset/request")
def password_reset_request(payload: dict, db: Session = Depends(get_db)):
    email = str(payload.get("email") or "").strip().lower()
    # Always return the same public response to prevent account enumeration.
    message = "If an account exists for that email, password reset instructions were sent."
    if not email:
        return {"message": message}

    try:
        PasswordResetService(db).request_reset(email)
    except RuntimeError:
        # Keep the public response generic; deployment logs contain the delivery failure.
        return {"message": message}

    return {"message": message}


@router.post("/password-reset/confirm")
def password_reset_confirm(payload: dict, db: Session = Depends(get_db)):
    token = str(payload.get("token") or "").strip()
    new_password = str(
        payload.get("new_password") or payload.get("password") or ""
    )
    PasswordResetService(db).confirm_reset(token, new_password)
    return {"message": "Password has been reset. You can sign in with your new password."}
