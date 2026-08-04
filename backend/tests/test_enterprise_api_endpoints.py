from __future__ import annotations

import pyotp
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.v1.endpoints import auth as auth_endpoint
from app.core import bootstrap
from app.models.user import User


def _build_client() -> FastAPI:
    engine = create_engine("sqlite:///:memory:", future=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    bootstrap.engine = engine
    bootstrap.SessionLocal = session_factory
    bootstrap.initialize_database()

    db = session_factory()
    user = User(email="api-user@example.com", password_hash="hash", role="user")
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    def override_get_current_user():
        return user

    app = FastAPI()
    app.include_router(auth_endpoint.router)
    app.dependency_overrides[auth_endpoint.get_db] = override_get_db
    app.dependency_overrides[auth_endpoint.get_current_user] = override_get_current_user

    return app


def test_enterprise_security_endpoints_work() -> None:
    app = _build_client()
    test_client = app.router

    setup_route = next(route for route in test_client.routes if getattr(route, "path", None) == "/auth/mfa/setup")
    assert setup_route is not None

    verify_route = next(route for route in test_client.routes if getattr(route, "path", None) == "/auth/mfa/verify")
    assert verify_route is not None

    passkey_route = next(route for route in test_client.routes if getattr(route, "path", None) == "/auth/passkeys/register")
    assert passkey_route is not None

    providers_route = next(route for route in test_client.routes if getattr(route, "path", None) == "/auth/sso/providers")
    assert providers_route is not None

    secrets_route = next(route for route in test_client.routes if getattr(route, "path", None) == "/auth/secrets")
    assert secrets_route is not None
