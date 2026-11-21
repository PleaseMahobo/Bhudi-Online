from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.services import supabase_reconciliation


def fake_db(users):
    db = Mock()
    db.scalars.return_value.all.return_value = users
    return db


def fake_admin_client(users):
    client = Mock()
    client.auth.admin.list_users.return_value = SimpleNamespace(users=users)
    return client


def auth_user(auth_id, email, verified=True):
    return SimpleNamespace(
        id=str(auth_id),
        email=email,
        email_confirmed_at="2026-01-01T00:00:00Z" if verified else None,
    )


def test_reconciliation_dry_run_repairs_only_exact_verified_email(monkeypatch):
    auth_id = uuid4()
    user = SimpleNamespace(
        id=uuid4(), email="USER@example.com", supabase_auth_id=None,
        tenant_id=uuid4(), role="user", active=True,
    )
    monkeypatch.setattr(
        supabase_reconciliation,
        "_admin_client",
        lambda: fake_admin_client([auth_user(auth_id, "user@example.com")]),
    )

    result = supabase_reconciliation.reconcile_supabase_identities(fake_db([user]), apply=False)

    assert result.dry_run is True
    assert result.repaired == 1
    assert result.rows[0]["action"] == "would_repair"
    assert user.supabase_auth_id is None


def test_reconciliation_apply_preserves_tenant_and_rbac(monkeypatch):
    auth_id = uuid4()
    tenant_id = uuid4()
    user = SimpleNamespace(
        id=uuid4(), email="user@example.com", supabase_auth_id=None,
        tenant_id=tenant_id, role="enterprise_admin", active=True,
    )
    db = fake_db([user])
    monkeypatch.setattr(
        supabase_reconciliation,
        "_admin_client",
        lambda: fake_admin_client([auth_user(auth_id, user.email)]),
    )

    result = supabase_reconciliation.reconcile_supabase_identities(db, apply=True)

    assert result.status == "applied"
    assert result.repaired == 1
    assert user.supabase_auth_id == auth_id
    assert user.tenant_id == tenant_id
    assert user.role == "enterprise_admin"
    assert user.active is True
    db.commit.assert_called_once()


def test_reconciliation_rejects_duplicate_bhudi_email(monkeypatch):
    auth_id = uuid4()
    users = [
        SimpleNamespace(id=uuid4(), email="user@example.com", supabase_auth_id=None, tenant_id=uuid4()),
        SimpleNamespace(id=uuid4(), email="USER@example.com", supabase_auth_id=None, tenant_id=uuid4()),
    ]
    monkeypatch.setattr(
        supabase_reconciliation,
        "_admin_client",
        lambda: fake_admin_client([auth_user(auth_id, "user@example.com")]),
    )

    result = supabase_reconciliation.reconcile_supabase_identities(fake_db(users), apply=True)

    assert result.repaired == 0
    assert result.conflicts == 2
    assert all(user.supabase_auth_id is None for user in users)


def test_reconciliation_ignores_unverified_supabase_identity(monkeypatch):
    user = SimpleNamespace(
        id=uuid4(), email="user@example.com", supabase_auth_id=None, tenant_id=uuid4()
    )
    monkeypatch.setattr(
        supabase_reconciliation,
        "_admin_client",
        lambda: fake_admin_client([auth_user(uuid4(), user.email, verified=False)]),
    )

    result = supabase_reconciliation.reconcile_supabase_identities(fake_db([user]), apply=True)

    assert result.repaired == 0
    assert result.unchanged == 1
    assert user.supabase_auth_id is None
