"""Trial vs privileged access helpers.

Roadmap:
  - Anyone can register (trial) without MFA
  - Trial users may view dashboard / device inventory
  - Remote control, shell commands, and destructive ops require MFA enabled
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status

from app.core.dependencies import get_current_user
from app.models.user import User

PRIVILEGED_ROLES = {"admin", "operator", "technician", "msp_admin"}


def user_has_mfa(user: User) -> bool:
    return bool(getattr(user, "mfa_enabled", False))


def user_is_trial(user: User) -> bool:
    role = (getattr(user, "role", None) or "").lower()
    return role in {"trial", "user", ""} and not user_has_mfa(user)


def require_mfa_for_actions(user: User = Depends(get_current_user)) -> User:
    """Block privileged mutations until MFA is enabled.

    Admins who already have MFA pass. New trial accounts must complete /mfa/setup.
    """
    if user_has_mfa(user):
        return user

    role = (getattr(user, "role", None) or "").lower()
    # Legacy full admins without MFA column still allowed once explicitly admin —
    # but product policy is: require MFA for actions for everyone going forward.
    if role == "admin" and getattr(user, "totp_secret", None):
        # secret present but not enabled → still block
        pass

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": "mfa_setup_required",
            "message": (
                "Multi-factor authentication is required before remote access, "
                "command execution, or other privileged actions. "
                "Complete MFA setup at /mfa/setup."
            ),
            "setup_path": "/mfa/setup",
        },
    )
