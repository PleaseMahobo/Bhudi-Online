from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.device_management import MaintenanceWindow
from app.models.monitoring import MonitoringAlert, MonitoringCheck


class MonitoringService:
    def __init__(self, db: Session):
        self.db = db

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
    ) -> tuple[MonitoringCheck, list[MonitoringAlert]]:
        fingerprint = self._fingerprint(provider=provider, check_type=check_type, target=target, metric_name=metric_name)
        correlation = correlation_key or f"{provider}:{target or check_type}"
        previous_check = self._previous_check(fingerprint)
        baseline_value = self._baseline_value(fingerprint, metric_value, anomaly_baseline)
        anomaly_score = self._anomaly_score(metric_value, baseline_value, anomaly_tolerance)

        computed_status = status
        alert_specs: list[dict[str, Any]] = []

        if metric_value is not None:
            if critical_threshold is not None and metric_value >= critical_threshold:
                computed_status = "critical"
                alert_specs.append(
                    {
                        "alert_type": "threshold",
                        "severity": "critical",
                        "message": f"{provider} {check_type} exceeded critical threshold",
                        "context": {
                            "metric_name": metric_name,
                            "metric_value": metric_value,
                            "critical_threshold": critical_threshold,
                            "warning_threshold": warning_threshold,
                        },
                    }
                )
            elif warning_threshold is not None and metric_value >= warning_threshold:
                computed_status = "warning"
                alert_specs.append(
                    {
                        "alert_type": "threshold",
                        "severity": "warning",
                        "message": f"{provider} {check_type} exceeded warning threshold",
                        "context": {
                            "metric_name": metric_name,
                            "metric_value": metric_value,
                            "warning_threshold": warning_threshold,
                        },
                    }
                )

            if anomaly_score is not None and anomaly_tolerance is not None and anomaly_score >= anomaly_tolerance:
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
                            "anomaly_tolerance": anomaly_tolerance,
                        },
                    }
                )

        if state_value is not None and previous_check is not None and previous_check.state_value and previous_check.state_value != state_value:
            computed_status = "warning" if computed_status == "healthy" else computed_status
            alert_specs.append(
                {
                    "alert_type": "state_change",
                    "severity": "warning",
                    "message": f"{provider} {check_type} changed state from {previous_check.state_value} to {state_value}",
                    "state_transition": f"{previous_check.state_value}->{state_value}",
                    "context": {"previous_state": previous_check.state_value, "current_state": state_value},
                }
            )

        check_details = dict(details or {})
        check_details.update({
            "warning_threshold": warning_threshold,
            "critical_threshold": critical_threshold,
            "maintenance_window_name": maintenance_window_name,
            "escalation_policy": escalation_policy or {},
            "ai_suppression_enabled": ai_suppression_enabled,
        })

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
                    ai_suppression_enabled=ai_suppression_enabled,
                    maintenance_window_name=maintenance_window_name,
                    escalation_policy=escalation_policy,
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
        escalation = self._escalation_decision(correlation_key=correlation_key, policy=escalation_policy, severity=severity)
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
            maintenance_window=maintenance_window_name if suppression_reason == "maintenance_window_active" else None,
            escalation_level=escalation["level"],
            anomaly_score=anomaly_score,
            state_transition=state_transition,
            context={**(context or {}), "correlated_count": correlated_count, "escalation_policy": escalation_policy or {}},
        )
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert

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
        return alert

    def _fingerprint(self, *, provider: str, check_type: str, target: str | None, metric_name: str | None) -> str:
        return "::".join(part for part in [provider, check_type, target or "global", metric_name or "status"])

    def _previous_check(self, fingerprint: str) -> MonitoringCheck | None:
        return (
            self.db.query(MonitoringCheck)
            .filter(MonitoringCheck.fingerprint == fingerprint)
            .order_by(MonitoringCheck.created_at.desc())
            .first()
        )

    def _baseline_value(self, fingerprint: str, metric_value: float | None, configured_baseline: float | None) -> float | None:
        if configured_baseline is not None:
            return configured_baseline
        if metric_value is None:
            return None
        history = (
            self.db.query(MonitoringCheck.metric_value)
            .filter(MonitoringCheck.fingerprint == fingerprint, MonitoringCheck.metric_value.is_not(None))
            .order_by(MonitoringCheck.created_at.desc())
            .limit(5)
            .all()
        )
        values = [row[0] for row in history if row[0] is not None]
        if not values:
            return metric_value
        return float(mean(values))

    def _anomaly_score(self, metric_value: float | None, baseline_value: float | None, anomaly_tolerance: float | None) -> float | None:
        if metric_value is None or baseline_value is None or anomaly_tolerance is None:
            return None
        return abs(metric_value - baseline_value)

    def _suppression_reason(self, *, fingerprint: str | None, severity: str, ai_suppression_enabled: bool, maintenance_window_name: str | None) -> str | None:
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
            .filter(MonitoringAlert.correlation_key == correlation_key, MonitoringAlert.resolved.is_(False))
            .count()
        )
        return count + 1

    def _escalation_decision(self, *, correlation_key: str | None, policy: dict[str, Any] | None, severity: str) -> dict[str, Any]:
        policy_levels = (policy or {}).get("levels") or []
        occurrence_count = self._correlated_count(correlation_key)
        applied_level = 0
        applied_severity = severity
        for index, level in enumerate(sorted(policy_levels, key=lambda item: int(item.get("repeat_count", 1)))):
            if occurrence_count >= int(level.get("repeat_count", 1)):
                applied_level = index + 1
                applied_severity = str(level.get("severity") or applied_severity)
        return {"level": applied_level, "severity": applied_severity}
