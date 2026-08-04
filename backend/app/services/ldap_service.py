from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session


class LdapService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def build_connection_config(
        self,
        host: str,
        port: int = 389,
        base_dn: str = "",
        bind_dn: str = "",
        password: str = "",
        *,
        use_tls: bool = False,
    ) -> dict[str, Any]:
        return {
            "host": host,
            "port": port,
            "base_dn": base_dn,
            "bind_dn": bind_dn,
            "password": password,
            "use_tls": use_tls,
            "mode": "ldap",
        }

    def validate_connection_config(self, config: dict[str, Any]) -> dict[str, Any]:
        required_fields = ["host", "port", "base_dn", "bind_dn", "password"]
        missing = [field for field in required_fields if not str(config.get(field, "")).strip()]
        if "port" in config and isinstance(config["port"], int):
            if config["port"] <= 0:
                missing.append("port")
        return {
            "valid": not missing,
            "mode": str(config.get("mode", "ldap")),
            "required_fields": required_fields,
            "missing_fields": missing,
        }
