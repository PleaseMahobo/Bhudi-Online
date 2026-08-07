from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReportTemplateCreate(BaseModel):
    template_key: str = Field(..., min_length=2, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    report_type: str = Field(..., min_length=2, max_length=64)
    audience: str = "internal"
    default_format: str = "pdf"
    definition: dict[str, Any] | None = None
    tenant_id: UUID | None = None
    enabled: bool = True


class ReportTemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    audience: str | None = None
    default_format: str | None = None
    definition: dict[str, Any] | None = None
    enabled: bool | None = None


class ReportTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID | None = None
    template_key: str
    name: str
    description: str | None = None
    report_type: str
    audience: str
    default_format: str
    definition: dict[str, Any] | None = None
    is_system: bool
    enabled: bool
    created_at: datetime
    updated_at: datetime


class ReportDefinitionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    report_type: str = "custom"
    audience: str = "internal"
    config: dict[str, Any] = Field(default_factory=dict)
    tenant_id: UUID | None = None
    created_by: str | None = None


class ReportDefinitionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    audience: str | None = None
    config: dict[str, Any] | None = None


class ReportDefinitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID | None = None
    name: str
    description: str | None = None
    report_type: str
    audience: str
    config: dict[str, Any]
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime


class ReportRunCreate(BaseModel):
    name: str | None = None
    report_type: str | None = None
    template_id: UUID | None = None
    definition_id: UUID | None = None
    audience: str = "internal"
    format: str = Field("pdf", pattern="^(pdf|excel|csv|json)$")
    parameters: dict[str, Any] | None = None
    tenant_id: UUID | None = None
    triggered_by: str | None = None
    run_now: bool = True


class ReportRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID | None = None
    template_id: UUID | None = None
    definition_id: UUID | None = None
    schedule_id: UUID | None = None
    name: str
    report_type: str
    audience: str
    format: str
    status: str
    parameters: dict[str, Any] | None = None
    result_data: dict[str, Any] | None = None
    storage_uri: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None
    row_count: int | None = None
    triggered_by: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ReportScheduleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    template_id: UUID | None = None
    definition_id: UUID | None = None
    frequency: str = Field("weekly", pattern="^(hourly|daily|weekly|monthly|quarterly)$")
    cron_hint: dict[str, Any] | None = None
    format: str = "pdf"
    parameters: dict[str, Any] | None = None
    recipients: list[str] | None = None
    tenant_id: UUID | None = None
    enabled: bool = True
    created_by: str | None = None


class ReportScheduleUpdate(BaseModel):
    name: str | None = None
    frequency: str | None = None
    cron_hint: dict[str, Any] | None = None
    format: str | None = None
    parameters: dict[str, Any] | None = None
    recipients: list[str] | None = None
    enabled: bool | None = None


class ReportScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID | None = None
    template_id: UUID | None = None
    definition_id: UUID | None = None
    name: str
    frequency: str
    cron_hint: dict[str, Any] | None = None
    format: str
    parameters: dict[str, Any] | None = None
    recipients: list[Any] | None = None
    enabled: bool
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    last_run_status: str | None = None
    run_count: int
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime


class ExecutiveDashboard(BaseModel):
    devices_total: int = 0
    devices_online: int = 0
    devices_offline: int = 0
    open_alerts: int = 0
    critical_alerts: int = 0
    open_tickets: int = 0
    avg_security_score: float | None = None
    avg_compliance_score: float | None = None
    patch_compliance_pct: float | None = None
    backup_jobs_failed_24h: int = 0
    incidents_open: int = 0
    generated_at: datetime
    by_section: dict[str, Any] = Field(default_factory=dict)


class PatchComplianceSummary(BaseModel):
    devices_total: int = 0
    devices_compliant: int = 0
    devices_noncompliant: int = 0
    compliance_pct: float | None = None
    critical_missing: int = 0
    by_os: list[dict[str, Any]] = Field(default_factory=list)
    generated_at: datetime


class SecurityComplianceSummary(BaseModel):
    avg_endpoint_score: float | None = None
    open_findings: int = 0
    critical_findings: int = 0
    frameworks_scored: int = 0
    avg_framework_score: float | None = None
    generated_at: datetime
    by_framework: list[dict[str, Any]] = Field(default_factory=list)


class AssetReportSummary(BaseModel):
    assets_total: int = 0
    by_status: dict[str, int] = Field(default_factory=dict)
    by_type: dict[str, int] = Field(default_factory=dict)
    licenses_expiring_30d: int = 0
    warranty_expiring_90d: int = 0
    generated_at: datetime


class ReportCatalogItem(BaseModel):
    template_key: str
    name: str
    description: str | None = None
    report_type: str
    audience: str
    default_format: str
