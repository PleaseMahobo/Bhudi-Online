from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.supabase_client import supabase


class SupabaseIdentityError(Exception):
    """Raised when a Supabase identity cannot be mapped to Bhudi."""


async def resolve_supabase_user(
    db: AsyncSession,
    access_token: str,
) -> User:
    """Verify a Supabase access token and resolve its Bhudi user mapping."""
    if not supabase:
        raise SupabaseIdentityError("Supabase authentication is not configured")

    try:
        response: Any = supabase.auth.get_user(access_token)
        auth_user = getattr(response, "user", None)
    except Exception as exc:
        raise SupabaseIdentityError("Invalid Supabase access token") from exc

    if not auth_user or not getattr(auth_user, "id", None):
        raise SupabaseIdentityError("Invalid Supabase identity")

    auth_id = UUID(str(auth_user.id))
    email = (getattr(auth_user, "email", None) or "").strip().lower()

    result = await db.execute(
        select(User).where(User.supabase_auth_id == auth_id)
    )
    user = result.scalar_one_or_none()

    if user is None and email:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is not None:
            user.supabase_auth_id = auth_id
            await db.flush()

    if user is None:
        raise SupabaseIdentityError("Supabase identity is not mapped to a Bhudi user")

    if not user.active:
        raise SupabaseIdentityError("Bhudi user account is inactive")

    return user
