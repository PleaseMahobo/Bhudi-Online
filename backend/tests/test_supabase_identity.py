from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.user import User
from app.services import supabase_identity


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_supabase_identity_maps_existing_user_by_auth_id(db, monkeypatch):
    auth_id = uuid4()
    user = User(email="user@example.com", password_hash="legacy", supabase_auth_id=auth_id, active=True)
    db.add(user)
    db.commit()

    class Auth:
        def get_user(self, token):
            return type("Response", (), {"user": type("AuthUser", (), {"id": str(auth_id), "email": "user@example.com"})()})()

    monkeypatch.setattr(supabase_identity, "supabase", type("Supabase", (), {"auth": Auth()})())
    resolved = supabase_identity.resolve_supabase_user(db, "token")
    assert resolved.id == user.id
    assert resolved.tenant_id is None


def test_supabase_identity_links_existing_email(db, monkeypatch):
    auth_id = uuid4()
    user = User(email="USER@example.com", password_hash="legacy", active=True)
    db.add(user)
    db.commit()

    class Auth:
        def get_user(self, token):
            return type("Response", (), {"user": type("AuthUser", (), {"id": str(auth_id), "email": "user@example.com"})()})()

    monkeypatch.setattr(supabase_identity, "supabase", type("Supabase", (), {"auth": Auth()})())
    resolved = supabase_identity.resolve_supabase_user(db, "token")
    assert resolved.id == user.id
    assert resolved.supabase_auth_id == auth_id


def test_supabase_identity_rejects_unmapped_user(db, monkeypatch):
    auth_id = uuid4()

    class Auth:
        def get_user(self, token):
            return type("Response", (), {"user": type("AuthUser", (), {"id": str(auth_id), "email": "missing@example.com"})()})()

    monkeypatch.setattr(supabase_identity, "supabase", type("Supabase", (), {"auth": Auth()})())
    with pytest.raises(supabase_identity.SupabaseIdentityError, match="not mapped"):
        supabase_identity.resolve_supabase_user(db, "token")


def test_supabase_identity_rejects_inactive_user(db, monkeypatch):
    auth_id = uuid4()
    db.add(User(email="disabled@example.com", password_hash="legacy", supabase_auth_id=auth_id, active=False))
    db.commit()

    class Auth:
        def get_user(self, token):
            return type("Response", (), {"user": type("AuthUser", (), {"id": str(auth_id), "email": "disabled@example.com"})()})()

    monkeypatch.setattr(supabase_identity, "supabase", type("Supabase", (), {"auth": Auth()})())
    with pytest.raises(supabase_identity.SupabaseIdentityError, match="inactive"):
        supabase_identity.resolve_supabase_user(db, "token")
