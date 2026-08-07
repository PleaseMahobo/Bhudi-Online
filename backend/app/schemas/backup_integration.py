from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
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
    verify: bool = True
    verification_policy: Literal["quick", "standard", "strict"] = "standard"
    # Max seconds allowed for verification after it starts (default applied in service)
    verification_timeout_seconds: int | None = Field(
        default=None, ge=60, le=86400, description="60s–24h; default 3600"
    )


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


# ---------- Restore verification workflow ----------

class VerificationCheckResult(BaseModel):
    check_id: str
    status: Literal["passed", "failed", "skipped"]
    message: str | None = None
    evidence: dict[str, Any] | None = None


class VerificationCheck(BaseModel):
    id: str
    name: str
    description: str | None = None
    required: bool = True
    status: Literal["pending", "running", "passed", "failed", "skipped"] = "pending"
    message: str | None = None
    evidence: dict[str, Any] | None = None
    started_at: str | None = None
    finished_at: str | None = None


class VerificationSummary(BaseModel):
    total: int
    passed: int
    failed: int
    skipped: int
    pending: int
    required_failed: int


class VerificationWorkflow(BaseModel):
    enabled: bool
    policy: Literal["quick", "standard", "strict"]
    status: Literal[
        "pending", "running", "passed", "failed", "skipped", "timed_out"
    ]
    started_at: str | None = None
    finished_at: str | None = None
    timeout_seconds: int | None = None
    deadline_at: str | None = None
    timed_out_at: str | None = None
    timeout_error: str | None = None
    checks: list[VerificationCheck] = []
    summary: VerificationSummary | None = None


class StartVerificationRequest(BaseModel):
    policy: Literal["quick", "standard", "strict"] | None = None
    force: bool = False
    timeout_seconds: int | None = Field(default=None, ge=60, le=86400)


class RunVerificationRequest(BaseModel):
    results: list[VerificationCheckResult] | None = None
    simulate_pass: bool = True


class VerificationTimeoutSweepResult(BaseModel):
    scanned: int
    timed_out: int
    restore_ids: list[UUID] = []


class BackupFleetSummary(BaseModel):
    providers_enabled: int
    resources_total: int
    resources_protected: int
    resources_at_risk: int
    jobs_success_24h: int
    jobs_failed_24h: int
    restores_open: int
    restores_verifying: int = 0
    restores_verify_failed: int = 0
