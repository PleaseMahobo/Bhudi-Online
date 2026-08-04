from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.user import User


class PasskeyService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_registration_challenge(self, user: User) -> dict[str, str]:
        return {"challenge": f"challenge-{user.id}"}

    def complete_registration(self, user: User, credential_id: str, credential_data: dict) -> bool:
        current = list(getattr(user, "passkeys", []) or [])
        if credential_id not in current:
            current.append(credential_id)
            user.passkeys = current
            self.db.add(user)
            self.db.flush()
        return True

    def verify_authentication(self, user: User, credential_id: str) -> bool:
        return credential_id in (getattr(user, "passkeys", []) or [])
