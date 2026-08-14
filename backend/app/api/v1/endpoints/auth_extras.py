"""Password reset and admin recovery endpoints under /auth."""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.password_reset_service import PasswordResetService

router = APIRouter(prefix="/auth", tags=["auth-extras"])


@router.post("/password-reset/request")
def password_reset_request(payload: dict, db: Session = Depends(get_db)):
    email = str(payload.get("email") or "").strip().lower()
    message = "If an account exists for that email, password reset instructions were sent."
    if not email:
        return {"message": message}

    try:
        PasswordResetService(db).request_reset(email)
    except RuntimeError:
        return {"message": message}

    return {"message": message}


@router.post("/password-reset/confirm")
def password_reset_confirm(payload: dict, db: Session = Depends(get_db)):
    token = str(payload.get("token") or "").strip()
    new_password = str(
        payload.get("new_password") or payload.get("password") or ""
    )
    if not token:
        raise HTTPException(status_code=400, detail="Missing reset token")
    if not new_password:
        raise HTTPException(status_code=400, detail="Missing new password")
    try:
        PasswordResetService(db).confirm_reset(token, new_password)
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Password reset failed: {type(exc).__name__}: {exc}",
        ) from exc
    return {"message": "Password has been reset. You can sign in with your new password."}


class EnsureAdminBody(BaseModel):
    email: str | None = None
    password: str | None = Field(default=None, min_length=12)


@router.post("/ensure-admin")
def ensure_admin(
    request: Request,
    db: Session = Depends(get_db),
    body: EnsureAdminBody | None = None,
):
    """Create or reset the bootstrap admin account.

    Requires header: X-Bootstrap-Secret matching env BHUDI_BOOTSTRAP_SECRET.
    """
    from app.core.security import hash_password
    from app.models.user import User

    expected = (os.getenv("BHUDI_BOOTSTRAP_SECRET") or "").strip()
    provided = (request.headers.get("X-Bootstrap-Secret") or "").strip()
    if not expected or provided != expected:
        raise HTTPException(status_code=403, detail="Forbidden")

    email = (
        (body.email if body and body.email else None)
        or os.getenv("BHUDI_ADMIN_EMAIL", "admin@example.com")
    ).strip().lower()
    password = (
        (body.password if body and body.password else None)
        or os.getenv("BHUDI_ADMIN_PASSWORD", "StrongPassword123!")
    )
    if not password or len(password) < 12:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 12 characters",
        )

    try:
        user = db.query(User).filter(User.email == email).first()
        created = False
        if user is None:
            user = User(
                email=email,
                password_hash=hash_password(password),
                first_name="System",
                last_name="Admin",
                role="admin",
                active=True,
            )
            db.add(user)
            created = True
        else:
            user.password_hash = hash_password(password)
            user.active = True
            user.role = "admin"
            if hasattr(user, "failed_login_attempts"):
                user.failed_login_attempts = 0
            if hasattr(user, "locked_until"):
                user.locked_until = None
        db.commit()
        return {"ok": True, "created": created, "email": email}
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"ensure-admin failed: {type(exc).__name__}: {exc}",
        ) from exc
