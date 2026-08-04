from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ManagedDeviceBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hostname: str
    platform: str
    ip_address: str | None = None
    status: str = "pending_approval"
    approved: bool = False
    tags: list[str] = Field(default_factory=list)
    extra_data: dict[str, Any] | None = None


class ManagedDeviceCreate(ManagedDeviceBase):
    pass


class ManagedDeviceResponse(ManagedDeviceBase):
    id: UUID
    group_id: UUID | None = None
    group_name: str | None = None


class DeviceGroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None


class DynamicDeviceGroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    criteria: dict[str, Any]


class DeviceTagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class DevicePolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    rules: dict[str, Any]


class ConfigurationProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    settings: dict[str, Any]


class MaintenanceWindowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    start: str
    end: str


class PatchRingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    tier: str


class PatchRolloutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    ring_id: UUID
    ring_name: str | None = None
    device_ids: list[str]
    status: str
