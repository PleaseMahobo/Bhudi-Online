from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.ws_manager import manager as ws_manager
from app.models.device_management import MaintenanceWindow
from app.models.monitoring import MonitoringAlert, MonitoringCheck
from app.services.alert_rule_service import AlertRuleService


class MonitoringService:
    def __init__(self, db: Session):
        self.db = db
        self.rule_service = AlertRuleService(db)

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
    ) -> MonitoringCheck:
        check = MonitoringCheck(
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

    def evaluate_check(
        self,
        *,
        provider: str,
        check_type: str,
        target: str | None,
        payload: dict[str, Any],
        status: str = "healthy",
        details: dict[str, Any] | None = None,
        metric_name: str | None = None,
        metric_value: float | None = None,
        state_value: str | None = None,
        warning_threshold: float | None = None,
        critical_threshold: float | None = None,
        anomaly_baseline: float | None = None,
        anomaly_tolerance: float | None = None,
        ai_suppression_enabled: bool = False,
        maintenance_window_name: str | None = None,
        escalation_policy: dict[str, Any] | None = None,
        correlation_key: str | None = None,
        use_rules: bool = True,
    ) -> tuple[MonitoringCheck, list[MonitoringAlert]]:
        matched_rules = []
        if use_rules:
            matched_rules = self.rule_service.find_matching_rules(
                provider=provider,
                check_type=check_type,
                target=target,
                metric_name=metric_name,
            )

        active_rule = matched_rules[0] if matched_rules else None

        effective_warning = warning_threshold
        effective_critical = critical_threshold
        effective_anomaly_tolerance = anomaly_tolerance
        effective_ai_suppression = ai_suppression_enabled
        effective_maintenance = maintenance_window_name
        effective_escalation = escalation_policy
        state_change_enabled = True
        anomaly_enabled = anomaly_tolerance is not None

        if active_rule is not None:
            if effective_warning is None:
                effective_warning = active_rule.warning_threshold
            if effective_critical is None:
                effective_critical = active_rule.critical_threshold
            if effective_anomaly_tolerance is None and active_rule.anomaly_enabled:
                effective_anomaly_tolerance = active_rule.anomaly_tolerance
            anomaly_enabled = active_rule.anomaly_enabled or anomaly_enabled
            state_change_enabled = active_rule.state_change_enabled
            effective_ai_suppression = (
                active_rule.ai_suppression_enabled if not ai_suppression_enabled else True
            )
            if effective_maintenance is None:
                effective_maintenance = active_rule.maintenance_window_name

            if effective_escalation is None and active_rule.escalation_policy_id:
                policy = self.rule_service.get_escalation_policy(active_rule.escalation_policy_id)
                if policy and policy.enabled:
                    effective_escalation = {"levels": policy.levels}

        fingerprint = self._fingerprint(
            provider=provider,
            check_type=check_type,
            target=target,
            metric_name=metric_name,
        )
        correlation = correlation_key or f"{provider}:{target or check_type}"
        previous_check = self._previous_check(fingerprint)
        baseline_value = self._baseline_value(fingerprint, metric_value, anomaly_baseline)
        anomaly_score = self._anomaly_score(metric_value, baseline_value, effective_anomaly_tolerance)

        computed_status = status
        alert_specs: list[dict[str, Any]] = []

        if metric_value is not None:
            if effective_critical is not None and metric_value >= effective_critical:
                computed_status = "critical"
                alert_specs.append(
                    {
                        "alert_type": "threshold",
                        "severity": "critical",
                        "message": f"{provider} {check_type} exceeded critical threshold",
                        "context": {
                            "metric_name": metric_name,
                            "metric_value": metric_value,
                            "critical_threshold": effective_critical,
                            "warning_threshold": effective_warning,
                            "rule_id": str(active_rule.id) if active_rule else None,
                            "rule_name": active_rule.name if active_rule else None,
                        },
                    }
                )
            elif effective_warning is not None and metric_value >= effective_warning:
                computed_status = "warning"
                alert_specs.append(
                    {
                        "alert_type": "threshold",
                        "severity": "warning",
                        "message": f"{provider} {check_type} exceeded warning threshold",
                        "context": {
                            "metric_name": metric_name,
                            "metric_value": metric_value,
                            "warning_threshold": effective_warning,
                            "rule_id": str(active_rule.id) if active_rule else None,
                            "rule_name": active_rule.name if active_rule else None,
                        },
                    }
                )

            if (
                anomaly_enabled
                and anomaly_score is not None
                and effective_anomaly_tolerance is not None
                and anomaly_score >= effective_anomaly_tolerance
            ):
                computed_status = "warning" if computed_status == "healthy" else computed_status
                alert_specs.append(
                    {
                        "alert_type": "anomaly",
                        "severity": "warning",
                        "message": f"{provider} {check_type} deviated from baseline",
                        "anomaly_score": anomaly_score,
                        "context": {
                            "metric_name": metric_name,
                            "metric_value": metric_value,
                            "baseline_value": baseline_value,
                            "anomaly_tolerance": effective_anomaly_tolerance,
                            "rule_id": str(active_rule.id) if active_rule else None,
                            "rule_name": active_rule.name if active_rule else None,
                        },
                    }
                )

        if (
            state_change_enabled
            and state_value is not None
            and previous_check is not None
            and previous_check.state_value
            and previous_check.state_value != state_value
        ):
            computed_status = "warning" if computed_status == "healthy" else computed_status
            alert_specs.append(
                {
                    "alert_type": "state_change",
                    "severity": "warning",
                    "message": (
                        f"{provider} {check_type} changed state from "
                        f"{previous_check.state_value} to {state_value}"
                    ),
                    "state_transition": f"{previous_check.state_value}->{state_value}",
                    "context": {
                        "previous_state": previous_check.state_value,
                        "current_state": state_value,
                        "rule_id": str(active_rule.id) if active_rule else None,
                        "rule_name": active_rule.name if active_rule else None,
                    },
                }
            )

        check_details = dict(details or {})
        check_details.update(
            {
                "warning_threshold": effective_warning,
                "critical_threshold": effective_critical,
                "maintenance_window_name": effective_maintenance,
                "escalation_policy": effective_escalation or {},
                "ai_suppression_enabled": effective_ai_suppression,
                "matched_rule_id": str(active_rule.id) if active_rule else None,
                "matched_rule_name": active_rule.name if active_rule else None,
            }
        )

        check = self.record_check(
            provider=provider,
            check_type=check_type,
            target=target,
            payload=payload,
            status=computed_status,
            details=check_details,
            fingerprint=fingerprint,
            correlation_key=correlation,
            metric_name=metric_name,
            metric_value=metric_value,
            state_value=state_value,
            baseline_value=baseline_value,
            anomaly_score=anomaly_score,
            auto_alert=False,
        )

        alerts: list[MonitoringAlert] = []
        for spec in alert_specs:
            alerts.append(
                self.raise_alert(
                    check=check,
                    alert_type=spec["alert_type"],
                    message=spec["message"],
                    severity=spec["severity"],
                    context=spec.get("context"),
                    anomaly_score=spec.get("anomaly_score"),
                    state_transition=spec.get("state_transition"),
                    correlation_key=correlation,
                    fingerprint=fingerprint,
                    ai_suppression_enabled=effective_ai_suppression,
                    maintenance_window_name=effective_maintenance,
                    escalation_policy=effective_escalation,
                )
            )
        return check, alerts

    def raise_alert(
        self,
        *,
        check: MonitoringCheck,
        alert_type: str,
        message: str,
        severity: str = "warning",
        context: dict[str, Any] | None = None,
        anomaly_score: float | None = None,
        state_transition: str | None = None,
        correlation_key: str | None = None,
        fingerprint: str | None = None,
        ai_suppression_enabled: bool = False,
        maintenance_window_name: str | None = None,
        escalation_policy: dict[str, Any] | None = None,
    ) -> MonitoringAlert:
        suppression_reason = self._suppression_reason(
            fingerprint=fingerprint,
            severity=severity,
            ai_suppression_enabled=ai_suppression_enabled,
            maintenance_window_name=maintenance_window_name,
        )
        correlated_count = self._correlated_count(correlation_key)
        escalation = self._escalation_decision(
            correlation_key=correlation_key,
            policy=escalation_policy,
            severity=severity,
        )
        alert = MonitoringAlert(
            check_id=check.id,
            provider=check.provider,
            alert_type=alert_type,
            severity=escalation["severity"],
            message=message,
            fingerprint=fingerprint,
            correlation_key=correlation_key,
            correlated_count=correlated_count,
            suppressed=suppression_reason is not None,
            suppression_reason=suppression_reason,
            maintenance_window=(
                maintenance_window_name
                if suppression_reason == "maintenance_window_active"
                else None
            ),
            escalation_level=escalation["level"],
            anomaly_score=anomaly_score,
            state_transition=state_transition,
            context={
                **(context or {}),
                "correlated_count": correlated_count,
                "escalation_policy": escalation_policy or {},
            },
        )
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)

        self._broadcast_alert_event("alert.created", alert)
        self._trigger_remediation(alert=alert, check=check)
        return alert

    def _trigger_remediation(self, *, alert: MonitoringAlert, check: MonitoringCheck) -> None:
        """Fire alert-driven remediation; failures never affect alert persistence."""
        try:
            from uuid import UUID as _UUID

            from app.services.remediation_service import RemediationService

            ctx = alert.context or {}
            rule_id = ctx.get("rule_id")
            rule_name = ctx.get("rule_name")
            actions = None
            if rule_id:
                try:
                    rule = self.rule_service.get_alert_rule(_UUID(str(rule_id)))
                    if rule is not None:
                        actions = list(getattr(rule, "remediation_actions", None) or [])
                        rule_name = rule_name or rule.name
                except Exception:
                    actions = None
            RemediationService(self.db).process_alert(
                alert=alert,
                check=check,
                rule_id=str(rule_id) if rule_id else None,
                rule_name=str(rule_name) if rule_name else None,
                remediation_actions=actions,
            )
        except Exception:
            pass

    def list_checks(self) -> list[MonitoringCheck]:
        return self.db.query(MonitoringCheck).order_by(MonitoringCheck.created_at.desc()).all()

    def list_alerts(self) -> list[MonitoringAlert]:
        return self.db.query(MonitoringAlert).order_by(MonitoringAlert.created_at.desc()).all()

    def resolve_alert(self, alert_id: UUID) -> MonitoringAlert | None:
        alert = self.db.get(MonitoringAlert, alert_id)
        if alert is None:
            return None
        alert.resolved = True
        self.db.commit()
        self.db.refresh(alert)
        self._broadcast_alert_event("alert.resolved", alert)
        return alert

    def _broadcast_alert_event(self, event: str, alert: MonitoringAlert) -> None:
        payload = {
            "type": event,
            "channel": "alerts",
            "alert": {
                "id": str(alert.id),
                "check_id": str(alert.check_id) if alert.check_id else None,
                "provider": alert.provider,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message,
                "fingerprint": alert.fingerprint,
                "correlation_key": alert.correlation_key,
                "correlated_count": alert.correlated_count,
                "suppressed": alert.suppressed,
                "suppression_reason": alert.suppression_reason,
                "maintenance_window": alert.maintenance_window,
                "escalation_level": alert.escalation_level,
                "anomaly_score": alert.anomaly_score,
                "state_transition": alert.state_transition,
                "context": alert.context,
                "resolved": alert.resolved,
                "created_at": alert.created_at.isoformat() if alert.created_at else None,
            },
        }
        try:
            ws_manager.broadcast_sync(payload, channel="alerts")
        except Exception:
            pass

    def _fingerprint(
        self, *, provider: str, check_type: str, target: str | None, metric_name: str | None
    ) -> str:
        return "::".join(
            part for part in [provider, check_type, target or "global", metric_name or "status"]
        )

    def _previous_check(self, fingerprint: str) -> MonitoringCheck | None:
        return (
            self.db.query(MonitoringCheck)
            .filter(MonitoringCheck.fingerprint == fingerprint)
            .order_by(MonitoringCheck.created_at.desc())
            .first()
        )

    def _baseline_value(
        self,
        fingerprint: str,
        metric_value: float | None,
        configured_baseline: float | None,
    ) -> float | None:
        if configured_baseline is not None:
            return configured_baseline
        if metric_value is None:
            return None
        history = (
            self.db.query(MonitoringCheck.metric_value)
            .filter(
                MonitoringCheck.fingerprint == fingerprint,
                MonitoringCheck.metric_value.is_not(None),
            )
            .order_by(MonitoringCheck.created_at.desc())
            .limit(5)
            .all()
        )
        values = [row[0] for row in history if row[0] is not None]
        if not values:
            return metric_value
        return float(mean(values))

    def _anomaly_score(
        self,
        metric_value: float | None,
        baseline_value: float | None,
        anomaly_tolerance: float | None,
    ) -> float | None:
        if metric_value is None or baseline_value is None or anomaly_tolerance is None:
            return None
        return abs(metric_value - baseline_value)

    def _suppression_reason(
        self,
        *,
        fingerprint: str | None,
        severity: str,
        ai_suppression_enabled: bool,
        maintenance_window_name: str | None,
    ) -> str | None:
        if self._maintenance_window_active(maintenance_window_name):
            return "maintenance_window_active"
        if ai_suppression_enabled and fingerprint:
            duplicate = (
                self.db.query(MonitoringAlert)
                .filter(
                    MonitoringAlert.fingerprint == fingerprint,
                    MonitoringAlert.severity == severity,
                    MonitoringAlert.resolved.is_(False),
                )
                .order_by(MonitoringAlert.created_at.desc())
                .first()
            )
            if duplicate is not None:
                return "ai_similarity_suppression"
        return None

    def _maintenance_window_active(self, maintenance_window_name: str | None) -> bool:
        if not maintenance_window_name:
            return False
        query = self.db.query(MaintenanceWindow)
        query = query.filter(MaintenanceWindow.name == maintenance_window_name)
        windows = query.all()
        now = datetime.now(timezone.utc)
        for window in windows:
            try:
                start = datetime.fromisoformat(window.start.replace("Z", "+00:00"))
                end = datetime.fromisoformat(window.end.replace("Z", "+00:00"))
            except ValueError:
                continue
            if start <= now <= end:
                return True
        return False

    def _correlated_count(self, correlation_key: str | None) -> int:
        if not correlation_key:
            return 1
        count = (
            self.db.query(MonitoringAlert)
            .filter(
                MonitoringAlert.correlation_key == correlation_key,
                MonitoringAlert.resolved.is_(False),
            )
            .count()
        )
        return count + 1

    def _escalation_decision(
        self,
        *,
        correlation_key: str | None,
        policy: dict[str, Any] | None,
        severity: str,
    ) -> dict[str, Any]:
        policy_levels = (policy or {}).get("levels") or []
        occurrence_count = self._correlated_count(correlation_key)
        applied_level = 0
        applied_severity = severity
        for index, level in enumerate(
            sorted(policy_levels, key=lambda item: int(item.get("repeat_count", 1)))
        ):
            if occurrence_count >= int(level.get("repeat_count", 1)):
                applied_level = index + 1
                applied_severity = str(level.get("severity") or applied_severity)
        return {"level": applied_level, "severity": applied_severity}
