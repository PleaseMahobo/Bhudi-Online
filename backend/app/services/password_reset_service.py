from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, validate_password
from app.models.password_reset_token import PasswordResetToken
from app.services.auth_service import AuthService
from app.services.email_service import EmailService


class PasswordResetService:
    """One-time, database-backed password reset workflow."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.auth = AuthService(db)
        self.email = EmailService()

    @staticmethod
    def _secret() -> str:
        secret = settings.PASSWORD_RESET_SECRET or settings.JWT_SECRET_KEY
        if not secret:
            raise RuntimeError("PASSWORD_RESET_SECRET or JWT_SECRET_KEY must be configured")
        return secret

    @classmethod
    def _hash_token(cls, token: str) -> str:
        return hmac.new(
            cls._secret().encode("utf-8"),
            token.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def request_reset(self, email: str) -> None:
        email = email.strip().lower()
        user = self.auth.users.get_by_email(email)

        # Do not disclose whether an email exists.
        if user is None or not user.active:
            return

        now = datetime.now(timezone.utc)
        outstanding = (
            self.db.query(PasswordResetToken)
            .filter(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at > now,
            )
            .all()
        )
        for row in outstanding:
            row.used_at = now

        raw_token = secrets.token_urlsafe(48)
        token = PasswordResetToken(
            user_id=user.id,
            token_hash=self._hash_token(raw_token),
            expires_at=now + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
        )
        self.db.add(token)
        self.db.commit()

        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={raw_token}"
        display_name = user.first_name or "there"
        subject = "Reset your Bhudi RMM password"
        body_text = (
            f"Hello {display_name},\n\n"
            "We received a request to reset your Bhudi RMM password.\n\n"
            f"Reset your password here:\n{reset_url}\n\n"
            f"This link expires in {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes and can only be used once.\n\n"
            "If you did not request this, you can safely ignore this email.\n\n"
            "— Bhudi RMM\n"
            "A big brother's approach to Remote Monitoring, Management and Security"
        )
        body_html = f"""
<html><body style="font-family:Arial,sans-serif;background:#0f172a;padding:32px;color:#e2e8f0">
  <div style="max-width:560px;margin:auto;background:#111827;border:1px solid #334155;border-radius:16px;padding:32px">
    <h2 style="margin-top:0;color:#ffffff">Reset your Bhudi RMM password</h2>
    <p>Hello {display_name},</p>
    <p>We received a request to reset your Bhudi RMM password.</p>
    <p style="margin:28px 0"><a href="{reset_url}" style="display:inline-block;background:#4f46e5;color:#fff;text-decoration:none;padding:13px 22px;border-radius:10px;font-weight:600">Reset Password</a></p>
    <p>This link expires in <strong>{settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes</strong> and can only be used once.</p>
    <p>If you did not request this, you can safely ignore this email.</p>
    <hr style="border:0;border-top:1px solid #334155;margin:28px 0" />
    <p style="font-size:12px;color:#94a3b8">Bhudi RMM<br>A big brother's approach to Remote Monitoring, Management and Security</p>
  </div>
</body></html>
"""

        result = self.email.send(
            to=[user.email],
            subject=subject,
            body_text=body_text,
            body_html=body_html,
        )
        if not result.ok:
            # Do not leave a live reset token when email delivery fails.
            token.used_at = datetime.now(timezone.utc)
            self.db.commit()
            raise RuntimeError("Password reset email could not be delivered")

    def confirm_reset(self, token_value: str, new_password: str) -> None:
        token_hash = self._hash_token(token_value.strip())
        row = (
            self.db.query(PasswordResetToken)
            .filter(PasswordResetToken.token_hash == token_hash)
            .first()
        )
        if row is None or row.is_used or row.is_expired:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset link",
            )

        errors = validate_password(new_password)
        if errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="; ".join(errors),
            )

        user = self.auth.users.get_by_id(row.user_id)
        if user is None or not user.active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset link",
            )

        if self.auth._is_password_reused(user, new_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password has already been used recently",
            )

        new_hash = hash_password(new_password)
        history = list(getattr(user, "password_history", []) or [])
        history.insert(0, new_hash)
        user.password_hash = new_hash
        user.password_history = history[:5]
        user.password_changed_at = datetime.now(timezone.utc)

        # Password reset invalidates every active login session.
        self.auth.refresh_tokens.revoke_all_for_user(
            user.id,
            reason="password_reset",
        )

        row.used_at = datetime.now(timezone.utc)
        self.db.commit()
