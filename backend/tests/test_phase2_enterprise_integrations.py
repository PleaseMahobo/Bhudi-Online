from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core import bootstrap
from app.services.ldap_service import LdapService
from app.services.scim_service import ScimService
from app.services.sso_service import SsoService
from app.services.secrets_service import SecretsService


def _session_factory() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    bootstrap.engine = engine
    bootstrap.SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    bootstrap.initialize_database()
    return bootstrap.SessionLocal()


def test_sso_service_validates_supported_provider_config() -> None:
    service = SsoService(_session_factory())

    provider = service.create_provider(
        "Azure",
        "azure",
        {
            "tenant_id": "tenant-123",
            "client_id": "client-456",
            "client_secret": "secret-789",
        },
    )

    validation = service.validate_provider_config(provider.provider_type, provider.config)

    assert provider.provider_type == "azure"
    assert validation["valid"] is True
    assert validation["required_fields"] == ["tenant_id", "client_id", "client_secret"]


def test_ldap_service_builds_connection_settings_and_validates_connection() -> None:
    service = LdapService(_session_factory())

    config = service.build_connection_config(
        "ldap.example.com",
        389,
        "dc=example,dc=com",
        "cn=admin,dc=example,dc=com",
        "secret",
    )

    assert config["host"] == "ldap.example.com"
    assert config["port"] == 389
    assert config["base_dn"] == "dc=example,dc=com"

    validation = service.validate_connection_config(config)
    assert validation["valid"] is True
    assert validation["mode"] == "ldap"


def test_scim_service_builds_provisioning_payload() -> None:
    service = ScimService(_session_factory())

    payload = service.provision_user(
        external_id="user-1",
        user_name="jane@example.com",
        display_name="Jane Doe",
        active=True,
        emails=["jane@example.com"],
    )

    assert payload["schemas"] == ["urn:ietf:params:scim:api:messages:2.0:PatchOp"]
    assert payload["externalId"] == "user-1"
    assert payload["userName"] == "jane@example.com"
    assert payload["active"] is True


def test_secrets_service_exposes_backend_metadata() -> None:
    service = SecretsService(_session_factory())

    assert service.get_backend_name() in {"fernet", "xor"}
    assert service.get_key_length() >= 16
