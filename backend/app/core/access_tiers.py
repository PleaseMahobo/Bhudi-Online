"""Access helpers: MFA for privileged actions; seats control supportable devices.

Product rules:
  - Anyone can register (starter) without MFA
  - After payment: Download agent is available
  - Remote control and commands require MFA enabled
  - Only devices within paid seat count are supportable for technicians
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status

from app.core.dependencies import get_current_user
from app.models.user import User

PRIVILEGED_ROLES = {"admin", "operator", "technician", "msp_admin", "professional"}


def user_has_mfa(user: User) -> bool:
    return bool(getattr(user, "mfa_enabled", False))


def user_is_unpaid_starter(user: User) -> bool:
    """Starter account without an active paid subscription flag (if present)."""
    role = (getattr(user, "role", None) or "user").lower()
    if role in PRIVILEGED_ROLES:
        return False
    paid = getattr(user, "subscription_active", None)
    if paid is True:
        return False
    return True


def require_mfa_for_actions(user: User = Depends(get_current_user)) -> User:
    """Block Remote / Run command until MFA is enabled."""
    if user_has_mfa(user):
        return user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": "mfa_setup_required",
            "message": (
                "Multi-factor authentication is required before remote access or "
                "command execution. Complete MFA setup at /mfa/setup."
            ),
            "setup_path": "/mfa/setup",
        },
    )
