from __future__ import annotations

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1.endpoints import auth as auth_endpoint
from app.api.v1.endpoints import auth_extras as auth_extras_endpoint
from app.api.v1.endpoints import mfa as mfa_endpoint
from app.core import bootstrap
from app.database.session import get_db
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
    app.include_router(mfa_endpoint.router)
    app.include_router(auth_extras_endpoint.router)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[auth_endpoint.get_current_user] = override_get_current_user
    app.dependency_overrides[mfa_endpoint.get_current_user] = override_get_current_user
    return app


def test_enterprise_security_endpoints_work() -> None:
    app = _build_client()
    paths = {getattr(route, "path", None) for route in app.router.routes}

    assert "/auth/login" in paths
    assert "/auth/refresh" in paths
    assert "/auth/mfa/setup" in paths
    assert "/auth/mfa/verify" in paths
    assert "/auth/password-reset/request" in paths
    assert "/auth/password-reset/confirm" in paths
