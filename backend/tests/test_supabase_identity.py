from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.services import supabase_identity


def fake_db(user_by_auth=None, user_by_email=None):
    db = Mock()
    db.scalar.side_effect = [user_by_auth, user_by_email]
    db.scalars.return_value.all.return_value = [user_by_email] if user_by_email else []
    return db


def fake_supabase(auth_id, email, *, verified=True):
    auth = Mock()
    auth.get_user.return_value = SimpleNamespace(user=SimpleNamespace(
        id=str(auth_id), email=email,
        email_confirmed_at="2026-01-01T00:00:00Z" if verified else None,
    ))
    return SimpleNamespace(auth=auth)


def test_supabase_identity_maps_existing_user_by_auth_id(monkeypatch):
    auth_id = uuid4()
    user = SimpleNamespace(id=uuid4(), email="user@example.com", supabase_auth_id=auth_id, tenant_id=None, active=True)
    db = fake_db(user_by_auth=user)
    monkeypatch.setattr(supabase_identity, "supabase", fake_supabase(auth_id, user.email))
    assert supabase_identity.resolve_supabase_user(db, "token") is user
    db.scalar.assert_called_once()


def test_supabase_identity_links_unique_existing_email(monkeypatch):
    auth_id = uuid4()
    user = SimpleNamespace(id=uuid4(), email="USER@example.com", supabase_auth_id=None, tenant_id=None, active=True)
    db = fake_db(user_by_auth=None, user_by_email=user)
    monkeypatch.setattr(supabase_identity, "supabase", fake_supabase(auth_id, "user@example.com"))
    assert supabase_identity.resolve_supabase_user(db, "token") is user
    assert user.supabase_auth_id == auth_id
    db.flush.assert_called_once()


def test_supabase_identity_rejects_unverified_email(monkeypatch):
    auth_id = uuid4()
    db = fake_db()
    monkeypatch.setattr(supabase_identity, "supabase", fake_supabase(auth_id, "user@example.com", verified=False))
    with pytest.raises(supabase_identity.SupabaseIdentityError, match="not verified"):
        supabase_identity.resolve_supabase_user(db, "token")


def test_supabase_identity_rejects_unmapped_user(monkeypatch):
    auth_id = uuid4()
    db = fake_db()
    monkeypatch.setattr(supabase_identity, "supabase", fake_supabase(auth_id, "missing@example.com"))
    with pytest.raises(supabase_identity.SupabaseIdentityError, match="unique Bhudi user"):
        supabase_identity.resolve_supabase_user(db, "token")


def test_supabase_identity_rejects_different_existing_link(monkeypatch):
    auth_id, old_id = uuid4(), uuid4()
    user = SimpleNamespace(id=uuid4(), email="user@example.com", supabase_auth_id=old_id, tenant_id=None, active=True)
    db = fake_db(user_by_auth=None, user_by_email=user)
    monkeypatch.setattr(supabase_identity, "supabase", fake_supabase(auth_id, user.email))
    with pytest.raises(supabase_identity.SupabaseIdentityError, match="different Supabase identity"):
        supabase_identity.resolve_supabase_user(db, "token")


def test_supabase_identity_rejects_inactive_user(monkeypatch):
    auth_id = uuid4()
    user = SimpleNamespace(id=uuid4(), email="disabled@example.com", supabase_auth_id=auth_id, tenant_id=None, active=False)
    db = fake_db(user_by_auth=user)
    monkeypatch.setattr(supabase_identity, "supabase", fake_supabase(auth_id, user.email))
    with pytest.raises(supabase_identity.SupabaseIdentityError, match="inactive"):
        supabase_identity.resolve_supabase_user(db, "token")
