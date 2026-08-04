from __future__ import annotations

import pyotp
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core import bootstrap
from app.models.user import User
from app.services.mfa_service import MfaService
from app.services.passkey_service import PasskeyService
from app.services.sso_service import SsoService
from app.services.secrets_service import SecretsService


def _session_factory() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    bootstrap.engine = engine
    bootstrap.SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    bootstrap.initialize_database()
    return bootstrap.SessionLocal()


def test_totp_secret_can_be_enabled_and_verified() -> None:
    session = _session_factory()
    user = User(email="mfa@example.com", password_hash="hash", role="user")
    session.add(user)
    session.commit()
    session.refresh(user)

    service = MfaService(session)
    secret, uri = service.generate_secret(user)

    assert secret
    assert "otpauth://" in uri

    code = pyotp.TOTP(secret).now()
    assert service.enable_totp(user, code) is True
    assert service.is_enabled(user) is True
    assert service.verify_code(user, code) is True


def test_passkey_registration_and_authentication_work() -> None:
    session = _session_factory()
    user = User(email="passkey@example.com", password_hash="hash", role="user")
    session.add(user)
    session.commit()
    session.refresh(user)

    service = PasskeyService(session)
    challenge = service.create_registration_challenge(user)

    assert challenge["challenge"]
    assert service.complete_registration(user, "credential-1", {"id": "credential-1"}) is True
    assert service.verify_authentication(user, "credential-1") is True


def test_sso_provider_configuration_is_stored_and_validated() -> None:
    session = _session_factory()
    service = SsoService(session)

    provider = service.create_provider(
        "Azure",
        "azure",
        {
            "tenant_id": "tenant-1",
            "client_id": "client-1",
            "client_secret": "secret-1",
        },
    )

    assert provider.provider_type == "azure"
    assert service.get_enabled_providers()[0].name == "Azure"


def test_secrets_service_round_trip_is_encrypted() -> None:
    session = _session_factory()
    service = SecretsService(session)

    entry = service.store_secret("api-key", "super-secret", category="integration")

    assert entry.name == "api-key"
    assert service.get_secret("api-key") == "super-secret"
    assert service.get_secret_value("api-key") == "super-secret"
