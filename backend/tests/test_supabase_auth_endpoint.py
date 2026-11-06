from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services.supabase_identity import resolve_supabase_user
from app.models.user import User
from app.services.auth_service import AuthService


def test_supabase_me_returns_bhudi_identity(monkeypatch):
    user = User(id=uuid4(), email="user@example.com", password_hash="legacy", role="admin", active=True, tenant_id=uuid4())

    def fake_resolve(db, token):
        assert token == "test"
        return user

    monkeypatch.setattr("app.core.supabase_auth.resolve_supabase_user", fake_resolve)
    response = TestClient(app).get("/api/v1/supabase-auth/me", headers={"Authorization": "Bearer test"})
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(user.id)
    assert body["email"] == user.email
    assert body["tenant_id"] == str(user.tenant_id)


def test_login_uses_supabase_identity_and_requires_mfa(monkeypatch):
    user = User(id=uuid4(), email="user@example.com", password_hash="not-the-supabase-password", role="admin", active=True, mfa_enabled=True)

    def fake_resolve(db, token):
        assert token == "test"
        return user

    def fail_if_local_password_is_used(*args, **kwargs):
        raise AssertionError("Bhudi local password authentication must not run")

    monkeypatch.setattr("app.api.v1.endpoints.auth.resolve_supabase_user", fake_resolve)
    monkeypatch.setattr(AuthService, "authenticate", fail_if_local_password_is_used)
    response = TestClient(app).post(
        "/api/v1/auth/login",
        json={},
        headers={"Authorization": "Bearer test"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "mfa_required"


def test_login_promotes_supabase_session_after_valid_mfa(monkeypatch):
    user = User(id=uuid4(), email="user@example.com", password_hash="legacy", role="admin", active=True, mfa_enabled=True)

    def fake_resolve(db, token):
        assert token == "test"
        return user

    def fake_login(self, user, **kwargs):
        return {
            "access_token": "bhudi-access",
            "refresh_token": "bhudi-refresh",
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
                "active": user.active,
                "mfa_enabled": user.mfa_enabled,
            },
            "session_id": str(uuid4()),
            "token_family": str(uuid4()),
        }

    class FakeMfaService:
        def __init__(self, db):
            pass

        def verify_code(self, user, code):
            return code == "123456"

    monkeypatch.setattr("app.api.v1.endpoints.auth.resolve_supabase_user", fake_resolve)
    monkeypatch.setattr(AuthService, "login", fake_login)
    monkeypatch.setattr("app.services.mfa_service.MfaService", FakeMfaService)
    response = TestClient(app).post(
        "/api/v1/auth/login",
        json={"mfa_code": "123456"},
        headers={"Authorization": "Bearer test"},
    )
    assert response.status_code == 200
    assert response.json()["access_token"] == "bhudi-access"
    assert "access_token=bhudi-access" in response.headers.get("set-cookie", "")
