from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.auth_service import AuthService


def test_revoke_session_is_scoped_to_authenticated_user():
    service = AuthService.__new__(AuthService)
    service.db = Mock()
    service.refresh_tokens = Mock()
    service.refresh_tokens.revoke_session.return_value = 1

    user_id = uuid4()
    user = SimpleNamespace(id=user_id)

    result = service.revoke_session(user, "session-123")

    assert result == 1
    service.refresh_tokens.revoke_session.assert_called_once_with(
        user_id=user_id,
        session_id="session-123",
        reason="session_revoked",
    )
    service.db.commit.assert_called_once_with()


def test_refresh_rejects_disabled_user(monkeypatch):
    """The test token is synthetic, so bypass JWT signature validation here."""
    monkeypatch.setattr("app.services.auth_service.verify_refresh_token", lambda _: None)

    service = AuthService.__new__(AuthService)
    service.db = Mock()
    service.refresh_tokens = Mock()
    service.users = Mock()

    token = SimpleNamespace(
        revoked=False,
        is_expired=False,
        user_id=uuid4(),
        token_family=str(uuid4()),
        session_id=str(uuid4()),
        generation=1,
    )
    service.refresh_tokens.get_by_token_hash.return_value = token
    service.users.get_by_id.return_value = SimpleNamespace(active=False, locked_until=None)

    with pytest.raises(HTTPException) as exc:
        service.refresh_access_token("refresh-token")

    assert exc.value.status_code == 403
    assert exc.value.detail == "User account is disabled"
    service.refresh_tokens.create.assert_not_called()
