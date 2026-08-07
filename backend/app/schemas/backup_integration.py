from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------- Providers ----------

class BackupProviderCreate(BaseModel):
    provider_key: str
    display_name: str = Field(..., min_length=1, max_length=255)
    enabled: bool = True
    config: dict[str, Any] | None = None
    notes: str | None = None
    tenant_id: UUID | None = None


class BackupProviderUpdate(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=255)
    enabled: bool | None = None
    config: dict[str, Any] | None = None
    notes: str | None = None
    last_sync_at: datetime | None = None
    last_sync_status: str | None = None
    last_sync_error: str | None = None


class BackupProviderResponse(BaseModel):
    id: UUID
    tenant_id: UUID | None
    provider_key: str
    display_name: str
    enabled: bool
    config: dict[str, Any] | None = None
    last_sync_at: datetime | None
    last_sync_status: str | None
    last_sync_error: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- Protected resources ----------

class ProtectedResourceCreate(BaseModel):
    provider_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    resource_type: str = "endpoint"
    device_id: UUID | None = None
    external_id: str | None = None
    hostname: str | None = None
    status: str = "unknown"
    last_backup_at: datetime | None = None
    last_backup_status: str | None = None
    last_backup_bytes: int | None = None
    rpo_hours: float | None = None
    details: dict[str, Any] | None = None


class ProtectedResourceUpdate(BaseModel):
    name: str | None = None
    resource_type: str | None = None
    device_id: UUID | None = None
    external_id: str | None = None
    hostname: str | None = None
    status: str | None = None
    last_backup_at: datetime | None = None
    last_backup_status: str | None = None
    last_backup_bytes: int | None = None
    rpo_hours: float | None = None
    details: dict[str, Any] | None = None


class ProtectedResourceResponse(BaseModel):
    id: UUID
    provider_id: UUID
    device_id: UUID | None
    name: str
    resource_type: str
    external_id: str | None
    hostname: str | None
    status: str
    last_backup_at: datetime | None
    last_backup_status: str | None
    last_backup_bytes: int | None
    rpo_hours: float | None
    details: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    provider_key: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ---------- Backup jobs ----------

class BackupJobCreate(BaseModel):
    provider_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    resource_id: UUID | None = None
    job_type: str = "full"
    schedule: str | None = None
    status: str = "pending"
    external_id: str | None = None
    details: dict[str, Any] | None = None


class BackupJobUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    bytes_processed: int | None = None
    files_processed: int | None = None
    duration_seconds: int | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    details: dict[str, Any] | None = None


class BackupJobResponse(BaseModel):
    id: UUID
    provider_id: UUID
    resource_id: UUID | None
    name: str
    job_type: str
    schedule: str | None
    status: str
    external_id: str | None
    bytes_processed: int | None
    files_processed: int | None
    duration_seconds: int | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    details: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    provider_key: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ---------- Restore jobs ----------

class RestoreJobCreate(BaseModel):
    provider_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    resource_id: UUID | None = None
    device_id: UUID | None = None
    restore_type: str = "file"
    source_point: str | None = None
    target_path: str | None = None
    auto_start: bool = True
    automation: dict[str, Any] | None = None
    requested_by: str | None = None
    details: dict[str, Any] | None = None


class RestoreJobUpdate(BaseModel):
    status: str | None = None
    bytes_restored: int | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    external_id: str | None = None
    automation: dict[str, Any] | None = None
    details: dict[str, Any] | None = None


class RestoreJobResponse(BaseModel):
    id: UUID
    provider_id: UUID
    resource_id: UUID | None
    device_id: UUID | None
    name: str
    restore_type: str
    source_point: str | None
    target_path: str | None
    status: str
    auto_start: bool
    automation: dict[str, Any] | None = None
    requested_by: str | None
    external_id: str | None
    bytes_restored: int | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    details: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    provider_key: str | None = None

    model_config = ConfigDict(from_attributes=True)


class BackupFleetSummary(BaseModel):
    providers_enabled: int
    resources_total: int
    resources_protected: int
    resources_at_risk: int
    jobs_success_24h: int
    jobs_failed_24h: int
    restores_open: int
