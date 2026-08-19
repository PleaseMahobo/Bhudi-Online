import pytest
from types import SimpleNamespace
from unittest.mock import Mock

from app.services import supabase_identity


def test_invalid_supabase_token_is_rejected(monkeypatch):
    auth = Mock()
    auth.get_user.side_effect = RuntimeError("invalid")
    monkeypatch.setattr(
        supabase_identity,
        "supabase",
        SimpleNamespace(auth=auth),
    )

    with pytest.raises(
        supabase_identity.SupabaseIdentityError,
        match="Invalid Supabase access token",
    ):
        supabase_identity.resolve_supabase_user(Mock(), "bad-token")
