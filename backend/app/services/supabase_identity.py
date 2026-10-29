from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User
from app.core.supabase_client import supabase


class SupabaseIdentityError(Exception):
    """Raised when a Supabase identity cannot be mapped to Bhudi."""


def _verified_auth_identity(access_token: str) -> tuple[UUID, str]:
    """Validate the bearer token with Supabase and require a verified email."""
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
    # Supabase returns email_confirmed_at for verified email identities.
    # Never establish an application-account link from an unverified address.
    if not email or not getattr(auth_user, "email_confirmed_at", None):
        raise SupabaseIdentityError("Supabase email address is not verified")
    try:
        auth_id = UUID(str(auth_user.id))
    except (TypeError, ValueError, AttributeError) as exc:
        raise SupabaseIdentityError("Invalid Supabase identity") from exc
    return auth_id, email


def resolve_supabase_user(db: Session, access_token: str) -> User:
    """Resolve a verified Supabase identity to one unambiguous active Bhudi user.

    Existing links are authoritative. Email matching is only a safe legacy
    migration path when there is exactly one matching Bhudi account and the
    target is not already linked to a different identity. The database unique
    constraint on supabase_auth_id arbitrates concurrent link attempts.
    """
    auth_id, email = _verified_auth_identity(access_token)

    user = db.scalar(select(User).where(User.supabase_auth_id == auth_id))
    if user is not None:
        linked_email = (user.email or "").strip().lower()
        if linked_email != email:
            raise SupabaseIdentityError("Supabase identity email does not match its Bhudi mapping")
    else:
        matches = db.scalars(select(User).where(User.email == email).limit(2)).all()
        if len(matches) != 1:
            raise SupabaseIdentityError(
                "Supabase identity is not mapped to one unique Bhudi user"
            )
        user = matches[0]
        if user.supabase_auth_id is not None and user.supabase_auth_id != auth_id:
            raise SupabaseIdentityError("Bhudi account is linked to a different Supabase identity")
        user.supabase_auth_id = auth_id
        try:
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            raise SupabaseIdentityError("Supabase identity linkage conflict") from exc

    if not user.active:
        raise SupabaseIdentityError("Bhudi user account is inactive")
    return user
