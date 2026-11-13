from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.core.supabase_client import supabase


class SupabaseIdentityError(Exception):
    """Raised when a Supabase identity cannot be mapped to Bhudi."""


def _verified_auth_identity(access_token: str) -> tuple[UUID, str, dict[str, Any]]:
    """Validate a Supabase access token and return its verified auth id/email."""
    if not supabase:
        raise SupabaseIdentityError("Supabase authentication is not configured")

    try:
        response: Any = supabase.auth.get_user(access_token)
        auth_user = getattr(response, "user", None)
    except Exception as exc:
        raise SupabaseIdentityError("Invalid Supabase access token") from exc

    if not auth_user or not getattr(auth_user, "id", None):
        raise SupabaseIdentityError("Invalid Supabase identity")

    email = (getattr(auth_user, "email", None) or "").strip().lower()
    if not email:
        raise SupabaseIdentityError("Supabase identity has no email")

    if not getattr(auth_user, "email_confirmed_at", None):
        raise SupabaseIdentityError("Supabase email is not verified")

    try:
        auth_id = UUID(str(auth_user.id))
    except (TypeError, ValueError) as exc:
        raise SupabaseIdentityError("Invalid Supabase identity id") from exc

    metadata = getattr(auth_user, "user_metadata", None) or {}
    if not isinstance(metadata, dict):
        metadata = {}

    return auth_id, email, metadata


def resolve_supabase_user(db: Session, access_token: str) -> User:
    """Verify a Supabase identity and resolve its Bhudi user mapping."""
    auth_id, email, _metadata = _verified_auth_identity(access_token)

    user = db.scalar(select(User).where(User.supabase_auth_id == auth_id))

    if user is None:
        matches = list(db.scalars(select(User).where(User.email == email)).all())
        if len(matches) > 1:
            raise SupabaseIdentityError("Supabase email matches multiple Bhudi users")
        if len(matches) == 1:
            user = matches[0]
            if user.supabase_auth_id is not None and user.supabase_auth_id != auth_id:
                raise SupabaseIdentityError("Bhudi account is linked to a different Supabase identity")
            user.supabase_auth_id = auth_id
            db.flush()

    if user is None:
        raise SupabaseIdentityError("Supabase identity is not mapped to a unique Bhudi user")

    if not user.active:
        raise SupabaseIdentityError("Bhudi user account is inactive")

    if (getattr(user, "email", "") or "").strip().lower() != email:
        raise SupabaseIdentityError("Supabase identity email does not match Bhudi account")

    return user
