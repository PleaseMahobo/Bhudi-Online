import pytest

from app.services import supabase_identity


def test_invalid_supabase_token_is_rejected(db, monkeypatch):
    class Auth:
        def get_user(self, token):
            raise RuntimeError("invalid")

    monkeypatch.setattr(
        supabase_identity,
        "supabase",
        type("Supabase", (), {"auth": Auth()})(),
    )
    with pytest.raises(supabase_identity.SupabaseIdentityError, match="Invalid Supabase access token"):
        supabase_identity.resolve_supabase_user(db, "bad-token")
