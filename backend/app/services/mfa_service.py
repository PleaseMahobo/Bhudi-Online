from __future__ import annotations

import pyotp
from sqlalchemy.orm import Session

from app.models.user import User


class MfaService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def generate_secret(self, user: User) -> tuple[str, str]:
        secret = pyotp.random_base32()
        user.totp_secret = secret
        user.mfa_enabled = True
        self.db.add(user)
        self.db.flush()
        uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="Bhudi")
        return secret, uri

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
        return pyotp.TOTP(secret).verify(code, valid_window=1)

    def is_enabled(self, user: User) -> bool:
        return bool(getattr(user, "totp_secret", None)) and bool(user.mfa_enabled)
