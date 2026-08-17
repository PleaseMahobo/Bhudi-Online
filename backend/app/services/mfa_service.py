from __future__ import annotations

import pyotp
from sqlalchemy.orm import Session

from app.models.user import User


class MfaService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def provisioning_uri(self, user: User, secret: str) -> str:
        return pyotp.totp.TOTP(secret).provisioning_uri(
            name=user.email,
            issuer_name="Bhudi RMM",
        )

    def generate_secret(self, user: User, *, force_new: bool = False) -> tuple[str, str]:
        """Return (secret, otpauth_uri).

        Once a secret exists, reuse it so the same authenticator entry keeps
        working. Only rotate when force_new=True (explicit user request).
        """
        existing = getattr(user, "totp_secret", None)
        if existing and not force_new:
            return existing, self.provisioning_uri(user, existing)

        secret = pyotp.random_base32()
        user.totp_secret = secret
        user.mfa_enabled = False
        self.db.add(user)
        self.db.flush()
        return secret, self.provisioning_uri(user, secret)

    def enable_totp(self, user: User, code: str) -> bool:
        secret = getattr(user, "totp_secret", None)
        if not secret:
            return False
        if not pyotp.TOTP(secret).verify(code, valid_window=1):
            return False
        user.mfa_enabled = True
        self.db.add(user)
        self.db.flush()
        return True

    def verify_code(self, user: User, code: str) -> bool:
        secret = getattr(user, "totp_secret", None)
        if not secret:
            return False
        return bool(pyotp.TOTP(secret).verify(code, valid_window=1))

    def is_enabled(self, user: User) -> bool:
        return bool(getattr(user, "totp_secret", None)) and bool(
            getattr(user, "mfa_enabled", False)
        )
