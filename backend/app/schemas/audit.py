"""Pydantic schemas for audit trail API."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuditLogItem(BaseModel):
    """Single audit trail entry."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Audit entry UUID")
    tenant_id: str | None = Field(None, description="Tenant scope, if any")
    user_id: str | None = Field(None, description="Acting user UUID, if any")
    action: str | None = Field(
        None,
        description="Machine action key, e.g. billing.admin.force_activate",
    )
    resource: str | None = Field(
        None,
        description="Target resource identifier, e.g. tenant:<uuid> or user:<uuid>",
    )
    details: dict[str, Any] | None = Field(
        None, description="Structured context for the action"
    )
    created_at: datetime | None = Field(None, description="When the entry was recorded")


class AuditLogListResponse(BaseModel):
    """Paginated-style list of audit entries (newest first)."""

    items: list[AuditLogItem] = Field(
        default_factory=list,
        description="Audit entries ordered by created_at descending",
    )


class AuditLogCreateRequest(BaseModel):
    """Client-submitted audit event (authenticated user)."""

    action: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Action key, e.g. portal.settings.update",
        examples=["portal.settings.update"],
    )
    resource: str | None = Field(
        None,
        max_length=512,
        description="Optional resource identifier",
        examples=["settings:notifications"],
    )
    details: dict[str, Any] | None = Field(
        None,
        description="Optional structured payload",
        examples=[{"field": "email_alerts", "value": True}],
    )


class AuditLogCreateResponse(BaseModel):
    status: str = Field("recorded", description="Outcome of the write")
    id: str = Field(..., description="New audit entry UUID")
