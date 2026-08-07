from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Framework
# ---------------------------------------------------------------------------

class ComplianceFrameworkCreate(BaseModel):
    framework_key: str = Field(..., min_length=2, max_length=64)
    display_name: str = Field(..., min_length=1, max_length=255)
    version: str | None = None
    enabled: bool = True
    tenant_id: UUID | None = None
    scope: dict[str, Any] | None = None
    notes: str | None = None


class ComplianceFrameworkUpdate(BaseModel):
    display_name: str | None = None
    version: str | None = None
    enabled: bool | None = None
    scope: dict[str, Any] | None = None
    notes: str | None = None


class ComplianceFrameworkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID | None = None
    framework_key: str
    display_name: str
    version: str | None = None
    enabled: bool
    scope: dict[str, Any] | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Control
# ---------------------------------------------------------------------------

class ComplianceControlCreate(BaseModel):
    framework_id: UUID
    control_id: str = Field(..., min_length=1, max_length=64)
    title: str = Field(..., min_length=1, max_length=512)
    description: str | None = None
    category: str | None = None
    severity: str = "medium"
    assessment_type: str = "manual"
    automation_hints: dict[str, Any] | None = None
    guidance: str | None = None


class ComplianceControlUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category: str | None = None
    severity: str | None = None
    assessment_type: str | None = None
    automation_hints: dict[str, Any] | None = None
    guidance: str | None = None


class ComplianceControlResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    framework_id: UUID
    control_id: str
    title: str
    description: str | None = None
    category: str | None = None
    severity: str
    assessment_type: str
    automation_hints: dict[str, Any] | None = None
    guidance: str | None = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Assessment
# ---------------------------------------------------------------------------

class ComplianceAssessmentCreate(BaseModel):
    framework_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    tenant_id: UUID | None = None
    triggered_by: str | None = None
    auto_start: bool = True


class ComplianceAssessmentUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    summary: dict[str, Any] | None = None
    error_message: str | None = None


class ComplianceAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    framework_id: UUID
    tenant_id: UUID | None = None
    name: str
    status: str
    triggered_by: str | None = None
    total_controls: int
    passed: int
    failed: int
    not_applicable: int
    not_assessed: int
    score: float | None = None
    grade: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    summary: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    framework_key: str | None = None


# ---------------------------------------------------------------------------
# Control result
# ---------------------------------------------------------------------------

class ControlResultUpsert(BaseModel):
    control_id: UUID
    status: str = Field(..., pattern="^(passed|failed|not_applicable|not_assessed|partial)$")
    score: float | None = Field(None, ge=0, le=100)
    findings: str | None = None
    remediation: str | None = None
    assessed_by: str | None = None
    details: dict[str, Any] | None = None


class ControlResultBatch(BaseModel):
    results: list[ControlResultUpsert]


class ControlResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assessment_id: UUID
    control_id: UUID
    status: str
    score: float | None = None
    findings: str | None = None
    remediation: str | None = None
    assessed_by: str | None = None
    assessed_at: datetime | None = None
    details: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    control_ref: str | None = None  # e.g. CIS-1.1
    control_title: str | None = None


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------

class ComplianceEvidenceCreate(BaseModel):
    control_id: UUID
    title: str = Field(..., min_length=1, max_length=512)
    evidence_type: str = "document"
    description: str | None = None
    assessment_id: UUID | None = None
    tenant_id: UUID | None = None
    device_id: UUID | None = None
    storage_uri: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None
    checksum: str | None = None
    collected_by: str | None = None
    expires_at: datetime | None = None
    metadata: dict[str, Any] | None = None


class ComplianceEvidenceUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    evidence_type: str | None = None
    storage_uri: str | None = None
    status: str | None = None
    expires_at: datetime | None = None
    metadata: dict[str, Any] | None = None


class ComplianceEvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    control_id: UUID
    assessment_id: UUID | None = None
    tenant_id: UUID | None = None
    device_id: UUID | None = None
    title: str
    evidence_type: str
    description: str | None = None
    storage_uri: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None
    checksum: str | None = None
    collected_by: str | None = None
    collected_at: datetime
    expires_at: datetime | None = None
    status: str
    metadata_json: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Score / summary
# ---------------------------------------------------------------------------

class ComplianceScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    framework_id: UUID
    tenant_id: UUID | None = None
    score: int
    grade: str
    factors: dict[str, Any] | None = None
    controls_passed: int
    controls_failed: int
    controls_total: int
    evidence_count: int
    last_assessment_id: UUID | None = None
    computed_at: datetime
    framework_key: str | None = None
    display_name: str | None = None


class ComplianceFleetSummary(BaseModel):
    frameworks_enabled: int
    controls_total: int
    assessments_open: int
    assessments_completed_30d: int
    evidence_count: int
    avg_score: float | None = None
    frameworks_below_threshold: int  # score < 70
    by_framework: list[dict[str, Any]] = Field(default_factory=list)
