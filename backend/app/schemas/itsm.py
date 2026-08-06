from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class TicketAssetLinkCreate(BaseModel):
    asset_id: UUID
    role: str = "primary"  # primary | related | impacted
    notes: str | None = None


class TicketAssetLinkResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    asset_id: UUID
    role: str
    linked_at: datetime
    notes: str | None = None
    # Optional denormalized asset summary
    asset_name: str | None = None
    asset_tag: str | None = None
    asset_status: str | None = None

    model_config = ConfigDict(from_attributes=True)


class WorkNoteCreate(BaseModel):
    body: str = Field(..., min_length=1)
    author: str | None = None
    is_public: bool = False


class WorkNoteResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    author: str | None
    body: str
    is_public: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ServiceTicketBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    description: str | None = None
    ticket_type: str = "incident"
    status: str = "open"
    priority: str = "medium"
    impact: str | None = None
    urgency: str | None = None
    category: str | None = None
    subcategory: str | None = None
    requester: str | None = None
    assignee: str | None = None
    assignment_group: str | None = None
    device_id: UUID | None = None
    incident_id: str | None = None
    contract_id: UUID | None = None
    source: str = "manual"
    source_ref: str | None = None
    sla_response_minutes: int | None = None
    sla_resolve_minutes: int | None = None
    tags: dict[str, Any] | None = None
    metadata_json: dict[str, Any] | None = None
    tenant_id: UUID | None = None


class ServiceTicketCreate(ServiceTicketBase):
    asset_ids: list[UUID] = Field(default_factory=list)
    asset_links: list[TicketAssetLinkCreate] = Field(default_factory=list)


class ServiceTicketUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=512)
    description: str | None = None
    ticket_type: str | None = None
    status: str | None = None
    priority: str | None = None
    impact: str | None = None
    urgency: str | None = None
    category: str | None = None
    subcategory: str | None = None
    requester: str | None = None
    assignee: str | None = None
    assignment_group: str | None = None
    device_id: UUID | None = None
    incident_id: str | None = None
    contract_id: UUID | None = None
    resolution: str | None = None
    sla_response_minutes: int | None = None
    sla_resolve_minutes: int | None = None
    tags: dict[str, Any] | None = None
    metadata_json: dict[str, Any] | None = None


class ServiceTicketResponse(ServiceTicketBase):
    id: UUID
    number: str
    resolution: str | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    sla_breached: bool = False
    created_at: datetime
    updated_at: datetime
    asset_links: list[TicketAssetLinkResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class AssetTicketCreateRequest(BaseModel):
    """Create an ITSM ticket from an asset context."""

    title: str = Field(..., min_length=1, max_length=512)
    description: str | None = None
    ticket_type: str = "incident"
    priority: str = "medium"
    category: str | None = None
    requester: str | None = None
    assignee: str | None = None
    # If true and ticket_type is maintenance/incident, set asset status to in_repair
    set_asset_in_repair: bool = False


class TicketStatusUpdate(BaseModel):
    status: str
    resolution: str | None = None
    actor: str | None = None
