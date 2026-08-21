from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.core.supabase_auth import get_supabase_user
from app.models.user import User
from app.services.auth_service import AuthService


def test_supabase_me_returns_bhudi_identity(monkeypatch):
    user = User(id=uuid4(), email="user@example.com", password_hash="legacy", role="admin", active=True, tenant_id=uuid4())

    def override():
        return user

    app.dependency_overrides[get_supabase_user] = override
    try:
        response = TestClient(app).get("/api/v1/supabase-auth/me", headers={"Authorization": "Bearer test"})
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == str(user.id)
        assert body["email"] == user.email
        assert body["tenant_id"] == str(user.tenant_id)
    finally:
        app.dependency_overrides.pop(get_supabase_user, None)


def test_login_uses_supabase_identity_and_requires_mfa(monkeypatch):
    user = User(id=uuid4(), email="user@example.com", password_hash="not-the-supabase-password", role="admin", active=True, mfa_enabled=True)

    def override():
        return user

    def fail_if_local_password_is_used(*args, **kwargs):
        raise AssertionError("Bhudi local password authentication must not run")

    app.dependency_overrides[get_supabase_user] = override
    monkeypatch.setattr(AuthService, "authenticate", fail_if_local_password_is_used)
    try:
        response = TestClient(app).post("/api/v1/auth/login", json={})
        assert response.status_code == 403
        assert response.json()["detail"] == "mfa_required"
    finally:
        app.dependency_overrides.pop(get_supabase_user, None)


def test_login_promotes_supabase_session_after_valid_mfa(monkeypatch):
    user = User(id=uuid4(), email="user@example.com", password_hash="legacy", role="admin", active=True, mfa_enabled=True)

    def override():
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

    app.dependency_overrides[get_supabase_user] = override
    monkeypatch.setattr(AuthService, "login", fake_login)
    monkeypatch.setattr("app.services.mfa_service.MfaService", FakeMfaService)
    try:
        response = TestClient(app).post("/api/v1/auth/login", json={"mfa_code": "123456"})
        assert response.status_code == 200
        assert response.json()["access_token"] == "bhudi-access"
        assert "access_token=bhudi-access" in response.headers.get("set-cookie", "")
    finally:
        app.dependency_overrides.pop(get_supabase_user, None)
