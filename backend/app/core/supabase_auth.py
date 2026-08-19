from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.dependencies import authentication_error, get_access_token
from app.database.session import get_db
from app.services.supabase_identity import SupabaseIdentityError, resolve_supabase_user


def get_supabase_user(
    request: Request,
    db: Session = Depends(get_db),
):
    token = get_access_token(request)
    try:
        return resolve_supabase_user(db, token)
    except SupabaseIdentityError as exc:
        raise authentication_error(str(exc)) from exc


def get_optional_supabase_user(
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        return get_supabase_user(request, db)
    except Exception:
        return None
