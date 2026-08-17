"""MFA setup / verify endpoints (QR emailed once; login uses 6-digit code only)."""
from __future__ import annotations

from io import BytesIO

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.services.email_service import EmailService
from app.services.mfa_service import MfaService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/mfa/setup", status_code=status.HTTP_200_OK)
def setup_mfa(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    force_new = (request.query_params.get("force_new") or "").lower() in ("1", "true", "yes")

    if (
        bool(getattr(current_user, "mfa_enabled", False))
        and getattr(current_user, "totp_secret", None)
        and not force_new
    ):
        return {
            "enabled": True,
            "email_sent": False,
            "already_enabled": True,
            "message": (
                "MFA is already enabled. Enter the 6-digit code from your authenticator "
                "at login. No new QR code was sent."
            ),
        }

    service = MfaService(db)
    secret, otpauth_uri = service.generate_secret(current_user, force_new=force_new)
    db.commit()

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=4,
    )
    qr.add_data(otpauth_uri)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    qr_buffer = BytesIO()
    image.save(qr_buffer, format="PNG")

    email_service = EmailService()
    if not email_service.configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MFA email delivery is not configured",
        )

    subject = "Bhudi RMM — Secure your account"
    body_text = (
        "Scan the attached QR code with your authenticator app, then enter the "
        "6-digit code in Bhudi once to finish MFA setup.\n\n"
        "If MFA is already set up, ignore this email and use your existing code at login.\n"
    )
    body_html = """
    <html><body style="margin:0;background:#0f172a;color:#e5e7eb;font-family:Arial,sans-serif">
      <div style="max-width:560px;margin:0 auto;padding:32px 20px">
        <div style="background:#111827;border:1px solid #334155;border-radius:20px;padding:32px;text-align:center">
          <h1 style="font-size:22px;margin:0 0 12px">Set up multi-factor authentication</h1>
          <p style="color:#cbd5e1;line-height:1.6">Scan once with your authenticator app. Later logins only need the 6-digit code.</p>
          <div style="background:#fff;border-radius:16px;padding:20px;margin:24px auto;width:fit-content">
            <img src="cid:bhudi-mfa-qr" alt="Bhudi MFA QR code" width="280" height="280" style="display:block" />
          </div>
        </div>
      </div>
    </body></html>
    """
    result = email_service.send(
        to=[current_user.email],
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        attachments=[("bhudi-mfa-qr.png", qr_buffer.getvalue(), "image/png", "bhudi-mfa-qr")],
    )
    if not result.ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not send MFA setup email",
        )

    return {
        "enabled": False,
        "email_sent": True,
        "already_enabled": False,
        "rotated": force_new,
        "message": (
            "New MFA secret issued — remove old Bhudi entries in your authenticator and scan the new QR."
            if force_new
            else "MFA setup email sent. Scan the QR once, then enter the 6-digit code to enable MFA."
        ),
    }


@router.post("/mfa/verify", status_code=status.HTTP_200_OK)
def verify_mfa(
    payload: dict[str, str],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = MfaService(db)
    code = (payload.get("code") or "").strip()
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing authenticator code")
    enabled = service.enable_totp(current_user, code)
    if not enabled:
        return {"enabled": False, "message": "Invalid authenticator code"}
    db.commit()
    db.refresh(current_user)
    return {
        "enabled": True,
        "message": "MFA is enabled. From now on you only need the 6-digit code at login — no new QR codes.",
    }
