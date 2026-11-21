from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.supabase_client import SUPABASE_URL
from app.models.user import User


class SupabaseReconciliationError(RuntimeError):
    """Raised when the trusted Supabase admin identity source is unavailable."""


@dataclass(frozen=True)
class ReconciliationResult:
    status: str
    dry_run: bool
    supabase_users: int
    bhudi_users: int
    matched: int
    repaired: int
    conflicts: int
    unchanged: int
    rows: list[dict[str, Any]]


def _email(value: str | None) -> str:
    return (value or "").strip().lower()


def _admin_client():
    secret = os.getenv("SUPABASE_SECRET_KEY", "").strip()
    if not SUPABASE_URL or not secret:
        raise SupabaseReconciliationError(
            "Supabase identity reconciliation requires SUPABASE_URL and SUPABASE_SECRET_KEY"
        )
    from supabase import create_client
    from supabase.lib.client_options import ClientOptions

    return create_client(
        SUPABASE_URL,
        secret,
        options=ClientOptions(auto_refresh_token=False, persist_session=False),
    )


def _list_confirmed_users(client) -> list[Any]:
    users: list[Any] = []
    page = 1
    per_page = 1000
    while True:
        response = client.auth.admin.list_users(page=page, per_page=per_page)
        page_users = list(getattr(response, "users", None) or [])
        users.extend(page_users)
        if len(page_users) < per_page:
            return users
        page += 1


def reconcile_supabase_identities(db: Session, *, apply: bool = False) -> ReconciliationResult:
    """Reconcile only verified, exact email matches.

    Existing Supabase auth IDs are authoritative. Conflicting auth IDs,
    duplicate email matches, and unconfirmed Supabase identities are never
    changed. Tenant, role, active state, and other Bhudi fields are preserved.
    """
    supabase_users = _list_confirmed_users(_admin_client())
    confirmed_by_email: dict[str, list[Any]] = {}
    for auth_user in supabase_users:
        email = _email(getattr(auth_user, "email", None))
        if email and getattr(auth_user, "email_confirmed_at", None):
            confirmed_by_email.setdefault(email, []).append(auth_user)

    bhudi_users = list(db.scalars(select(User).order_by(User.email.asc())).all())
    duplicate_bhudi_emails = {
        email
        for email, count in (
            (e, sum(1 for u in bhudi_users if _email(u.email) == e))
            for e in {_email(u.email) for u in bhudi_users}
        )
        if email and count > 1
    }

    rows: list[dict[str, Any]] = []
    repaired_users: list[User] = []
    matched = repaired = conflicts = unchanged = 0

    for user in bhudi_users:
        email = _email(user.email)
        base = {
            "user_id": str(user.id),
            "email": email,
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            "current_supabase_auth_id": str(user.supabase_auth_id) if user.supabase_auth_id else None,
        }

        if user.supabase_auth_id:
            candidates = confirmed_by_email.get(email, [])
            same_id = any(str(getattr(candidate, "id", "")) == str(user.supabase_auth_id) for candidate in candidates)
            if same_id:
                matched += 1
                rows.append({**base, "action": "unchanged", "reason": "existing_authoritative_identity"})
            else:
                conflicts += 1
                rows.append({**base, "action": "unchanged", "reason": "existing_auth_id_conflict_or_missing"})
            continue

        if email in duplicate_bhudi_emails:
            conflicts += 1
            rows.append({**base, "action": "unchanged", "reason": "duplicate_bhudi_email"})
            continue

        candidates = confirmed_by_email.get(email, [])
        if len(candidates) != 1:
            unchanged += 1
            reason = "no_verified_supabase_match" if not candidates else "duplicate_supabase_email"
            if candidates:
                conflicts += 1
            rows.append({**base, "action": "unchanged", "reason": reason})
            continue

        auth_id = UUID(str(getattr(candidates[0], "id")))
        matched += 1
        repaired += 1
        row = {**base, "action": "repair" if apply else "would_repair", "reason": "exact_verified_email_match", "supabase_auth_id": str(auth_id)}
        rows.append(row)
        if apply:
            user.supabase_auth_id = auth_id
            repaired_users.append(user)

    if apply and repaired_users:
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

    return ReconciliationResult(
        status="applied" if apply else "dry_run",
        dry_run=not apply,
        supabase_users=len(supabase_users),
        bhudi_users=len(bhudi_users),
        matched=matched,
        repaired=len(repaired_users) if apply else repaired,
        conflicts=conflicts,
        unchanged=unchanged,
        rows=rows,
    )


__all__ = ["SupabaseReconciliationError", "ReconciliationResult", "reconcile_supabase_identities"]
