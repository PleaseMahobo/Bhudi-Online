from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Framework
# ---------------------------------------------------------------------------

class ComplianceFrameworkCreate(BaseModel):
    framework_key: str = Field(..., min_length=2, max_length=64)
    display_name: str = Field(..., min_length=1, max_length=255)
    version: str | None = None
    enabled: bool = True
    tenant_id: UUID | None = None
    scope: dict[str, Any] | None = None
    notes: str | None = None


class ComplianceFrameworkUpdate(BaseModel):
    display_name: str | None = None
    version: str | None = None
    enabled: bool | None = None
    scope: dict[str, Any] | None = None
    notes: str | None = None


class ComplianceFrameworkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID | None = None
    framework_key: str
    display_name: str
    version: str | None = None
    enabled: bool
    scope: dict[str, Any] | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
