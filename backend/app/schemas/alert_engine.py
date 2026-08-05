from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# =========================================================
# Escalation Policy Schemas
# =========================================================

class EscalationLevel(BaseModel):
    repeat_count: int = Field(..., ge=1, description="Number of occurrences before this level applies")
    severity: str = Field(..., description="Severity to apply (warning, critical, etc.)")
    notify: list[str] = Field(default_factory=list, description="Notification channels")


class EscalationPolicyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    levels: list[EscalationLevel] = Field(default_factory=list)
    enabled: bool = True


class EscalationPolicyCreate(EscalationPolicyBase):
    pass


class EscalationPolicyUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    levels: list[EscalationLevel] | None = None
    enabled: bool | None = None


class EscalationPolicyResponse(EscalationPolicyBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# Alert Rule Schemas
# =========================================================

class AlertRuleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None

    provider: str | None = None
    check_type: str | None = None
    target: str | None = None
    metric_name: str | None = None

    warning_threshold: float | None = None
    critical_threshold: float | None = None

    anomaly_enabled: bool = False
    anomaly_tolerance: float | None = None

    state_change_enabled: bool = True

    ai_suppression_enabled: bool = True
    maintenance_window_name: str | None = None

    escalation_policy_id: UUID | None = None

    enabled: bool = True
    priority: int = Field(default=100, ge=1)
    tags: dict[str, Any] | None = None


class AlertRuleCreate(AlertRuleBase):
    pass


class AlertRuleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None

    provider: str | None = None
    check_type: str | None = None
    target: str | None = None
    metric_name: str | None = None

    warning_threshold: float | None = None
    critical_threshold: float | None = None

    anomaly_enabled: bool | None = None
    anomaly_tolerance: float | None = None

    state_change_enabled: bool | None = None

    ai_suppression_enabled: bool | None = None
    maintenance_window_name: str | None = None

    escalation_policy_id: UUID | None = None

    enabled: bool | None = None
    priority: int | None = Field(None, ge=1)
    tags: dict[str, Any] | None = None


class AlertRuleResponse(AlertRuleBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
