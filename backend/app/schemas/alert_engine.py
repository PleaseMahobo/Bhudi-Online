from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator


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
# Remediation action schemas (alert-driven)
# =========================================================

RemediationActionType = Literal[
    "run_script",
    "run_command",
    "inventory_refresh",
    "notify_only",
]


class RemediationAction(BaseModel):
    """One auto-remediation step attached to an AlertRule."""

    name: str = Field(..., min_length=1, max_length=128)
    type: RemediationActionType
    enabled: bool = True

    shell: str = Field(default="powershell", pattern="^(powershell|bash|sh|python|cmd)$")
    script_content: str | None = Field(
        default=None,
        max_length=100_000,
        description="Script or command body (required for run_script / run_command)",
    )
    command_type: str | None = Field(
        default=None,
        max_length=64,
        description="Optional catalog command type label",
    )

    min_severity: Literal["info", "warning", "critical", "emergency"] = "warning"
    cooldown_seconds: int = Field(default=900, ge=0, le=86400)
    dry_run: bool = False
    ignore_suppression: bool = False

    @field_validator("script_content")
    @classmethod
    def strip_content(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return v.strip() or None


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

    remediation_actions: list[RemediationAction] = Field(default_factory=list)

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

    remediation_actions: list[RemediationAction] | None = None

    enabled: bool | None = None
    priority: int | None = Field(None, ge=1)
    tags: dict[str, Any] | None = None


class AlertRuleResponse(AlertRuleBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RemediationRunResponse(BaseModel):
    id: UUID
    alert_id: str | None = None
    rule_id: str | None = None
    rule_name: str | None = None
    fingerprint: str | None = None
    device_id: str | None = None
    action_type: str
    action_name: str | None = None
    status: str
    skip_reason: str | None = None
    dry_run: bool = False
    task_id: str | None = None
    severity: str | None = None
    details: dict[str, Any] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
