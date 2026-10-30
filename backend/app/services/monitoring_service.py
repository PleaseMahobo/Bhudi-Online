from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.ws_manager import manager as ws_manager
from app.models.agent import Agent
from app.models.device_management import MaintenanceWindow
from app.models.monitoring import MonitoringAlert, MonitoringCheck
from app.services.alert_rule_service import AlertRuleService


class MonitoringService:
    def __init__(self, db: Session):
        self.db = db
        self.rule_service = AlertRuleService(db)

    def _resolve_tenant_id(
        self,
        *,
        tenant_id: UUID | None,
        payload: dict[str, Any],
    ) -> UUID:
        """Prefer explicit tenant_id; else derive from payload agent_id."""
        if tenant_id is not None:
            return tenant_id
        agent_id_raw = payload.get("agent_id")
        if agent_id_raw:
            try:
                agent = self.db.get(Agent, UUID(str(agent_id_raw)))
            except (ValueError, TypeError):
                agent = None
            if agent is not None and agent.tenant_id is not None:
                return agent.tenant_id
        raise ValueError(
            "tenant_id is required for monitoring rows "
            "(pass tenant_id= or include agent_id in payload that maps to an agent with tenant_id)"
        )

    def record_check(
        self,
        *,
        provider: str,
        check_type: str,
        target: str | None,
        payload: dict[str, Any],
        status: str,
        details: dict[str, Any] | None = None,
        fingerprint: str | None = None,
        correlation_key: str | None = None,
        metric_name: str | None = None,
        metric_value: float | None = None,
        state_value: str | None = None,
        baseline_value: float | None = None,
        anomaly_score: float | None = None,
        auto_alert: bool = True,
        tenant_id: UUID | None = None,
    ) -> MonitoringCheck:
        resolved_tenant_id = self._resolve_tenant_id(tenant_id=tenant_id, payload=payload)
        check = MonitoringCheck(
            tenant_id=resolved_tenant_id,
            provider=provider,
            check_type=check_type,
            target=target,
            fingerprint=fingerprint,
            correlation_key=correlation_key,
            payload=payload,
            status=status,
            metric_name=metric_name,
            metric_value=metric_value,
            state_value=state_value,
            baseline_value=baseline_value,
            anomaly_score=anomaly_score,
            details=details or {},
        )
        self.db.add(check)
        self.db.commit()
        self.db.refresh(check)
        if auto_alert and status != "healthy":
            self.raise_alert(
                check=check,
                alert_type="state_change" if state_value is not None else "state",
                message=f"{provider} {check_type} reported {status}",
                correlation_key=correlation_key,
                fingerprint=fingerprint,
            )
        return check
