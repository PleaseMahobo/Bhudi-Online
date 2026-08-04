from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.device_management import (
    ConfigurationProfileResponse,
    DeviceGroupResponse,
    DevicePolicyResponse,
    DeviceTagResponse,
    DynamicDeviceGroupResponse,
    MaintenanceWindowResponse,
    ManagedDeviceResponse,
)
from app.services.device_management_service import DeviceManagementService

router = APIRouter()


class DeviceEnrollmentRequest(BaseModel):
    hostname: str
    platform: str
    ip: str | None = None
    tags: list[str] | None = None
    group_id: str | None = None


class GroupCreateRequest(BaseModel):
    name: str
    description: str | None = None


class DynamicGroupCreateRequest(BaseModel):
    name: str
    criteria: dict[str, Any]


class TagCreateRequest(BaseModel):
    name: str


class PolicyCreateRequest(BaseModel):
    name: str
    rules: dict[str, Any]


class ConfigurationProfileCreateRequest(BaseModel):
    name: str
    settings: dict[str, Any]


class MaintenanceWindowCreateRequest(BaseModel):
    name: str
    start: str
    end: str


def _service(db: Session = Depends(get_db)) -> DeviceManagementService:
    return DeviceManagementService(db)


@router.post("/enroll", response_model=ManagedDeviceResponse)
def enroll_device(payload: DeviceEnrollmentRequest, service: DeviceManagementService = Depends(_service)) -> ManagedDeviceResponse:
    print("DEBUG enroll service db", service.db.get_bind().url)
    device = service.enroll_device(
        hostname=payload.hostname,
        platform=payload.platform,
        ip_address=payload.ip,
        tags=payload.tags,
    )
    return ManagedDeviceResponse(
        id=device.id,
        hostname=device.hostname,
        platform=device.platform,
        ip_address=device.ip_address,
        status=device.status,
        tags=device.tags,
        approved=device.approved,
        group_id=device.group_id,
        group_name=device.group.name if device.group is not None else None,
    )


@router.get("/discovered", response_model=dict[str, list[ManagedDeviceResponse]])
def list_discovered_devices(service: DeviceManagementService = Depends(_service)) -> dict[str, list[ManagedDeviceResponse]]:
    devices = service.list_discovered_devices()
    return {"devices": [
        ManagedDeviceResponse(
            id=device.id,
            hostname=device.hostname,
            platform=device.platform,
            ip_address=device.ip_address,
            status=device.status,
            tags=device.tags,
            approved=device.approved,
            group_id=device.group_id,
            group_name=device.group.name if device.group is not None else None,
        )
        for device in devices
    ]}


@router.post("/devices/{device_id}/approve", response_model=ManagedDeviceResponse)
def approve_device(device_id: str, service: DeviceManagementService = Depends(_service)) -> ManagedDeviceResponse:
    device = service.approve_device(UUID(device_id))
    if device is None:
        return {"error": "device_not_found"}
    return ManagedDeviceResponse(
        id=device.id,
        hostname=device.hostname,
        platform=device.platform,
        ip_address=device.ip_address,
        status=device.status,
        tags=device.tags,
        approved=device.approved,
        group_id=device.group_id,
        group_name=device.group.name if device.group is not None else None,
    )


@router.post("/groups", response_model=DeviceGroupResponse)
def create_group(payload: GroupCreateRequest, service: DeviceManagementService = Depends(_service)) -> DeviceGroupResponse:
    group = service.create_group(name=payload.name, description=payload.description)
    return DeviceGroupResponse(id=group.id, name=group.name, description=group.description)


@router.post("/dynamic-groups", response_model=DynamicDeviceGroupResponse)
def create_dynamic_group(payload: DynamicGroupCreateRequest, service: DeviceManagementService = Depends(_service)) -> DynamicDeviceGroupResponse:
    group = service.create_dynamic_group(name=payload.name, criteria=payload.criteria)
    return DynamicDeviceGroupResponse(id=group.id, name=group.name, criteria=group.criteria)


@router.post("/tags", response_model=DeviceTagResponse)
def create_tag(payload: TagCreateRequest, service: DeviceManagementService = Depends(_service)) -> DeviceTagResponse:
    tag = service.create_tag(name=payload.name)
    return DeviceTagResponse(id=tag.id, name=tag.name)


@router.post("/policies", response_model=DevicePolicyResponse)
def create_policy(payload: PolicyCreateRequest, service: DeviceManagementService = Depends(_service)) -> DevicePolicyResponse:
    policy = service.create_policy(name=payload.name, rules=payload.rules)
    return DevicePolicyResponse(id=policy.id, name=policy.name, rules=policy.rules)


@router.post("/configuration-profiles", response_model=ConfigurationProfileResponse)
def create_configuration_profile(payload: ConfigurationProfileCreateRequest, service: DeviceManagementService = Depends(_service)) -> ConfigurationProfileResponse:
    profile = service.create_configuration_profile(name=payload.name, settings=payload.settings)
    return ConfigurationProfileResponse(id=profile.id, name=profile.name, settings=profile.settings)


@router.post("/maintenance-windows", response_model=MaintenanceWindowResponse)
def create_maintenance_window(payload: MaintenanceWindowCreateRequest, service: DeviceManagementService = Depends(_service)) -> MaintenanceWindowResponse:
    window = service.create_maintenance_window(name=payload.name, start=payload.start, end=payload.end)
    return MaintenanceWindowResponse(id=window.id, name=window.name, start=window.start, end=window.end)
