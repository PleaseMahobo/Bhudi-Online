from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session


class ScimService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def provision_user(
        self,
        *,
        external_id: str,
        user_name: str,
        display_name: str | None = None,
        active: bool = True,
        emails: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "externalId": external_id,
            "userName": user_name,
            "displayName": display_name or user_name,
            "active": active,
            "emails": emails or [user_name],
        }
