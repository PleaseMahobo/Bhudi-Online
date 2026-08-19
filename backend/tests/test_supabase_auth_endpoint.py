from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.core.supabase_auth import get_supabase_user
from app.models.user import User


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
