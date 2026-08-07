from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AIRootCauseRequest(BaseModel):
    tenant_id: UUID | None = None
    title: str
    symptoms: str
    context: dict[str, Any] | None = None


class AIScriptRequest(BaseModel):
    tenant_id: UUID | None = None
    goal: str
    platform: str = "powershell"
    constraints: str | None = None


class AIRemediationRequest(BaseModel):
    tenant_id: UUID | None = None
    issue: str
    environment: dict[str, Any] | None = None


class AITicketSummaryRequest(BaseModel):
    tenant_id: UUID | None = None
    ticket_id: UUID | None = None
    title: str
    description: str | None = None
    work_notes: list[str] | None = None


class AIKnowledgeSearchRequest(BaseModel):
    tenant_id: UUID | None = None
    query: str
    limit: int = 5


class AIPredictiveRequest(BaseModel):
    tenant_id: UUID | None = None
    target_type: str = "device"
    target_id: str
    metrics: dict[str, Any] | None = None
    horizon_hours: int = 72


class AICapacityRequest(BaseModel):
    tenant_id: UUID | None = None
    resource: str  # cpu | memory | disk | seats
    history: list[dict[str, Any]] = Field(default_factory=list)
    horizon_hours: int = 168


class AIRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID | None = None
    task_type: str
    model: str | None = None
    status: str
    input_json: dict[str, Any] | None = None
    output_json: dict[str, Any] | None = None
    error: str | None = None
    latency_ms: int | None = None
    created_at: datetime
    completed_at: datetime | None = None


class KnowledgeArticleCreate(BaseModel):
    slug: str
    title: str
    body: str
    tags: dict[str, Any] | None = None
    source: str = "manual"
    published: bool = True
    tenant_id: UUID | None = None


class KnowledgeArticleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID | None = None
    slug: str
    title: str
    body: str
    tags: dict[str, Any] | None = None
    source: str
    published: bool
    created_at: datetime
    updated_at: datetime


class PredictionRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID | None = None
    kind: str
    target_type: str | None = None
    target_id: str | None = None
    score: float | None = None
    horizon_hours: int | None = None
    summary: str | None = None
    details: dict[str, Any] | None = None
    created_at: datetime
