from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.action import Action
from app.models.automation_log import AutomationLog
from app.models.device import Device
from app.models.monitoring import MonitoringAlert, MonitoringCheck
from app.models.remediation_run import RemediationRun
from app.models.script import Script
from app.models.script_task import ScriptTask
from app.services.alert_rule_service import AlertRuleService

logger = logging.getLogger(__name__)

# Default safety limits
DEFAULT_COOLDOWN_SECONDS = 900  # 15 minutes
MAX_ACTIONS_PER_ALERT = 5
ALLOWED_ACTION_TYPES = {"run_script", "run_command", "inventory_refresh", "notify_only"}


class RemediationService:
    """
    Production alert → remediation executor.

    Safety guarantees:
    - Never raises out of process_alert (callers must not break alert path)
    - Cooldown per (fingerprint, action_name) prevents storm loops
    - Severity gate: only run when alert severity is in action.min_severity set
    - Skips suppressed alerts unless action.ignore_suppression is true
    - dry_run records intent without queueing work
    """

    def __init__(self, db: Session):
        self.db = db
        self.rule_service = AlertRuleService(db)

    def process_alert(
        self,
        *,
        alert: MonitoringAlert,
        check: MonitoringCheck | None = None,
        rule_id: str | None = None,
        rule_name: str | None = None,
        remediation_actions: list[dict[str, Any]] | None = None,
    ) -> list[RemediationRun]:
        runs: list[RemediationRun] = []
        try:
            actions = remediation_actions or []
            if not actions and rule_id:
                rule = self.rule_service.get_alert_rule(UUID(str(rule_id)))
                if rule is not None:
                    actions = list(getattr(rule, "remediation_actions", None) or [])
                    rule_name = rule_name or rule.name

            if not actions:
                return runs

            if alert.suppressed and not any(
                bool(a.get("ignore_suppression")) for a in actions if isinstance(a, dict)
            ):
                runs.append(
                    self._record_skip(
                        alert=alert,
                        rule_id=rule_id,
                        rule_name=rule_name,
                        action_type="policy",
                        action_name="all",
                        reason="alert_suppressed",
                    )
                )
                self.db.commit()
                return runs

            device_id = self._resolve_device_id(check=check, alert=alert)

            for raw in actions[:MAX_ACTIONS_PER_ALERT]:
                if not isinstance(raw, dict):
                    continue
                run = self._execute_one(
                    alert=alert,
                    check=check,
                    rule_id=rule_id,
                    rule_name=rule_name,
                    action=raw,
                    device_id=device_id,
                )
                if run is not None:
                    runs.append(run)

            self.db.commit()
            for run in runs:
                self.db.refresh(run)
        except Exception:
            logger.exception("remediation process_alert failed; alert path preserved")
            try:
                self.db.rollback()
            except Exception:
                pass
        return runs

    def _execute_one(
        self,
        *,
        alert: MonitoringAlert,
        check: MonitoringCheck | None,
        rule_id: str | None,
        rule_name: str | None,
        action: dict[str, Any],
        device_id: str | None,
    ) -> RemediationRun | None:
        action_type = str(action.get("type") or "").strip()
        action_name = str(action.get("name") or action_type or "unnamed")[:255]
        enabled = action.get("enabled", True)
        if not enabled:
            return self._record_skip(
                alert=alert,
                rule_id=rule_id,
                rule_name=rule_name,
                action_type=action_type or "unknown",
                action_name=action_name,
                reason="action_disabled",
            )

        if action_type not in ALLOWED_ACTION_TYPES:
            return self._record_skip(
                alert=alert,
                rule_id=rule_id,
                rule_name=rule_name,
                action_type=action_type or "unknown",
                action_name=action_name,
                reason="unsupported_action_type",
            )

        if alert.suppressed and not action.get("ignore_suppression"):
            return self._record_skip(
                alert=alert,
                rule_id=rule_id,
                rule_name=rule_name,
                action_type=action_type,
                action_name=action_name,
                reason="alert_suppressed",
            )

        min_severity = action.get("min_severity") or "warning"
        if not self._severity_allows(alert.severity, min_severity):
            return self._record_skip(
                alert=alert,
                rule_id=rule_id,
                rule_name=rule_name,
                action_type=action_type,
                action_name=action_name,
                reason="severity_gate",
            )

        cooldown = int(action.get("cooldown_seconds") or DEFAULT_COOLDOWN_SECONDS)
        if cooldown > 0 and self._in_cooldown(
            fingerprint=alert.fingerprint,
            action_name=action_name,
            cooldown_seconds=cooldown,
        ):
            return self._record_skip(
                alert=alert,
                rule_id=rule_id,
                rule_name=rule_name,
                action_type=action_type,
                action_name=action_name,
                reason="cooldown_active",
            )

        dry_run = bool(action.get("dry_run", False))
        if dry_run or action_type == "notify_only":
            run = RemediationRun(
                alert_id=str(alert.id),
                rule_id=rule_id,
                rule_name=rule_name,
                fingerprint=alert.fingerprint,
                correlation_key=alert.correlation_key,
                device_id=device_id,
                action_type=action_type,
                action_name=action_name,
                command_type=action.get("command_type"),
                status="dry_run" if dry_run else "skipped",
                skip_reason=None if dry_run else "notify_only",
                dry_run=dry_run,
                severity=alert.severity,
                details={
                    "action": {k: v for k, v in action.items() if k != "script_content"},
                    "message": alert.message,
                },
            )
            self.db.add(run)
            return run

        if not device_id:
            return self._record_skip(
                alert=alert,
                rule_id=rule_id,
                rule_name=rule_name,
                action_type=action_type,
                action_name=action_name,
                reason="device_unresolved",
            )

        try:
            task_id, command_type = self._queue_work(
                action=action,
                device_id=device_id,
                alert=alert,
            )
            run = RemediationRun(
                alert_id=str(alert.id),
                rule_id=rule_id,
                rule_name=rule_name,
                fingerprint=alert.fingerprint,
                correlation_key=alert.correlation_key,
                device_id=device_id,
                action_type=action_type,
                action_name=action_name,
                command_type=command_type,
                status="queued",
                dry_run=False,
                task_id=task_id,
                severity=alert.severity,
                details={
                    "action_name": action_name,
                    "shell": action.get("shell"),
                    "check_id": str(check.id) if check else None,
                },
            )
            self.db.add(run)
            return run
        except Exception as exc:
            logger.exception("failed to queue remediation action %s", action_name)
            run = RemediationRun(
                alert_id=str(alert.id),
                rule_id=rule_id,
                rule_name=rule_name,
                fingerprint=alert.fingerprint,
                correlation_key=alert.correlation_key,
                device_id=device_id,
                action_type=action_type,
                action_name=action_name,
                status="failed",
                skip_reason="queue_error",
                severity=alert.severity,
                details={"error": str(exc)[:500]},
            )
            self.db.add(run)
            return run

    def _queue_work(
        self,
        *,
        action: dict[str, Any],
        device_id: str,
        alert: MonitoringAlert,
    ) -> tuple[str | None, str | None]:
        action_type = action.get("type")
        shell = str(action.get("shell") or "powershell")
        content = str(action.get("script_content") or "").strip()
        command_type = str(action.get("command_type") or action_type)

        if action_type == "inventory_refresh":
            content = content or (
                "Get-ComputerInfo | Select-Object CsName, WindowsVersion, OsArchitecture | ConvertTo-Json"
                if shell == "powershell"
                else "uname -a; cat /etc/os-release 2>/dev/null || true"
            )
            command_type = "inventory_refresh"

        if action_type in {"run_script", "run_command", "inventory_refresh"} and not content:
            raise ValueError("script_content required for remediation action")

        script = Script(
            name=f"remediation:{action.get('name') or command_type}",
            description=f"Auto-remediation for alert {alert.id}",
            shell=shell,
            content=content,
        )
        self.db.add(script)
        self.db.flush()

        # tenant_id: prefer device.tenant_id when available
        tenant_id = device_id
        device = self.db.get(Device, device_id)
        if device is not None and getattr(device, "tenant_id", None):
            tenant_id = str(device.tenant_id)

        task = ScriptTask(
            script_id=script.id,
            device_id=device_id,
            tenant_id=str(tenant_id),
            status="queued",
            parameters={
                "source": "alert_remediation",
                "alert_id": str(alert.id),
                "fingerprint": alert.fingerprint,
                "action": action.get("name"),
            },
        )
        self.db.add(task)
        self.db.flush()

        action_row = Action(
            device_id=device_id,
            tenant_id=str(tenant_id),
            type="alert.remediation",
            payload={
                "script_id": str(script.id),
                "task_id": str(task.id),
                "alert_id": str(alert.id),
            },
            status="queued",
            result="queued",
        )
        self.db.add(action_row)

        log = AutomationLog(
            action="alert.remediation",
            result="queued",
        )
        self.db.add(log)
        self.db.flush()

        return str(task.id), command_type

    def _resolve_device_id(
        self,
        *,
        check: MonitoringCheck | None,
        alert: MonitoringAlert,
    ) -> str | None:
        # Prefer explicit context
        ctx = alert.context or {}
        for key in ("device_id", "agent_id"):
            val = ctx.get(key)
            if val:
                return str(val)

        target = None
        if check is not None and check.target:
            target = check.target
        elif ctx.get("target"):
            target = str(ctx["target"])

        if not target:
            return None

        # Match device by id, device_id, or hostname
        device = self.db.get(Device, target)
        if device is not None:
            return str(device.id)

        q = (
            self.db.query(Device)
            .filter(
                (Device.hostname == target)
                | (getattr(Device, "device_id", Device.id) == target)
            )
            .first()
        )
        if q is not None:
            return str(q.id)

        # hostname case-insensitive fallback
        try:
            q = (
                self.db.query(Device)
                .filter(Device.hostname.ilike(target))
                .first()
            )
            if q is not None:
                return str(q.id)
        except Exception:
            pass

        return None

    def _in_cooldown(
        self,
        *,
        fingerprint: str | None,
        action_name: str,
        cooldown_seconds: int,
    ) -> bool:
        if not fingerprint:
            return False
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=cooldown_seconds)
        existing = (
            self.db.query(RemediationRun)
            .filter(
                RemediationRun.fingerprint == fingerprint,
                RemediationRun.action_name == action_name,
                RemediationRun.status.in_(["queued", "completed", "dry_run"]),
                RemediationRun.created_at >= cutoff,
            )
            .first()
        )
        return existing is not None

    @staticmethod
    def _severity_allows(alert_severity: str | None, min_severity: str) -> bool:
        order = {"info": 0, "warning": 1, "critical": 2, "emergency": 3}
        a = order.get((alert_severity or "warning").lower(), 1)
        m = order.get((min_severity or "warning").lower(), 1)
        return a >= m

    def _record_skip(
        self,
        *,
        alert: MonitoringAlert,
        rule_id: str | None,
        rule_name: str | None,
        action_type: str,
        action_name: str,
        reason: str,
    ) -> RemediationRun:
        run = RemediationRun(
            alert_id=str(alert.id),
            rule_id=rule_id,
            rule_name=rule_name,
            fingerprint=alert.fingerprint,
            correlation_key=alert.correlation_key,
            action_type=action_type,
            action_name=action_name,
            status="skipped",
            skip_reason=reason,
            severity=alert.severity,
            details={"reason": reason},
        )
        self.db.add(run)
        return run

    def list_runs(self, limit: int = 50) -> list[RemediationRun]:
        return (
            self.db.query(RemediationRun)
            .order_by(RemediationRun.created_at.desc())
            .limit(limit)
            .all()
        )
