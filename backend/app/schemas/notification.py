from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotificationChannelCreate(BaseModel):
    channel_type: str
    name: str
    enabled: bool = True
    tenant_id: UUID | None = None
    config: dict[str, Any] | None = None
    notes: str | None = None


class NotificationChannelUpdate(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    config: dict[str, Any] | None = None
    notes: str | None = None


class NotificationChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID | None = None
    channel_type: str
    name: str
    enabled: bool
    config: dict[str, Any] | None = None
    last_used_at: datetime | None = None
    last_error: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class NotificationTemplateCreate(BaseModel):
    code: str
    name: str
    body: str
    subject: str | None = None
    channel_bodies: dict[str, Any] | None = None
    variables: dict[str, Any] | None = None
    enabled: bool = True
    tenant_id: UUID | None = None


class NotificationTemplateUpdate(BaseModel):
    name: str | None = None
    body: str | None = None
    subject: str | None = None
    channel_bodies: dict[str, Any] | None = None
    variables: dict[str, Any] | None = None
    enabled: bool | None = None


class NotificationTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID | None = None
    code: str
    name: str
    subject: str | None = None
    body: str
    channel_bodies: dict[str, Any] | None = None
    variables: dict[str, Any] | None = None
    enabled: bool
    created_at: datetime
    updated_at: datetime


class NotificationSendRequest(BaseModel):
    channel_id: UUID
    recipient: str
    subject: str | None = None
    body: str | None = None
    template_code: str | None = None
    template_vars: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class NotificationDeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    channel_id: UUID
    tenant_id: UUID | None = None
    template_id: UUID | None = None
    recipient: str
    subject: str | None = None
    body: str
    status: str
    attempts: int
    error: str | None = None
    provider_ref: str | None = None
    metadata_json: dict[str, Any] | None = Field(default=None, validation_alias="metadata")
    created_at: datetime
    sent_at: datetime | None = None
