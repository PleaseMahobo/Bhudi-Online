from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


PACKAGE_TYPES = ("msi", "exe", "chocolatey", "winget", "custom")
JOB_ACTIONS = ("install", "uninstall", "rollback")
JOB_STATUSES = (
    "pending",
    "queued",
    "running",
    "completed",
    "failed",
    "cancelled",
    "rolled_back",
)
TARGET_STATUSES = (
    "pending",
    "downloading",
    "installing",
    "success",
    "failed",
    "rolled_back",
    "skipped",
)


# ---------- Package (application repository) ----------

class SoftwarePackageBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    version: str = "1.0.0"
    publisher: str | None = None
    description: str | None = None
    package_type: str = Field(..., description="msi | exe | chocolatey | winget | custom")
    source_url: str | None = None
    file_name: str | None = None
    sha256: str | None = None
    file_size_bytes: int | None = None
    choco_id: str | None = None
    winget_id: str | None = None
    install_args: str | None = None
    uninstall_args: str | None = None
    uninstall_command: str | None = None
    success_exit_codes: list[int] | None = Field(default_factory=lambda: [0])
    requires_reboot: bool = False
    requires_elevation: bool = True
    timeout_seconds: int = Field(default=3600, ge=30)
    architecture: str | None = "any"
    is_active: bool = True
    tags: dict[str, Any] | None = None
    metadata_json: dict[str, Any] | None = None
    tenant_id: UUID | None = None


class SoftwarePackageCreate(SoftwarePackageBase):
    pass


class SoftwarePackageUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    version: str | None = None
    publisher: str | None = None
    description: str | None = None
    package_type: str | None = None
    source_url: str | None = None
    file_name: str | None = None
    sha256: str | None = None
    file_size_bytes: int | None = None
    choco_id: str | None = None
    winget_id: str | None = None
    install_args: str | None = None
    uninstall_args: str | None = None
    uninstall_command: str | None = None
    success_exit_codes: list[int] | None = None
    requires_reboot: bool | None = None
    requires_elevation: bool | None = None
    timeout_seconds: int | None = Field(None, ge=30)
    architecture: str | None = None
    is_active: bool | None = None
    tags: dict[str, Any] | None = None
    metadata_json: dict[str, Any] | None = None


class SoftwarePackageResponse(SoftwarePackageBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- Deployment job ----------

class DeploymentJobCreate(BaseModel):
    package_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    action: str = "install"
    device_ids: list[UUID] = Field(default_factory=list)
    hostnames: list[str] = Field(default_factory=list)
    created_by: str | None = None
    notes: str | None = None
    scheduled_at: datetime | None = None
    tenant_id: UUID | None = None
    tags: dict[str, Any] | None = None


class DeploymentJobUpdate(BaseModel):
    name: str | None = None
    notes: str | None = None
    status: str | None = None
    scheduled_at: datetime | None = None
    tags: dict[str, Any] | None = None


class DeploymentTargetResponse(BaseModel):
    id: UUID
    job_id: UUID
    device_id: UUID | None
    agent_id: UUID | None = None
    hostname: str | None
    status: str
    exit_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    error_message: str | None = None
    download_bytes: int | None = None
    duration_ms: int | None = None
    reboot_required: bool = False
    started_at: datetime | None = None
    finished_at: datetime | None = None
    reported_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeploymentJobResponse(BaseModel):
    id: UUID
    tenant_id: UUID | None
    package_id: UUID
    name: str
    action: str
    status: str
    created_by: str | None
    notes: str | None
    rollback_of_job_id: UUID | None
    scheduled_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None
    targets_total: int
    targets_success: int
    targets_failed: int
    targets_pending: int
    tags: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    targets: list[DeploymentTargetResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class DeploymentJobSummary(BaseModel):
    """Success reporting aggregate."""

    job_id: UUID
    status: str
    targets_total: int
    targets_success: int
    targets_failed: int
    targets_pending: int
    success_rate: float
    finished_at: datetime | None


# ---------- Agent / target reporting ----------

class TargetReportRequest(BaseModel):
    status: str
    exit_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    error_message: str | None = None
    download_bytes: int | None = None
    duration_ms: int | None = None
    reboot_required: bool = False


class DeploymentEventResponse(BaseModel):
    id: UUID
    job_id: UUID
    target_id: UUID | None
    level: str
    message: str
    detail: dict[str, Any] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RollbackRequest(BaseModel):
    created_by: str | None = None
    notes: str | None = None
    # If empty, roll back all successful targets from the original job
    device_ids: list[UUID] = Field(default_factory=list)
