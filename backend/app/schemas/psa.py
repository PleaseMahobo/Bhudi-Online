from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PSAProviderCatalogItem(BaseModel):
    provider_key: str
    display_name: str
    auth_modes: list[str] = Field(default_factory=list)
    docs_url: str | None = None
    required_config: list[str] = Field(default_factory=list)


class PSAConnectionCreate(BaseModel):
    provider_key: str
    display_name: str
    enabled: bool = True
    tenant_id: UUID | None = None
    config: dict[str, Any] | None = None
    webhook_secret: str | None = None
    notes: str | None = None


class PSAConnectionUpdate(BaseModel):
    display_name: str | None = None
    enabled: bool | None = None
    config: dict[str, Any] | None = None
    webhook_secret: str | None = None
    notes: str | None = None


class PSAConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID | None = None
    provider_key: str
    display_name: str
    enabled: bool
    config: dict[str, Any] | None = None
    last_sync_status: str | None = None
    last_sync_at: datetime | None = None
    last_sync_error: str | None = None
    last_tested_at: datetime | None = None
    webhook_secret: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class PSAConnectionTestResult(BaseModel):
    ok: bool
    provider_key: str
    message: str
    dry_run: bool = False
    details: dict[str, Any] | None = None


class PSATicketPushRequest(BaseModel):
    connection_id: UUID
    ticket_id: UUID
    force: bool = False


class PSATicketLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    connection_id: UUID
    ticket_id: UUID
    external_id: str
    external_key: str | None = None
    external_url: str | None = None
    external_status: str | None = None
    direction: str
    sync_status: str
    last_synced_at: datetime | None = None
    last_error: str | None = None
    metadata_json: dict[str, Any] | None = Field(default=None, validation_alias="metadata")
    created_at: datetime
    updated_at: datetime
    provider_key: str | None = None


class PSASyncEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    connection_id: UUID
    event_type: str
    direction: str
    external_event_id: str | None = None
    external_ticket_id: str | None = None
    status: str
    action: str | None = None
    error: str | None = None
    payload: dict[str, Any] | None = None
    received_at: datetime
    processed_at: datetime | None = None


class PSAWebhookResult(BaseModel):
    status: str
    action: str | None = None
    event_id: UUID | None = None
    duplicate: bool = False
