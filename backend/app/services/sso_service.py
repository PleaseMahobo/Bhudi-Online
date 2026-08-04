from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session


@dataclass
class SsoProvider:
    name: str
    provider_type: str
    config: dict[str, Any]
    enabled: bool = True


class SsoService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._providers: list[SsoProvider] = []

    def create_provider(self, name: str, provider_type: str, config: dict[str, Any]) -> SsoProvider:
        provider = SsoProvider(name=name, provider_type=provider_type, config=config)
        self._providers.append(provider)
        return provider

    def get_enabled_providers(self) -> list[SsoProvider]:
        return [provider for provider in self._providers if provider.enabled]

    def validate_provider_config(self, provider_type: str, config: dict[str, Any]) -> dict[str, Any]:
        required_fields = {
            "azure": ["tenant_id", "client_id", "client_secret"],
            "google": ["client_id", "client_secret"],
            "okta": ["org_url", "client_id", "client_secret"],
        }
        required = required_fields.get(provider_type.lower(), [])
        missing = [field for field in required if not str(config.get(field, "")).strip()]
        return {
            "valid": not missing,
            "provider_type": provider_type,
            "required_fields": required,
            "missing_fields": missing,
        }
