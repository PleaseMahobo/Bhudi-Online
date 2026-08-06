from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


PROVIDER_KEYS = (
    "windows_defender",
    "microsoft_defender_xdr",
    "threatlocker",
    "huntress",
    "sentinelone",
    "crowdstrike",
    "bitdefender",
    "sophos",
    "malwarebytes",
)


# ---------- Providers ----------

class SecurityProviderCreate(BaseModel):
    provider_key: str = Field(..., description="Canonical key, e.g. crowdstrike")
    display_name: str = Field(..., min_length=1, max_length=255)
    enabled: bool = True
    config: dict[str, Any] | None = None
    notes: str | None = None
    tenant_id: UUID | None = None


class SecurityProviderUpdate(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=255)
    enabled: bool | None = None
    config: dict[str, Any] | None = None
    notes: str | None = None
    last_sync_at: datetime | None = None
    last_sync_status: str | None = None
    last_sync_error: str | None = None


class SecurityProviderResponse(BaseModel):
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


# ---------- Agents ----------

class EndpointSecurityAgentCreate(BaseModel):
    provider_id: UUID
    device_id: UUID | None = None
    hostname: str | None = None
    external_agent_id: str | None = None
    agent_version: str | None = None
    status: str = "unknown"
    real_time_protection: bool | None = None
    definitions_up_to_date: bool | None = None
    last_scan_at: datetime | None = None
    last_seen_at: datetime | None = None
    details: dict[str, Any] | None = None


class EndpointSecurityAgentUpdate(BaseModel):
    external_agent_id: str | None = None
    agent_version: str | None = None
    status: str | None = None
    real_time_protection: bool | None = None
    definitions_up_to_date: bool | None = None
    last_scan_at: datetime | None = None
    last_seen_at: datetime | None = None
    details: dict[str, Any] | None = None
    hostname: str | None = None
    device_id: UUID | None = None


class EndpointSecurityAgentResponse(BaseModel):
    id: UUID
    device_id: UUID | None
    hostname: str | None
    provider_id: UUID
    external_agent_id: str | None
    agent_version: str | None
    status: str
    real_time_protection: bool | None
    definitions_up_to_date: bool | None
    last_scan_at: datetime | None
    last_seen_at: datetime | None
    details: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    provider_key: str | None = None
    provider_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ---------- Findings ----------

class SecurityFindingCreate(BaseModel):
    provider_id: UUID
    device_id: UUID | None = None
    hostname: str | None = None
    external_id: str | None = None
    title: str = Field(..., min_length=1, max_length=512)
    description: str | None = None
    severity: str = "medium"
    status: str = "open"
    category: str | None = None
    confidence: float | None = None
    detected_at: datetime | None = None
    raw: dict[str, Any] | None = None


class SecurityFindingUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    severity: str | None = None
    status: str | None = None
    category: str | None = None
    confidence: float | None = None
    resolved_at: datetime | None = None
    raw: dict[str, Any] | None = None


class SecurityFindingResponse(BaseModel):
    id: UUID
    provider_id: UUID
    device_id: UUID | None
    hostname: str | None
    external_id: str | None
    title: str
    description: str | None
    severity: str
    status: str
    category: str | None
    confidence: float | None
    detected_at: datetime | None
    resolved_at: datetime | None
    raw: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    provider_key: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ---------- Scores ----------

class EndpointSecurityScoreResponse(BaseModel):
    id: UUID
    device_id: UUID
    hostname: str | None
    score: int
    grade: str
    factors: dict[str, Any] | None = None
    open_critical: int
    open_high: int
    agents_healthy: int
    agents_total: int
    computed_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrgSecurityScoreResponse(BaseModel):
    """Roll-up posture for the tenant / fleet."""

    devices_scored: int
    average_score: float
    median_score: float
    grade_distribution: dict[str, int]
    open_critical_total: int
    open_high_total: int
    providers_enabled: int
    agents_healthy: int
    agents_total: int


class AgentIngestPayload(BaseModel):
    """
    Bulk / webhook-style ingest from a connector or RMM agent snapshot.
    Used to upsert agent health for a provider.
    """

    provider_key: str
    device_id: UUID | None = None
    hostname: str | None = None
    external_agent_id: str | None = None
    agent_version: str | None = None
    status: str = "unknown"
    real_time_protection: bool | None = None
    definitions_up_to_date: bool | None = None
    last_scan_at: datetime | None = None
    last_seen_at: datetime | None = None
    details: dict[str, Any] | None = None


class FindingIngestPayload(BaseModel):
    provider_key: str
    device_id: UUID | None = None
    hostname: str | None = None
    external_id: str | None = None
    title: str
    description: str | None = None
    severity: str = "medium"
    status: str = "open"
    category: str | None = None
    confidence: float | None = None
    detected_at: datetime | None = None
    raw: dict[str, Any] | None = None
