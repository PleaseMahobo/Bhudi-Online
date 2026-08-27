from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.monitoring import MonitoringAlert
from app.schemas.alert_engine import (
    AlertRuleCreate,
    AlertRuleUpdate,
    AlertRuleResponse,
    EscalationPolicyCreate,
    EscalationPolicyUpdate,
    EscalationPolicyResponse,
    EscalationLevel,
    RemediationRunResponse,
)
from app.services.alert_rule_service import AlertRuleService
from app.services.monitoring_service import MonitoringService
from app.services.remediation_service import RemediationService

router = APIRouter(prefix="/alert-engine", tags=["Alert Engine"])


@router.post("/escalation-policies", response_model=EscalationPolicyResponse, status_code=status.HTTP_201_CREATED)
def create_escalation_policy(payload: EscalationPolicyCreate, db: Session = Depends(get_db)):
    return AlertRuleService(db).create_escalation_policy(payload)


@router.get("/escalation-policies", response_model=list[EscalationPolicyResponse])
def list_escalation_policies(enabled_only: bool = False, db: Session = Depends(get_db)):
    return AlertRuleService(db).list_escalation_policies(enabled_only=enabled_only)


@router.get("/escalation-policies/{policy_id}", response_model=EscalationPolicyResponse)
def get_escalation_policy(policy_id: UUID, db: Session = Depends(get_db)):
    policy = AlertRuleService(db).get_escalation_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Escalation policy not found")
    return policy


@router.patch("/escalation-policies/{policy_id}", response_model=EscalationPolicyResponse)
def update_escalation_policy(policy_id: UUID, payload: EscalationPolicyUpdate, db: Session = Depends(get_db)):
    policy = AlertRuleService(db).update_escalation_policy(policy_id, payload)
    if not policy:
        raise HTTPException(status_code=404, detail="Escalation policy not found")
    return policy


@router.delete("/escalation-policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_escalation_policy(policy_id: UUID, db: Session = Depends(get_db)):
    if not AlertRuleService(db).delete_escalation_policy(policy_id):
        raise HTTPException(status_code=404, detail="Escalation policy not found")


@router.post("/rules", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
def create_alert_rule(payload: AlertRuleCreate, db: Session = Depends(get_db)):
    return AlertRuleService(db).create_alert_rule(payload)


@router.get("/rules", response_model=list[AlertRuleResponse])
def list_alert_rules(enabled_only: bool = False, db: Session = Depends(get_db)):
    return AlertRuleService(db).list_alert_rules(enabled_only=enabled_only)


@router.get("/rules/{rule_id}", response_model=AlertRuleResponse)
def get_alert_rule(rule_id: UUID, db: Session = Depends(get_db)):
    rule = AlertRuleService(db).get_alert_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return rule


@router.patch("/rules/{rule_id}", response_model=AlertRuleResponse)
def update_alert_rule(rule_id: UUID, payload: AlertRuleUpdate, db: Session = Depends(get_db)):
    rule = AlertRuleService(db).update_alert_rule(rule_id, payload)
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return rule


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert_rule(rule_id: UUID, db: Session = Depends(get_db)):
    if not AlertRuleService(db).delete_alert_rule(rule_id):
        raise HTTPException(status_code=404, detail="Alert rule not found")


@router.get("/remediation-runs", response_model=list[RemediationRunResponse])
def list_remediation_runs(limit: int = 50, db: Session = Depends(get_db)):
    return RemediationService(db).list_runs(limit=min(max(limit, 1), 200))


class MetricEvaluateRequest(BaseModel):
    provider: str = "bhudi-agent"
    check_type: str = "metric"
    target: str | None = None
    metric_name: str
    metric_value: float
    warning_threshold: float | None = None
    critical_threshold: float | None = None
    correlation_key: str | None = None
    context: dict[str, Any] | None = None


class ActiveAlertResponse(BaseModel):
    id: str
    provider: str
    alert_type: str
    severity: str
    message: str
    suppressed: bool = False
    suppression_reason: str | None = None
    escalation_level: int = 0
    correlated_count: int = 1
    resolved: bool = False
    acknowledged: bool = False
    fingerprint: str | None = None
    correlation_key: str | None = None
    context: dict[str, Any] | None = None
    created_at: str | None = None


def _alert_to_response(alert: MonitoringAlert) -> ActiveAlertResponse:
    ctx = alert.context or {}
    created = getattr(alert, "created_at", None)
    return ActiveAlertResponse(
        id=str(alert.id),
        provider=alert.provider,
        alert_type=alert.alert_type,
        severity=alert.severity,
        message=alert.message,
        suppressed=bool(getattr(alert, "suppressed", False)),
        suppression_reason=getattr(alert, "suppression_reason", None),
        escalation_level=int(getattr(alert, "escalation_level", 0) or 0),
        correlated_count=int(getattr(alert, "correlated_count", 1) or 1),
        resolved=bool(getattr(alert, "resolved", False)),
        acknowledged=bool(ctx.get("acknowledged")),
        fingerprint=getattr(alert, "fingerprint", None),
        correlation_key=getattr(alert, "correlation_key", None),
        context=ctx,
        created_at=created.isoformat() if created is not None else None,
    )


@router.get("/alerts", response_model=list[ActiveAlertResponse])
def list_active_alerts(
    resolved: bool | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    rows = MonitoringService(db).list_alerts()
    out: list[ActiveAlertResponse] = []
    for alert in rows:
        if resolved is not None and bool(alert.resolved) != resolved:
            continue
        out.append(_alert_to_response(alert))
        if len(out) >= max(1, min(limit, 500)):
            break
    return out


@router.post("/alerts/{alert_id}/resolve", response_model=ActiveAlertResponse)
def resolve_active_alert(alert_id: UUID, db: Session = Depends(get_db)):
    alert = MonitoringService(db).resolve_alert(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return _alert_to_response(alert)


@router.post("/alerts/{alert_id}/acknowledge", response_model=ActiveAlertResponse)
def acknowledge_alert(alert_id: UUID, db: Session = Depends(get_db)):
    svc = MonitoringService(db)
    alert = db.get(MonitoringAlert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    ctx = dict(alert.context or {})
    ctx["acknowledged"] = True
    ctx["acknowledged_at"] = datetime.now(timezone.utc).isoformat()
    alert.context = ctx
    db.commit()
    db.refresh(alert)
    try:
        svc._broadcast_alert_event("alert.acknowledged", alert)
    except Exception:
        pass
    return _alert_to_response(alert)


@router.post("/evaluate")
def evaluate_metric(payload: MetricEvaluateRequest, db: Session = Depends(get_db)):
    check, alerts = MonitoringService(db).evaluate_check(
        provider=payload.provider,
        check_type=payload.check_type,
        target=payload.target,
        payload=payload.context or {},
        metric_name=payload.metric_name,
        metric_value=payload.metric_value,
        warning_threshold=payload.warning_threshold,
        critical_threshold=payload.critical_threshold,
        correlation_key=payload.correlation_key or payload.target,
        use_rules=True,
    )
    return {
        "check_id": str(check.id),
        "status": check.status,
        "alert_count": len(alerts),
        "alerts": [_alert_to_response(a) for a in alerts],
    }


class SeedDefaultsResponse(BaseModel):
    created: int
    skipped: int = 0
    message: str
    rules: list[AlertRuleResponse] = []
    policies: list[EscalationPolicyResponse] = []
    defaults: list[str] = []


@router.post("/seed-defaults", response_model=SeedDefaultsResponse)
def seed_default_rules(force: bool = False, db: Session = Depends(get_db)):
    """Seed baseline agent rules; response includes full rules + policies for UI refresh."""
    service = AlertRuleService(db)
    existing = list(service.list_alert_rules())
    existing_names = {r.name for r in existing}

    default_specs = [
        AlertRuleCreate(
            name="Agent high CPU",
            description="CPU utilization from native agents",
            provider="bhudi-agent",
            check_type="metric",
            metric_name="cpu_percent",
            warning_threshold=85.0,
            critical_threshold=95.0,
            enabled=True,
            priority=10,
        ),
        AlertRuleCreate(
            name="Agent high memory",
            description="Memory utilization from native agents",
            provider="bhudi-agent",
            check_type="metric",
            metric_name="memory_percent",
            warning_threshold=85.0,
            critical_threshold=95.0,
            enabled=True,
            priority=20,
        ),
        AlertRuleCreate(
            name="Agent high disk",
            description="Disk utilization from native agents",
            provider="bhudi-agent",
            check_type="metric",
            metric_name="disk_percent",
            warning_threshold=85.0,
            critical_threshold=95.0,
            enabled=True,
            priority=30,
        ),
        AlertRuleCreate(
            name="Agent offline",
            description="Agent reported offline status",
            provider="bhudi-agent",
            check_type="state",
            enabled=True,
            priority=5,
        ),
    ]
    default_names = [d.name for d in default_specs]

    def _ensure_default_policy():
        policies = list(service.list_escalation_policies())
        if policies:
            return policies
        try:
            service.create_escalation_policy(
                EscalationPolicyCreate(
                    name="Default agent escalation",
                    description="Warn once, then critical with email",
                    levels=[
                        EscalationLevel(repeat_count=1, severity="warning", notify=["email"]),
                        EscalationLevel(repeat_count=3, severity="critical", notify=["email"]),
                    ],
                    enabled=True,
                )
            )
        except Exception as exc:
            print(f"[alert-engine] policy seed skip: {exc}")
        return list(service.list_escalation_policies())

    if existing and not force:
        policies = _ensure_default_policy()
        return SeedDefaultsResponse(
            created=0,
            skipped=len(existing),
            message=f"Already have {len(existing)} rules — pass force=true to add any missing defaults",
            rules=existing,
            policies=policies,
            defaults=default_names,
        )

    created = 0
    skipped = 0
    created_names: list[str] = []
    for item in default_specs:
        if item.name in existing_names:
            skipped += 1
            continue
        try:
            service.create_alert_rule(item)
            created += 1
            created_names.append(item.name)
            existing_names.add(item.name)
        except Exception as exc:
            print(f"[alert-engine] seed skip {item.name}: {exc}")
            skipped += 1

    policies = _ensure_default_policy()
    rules = list(service.list_alert_rules())
    msg = f"Seeded {created} default rules"
    if created_names:
        msg += f" ({', '.join(created_names)})"
    if skipped:
        msg += f"; skipped {skipped}"
    return SeedDefaultsResponse(
        created=created,
        skipped=skipped,
        message=msg,
        rules=rules,
        policies=policies,
        defaults=default_names,
    )
