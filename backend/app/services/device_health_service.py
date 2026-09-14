"""Device health scoring, missed-heartbeat tracking, and resource threshold alerts.

Score starts at 100 and subtracts weighted penalties for connectivity and
resource pressure. Also drives agent/device status from last_seen age.
SMART attribute details (reallocated/pending/uncorrectable sectors) further
adjust the score when agents report rich smartctl data.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Connectivity windows (seconds)
ONLINE_SECS = int(os.getenv("BHUDI_ONLINE_SECS", "45"))
OVERDUE_SECS = int(os.getenv("BHUDI_OVERDUE_SECS", "120"))
OFFLINE_SECS = int(os.getenv("BHUDI_OFFLINE_SECS", "300"))

# Resource thresholds (percent)
CPU_WARN = float(os.getenv("BHUDI_CPU_WARN", "85"))
CPU_CRIT = float(os.getenv("BHUDI_CPU_CRIT", "95"))
MEM_WARN = float(os.getenv("BHUDI_MEM_WARN", "85"))
MEM_CRIT = float(os.getenv("BHUDI_MEM_CRIT", "95"))
DISK_WARN = float(os.getenv("BHUDI_DISK_WARN", "90"))
DISK_CRIT = float(os.getenv("BHUDI_DISK_CRIT", "95"))
TEMP_WARN = float(os.getenv("BHUDI_TEMP_WARN", "80"))
TEMP_CRIT = float(os.getenv("BHUDI_TEMP_CRIT", "90"))

# SMART attribute thresholds (raw counts)
SMART_REALLOC_WARN = int(os.getenv("BHUDI_SMART_REALLOC_WARN", "1"))
SMART_REALLOC_CRIT = int(os.getenv("BHUDI_SMART_REALLOC_CRIT", "50"))
SMART_PENDING_WARN = int(os.getenv("BHUDI_SMART_PENDING_WARN", "1"))
SMART_UNCORRECT_WARN = int(os.getenv("BHUDI_SMART_UNCORRECT_WARN", "1"))


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def status_from_age(age_secs: float | None) -> str:
    if age_secs is None:
        return "unknown"
    if age_secs <= ONLINE_SECS:
        return "online"
    if age_secs <= OVERDUE_SECS:
        return "overdue"
    if age_secs <= OFFLINE_SECS:
        return "offline"
    return "offline"


def _aggregate_smart_critical(smart_details: dict[str, Any] | None) -> dict[str, int]:
    """Sum critical attribute raw values across all disks in smart_details."""
    totals: dict[str, int] = {}
    if not smart_details or not isinstance(smart_details, dict):
        return totals
    disks = smart_details.get("disks") or []
    if not isinstance(disks, list):
        return totals
    keys = (
        "reallocated_sectors",
        "current_pending_sectors",
        "offline_uncorrectable",
        "reported_uncorrectable",
        "media_errors",
        "runtime_bad_block",
        "end_to_end_error",
    )
    for disk in disks:
        if not isinstance(disk, dict):
            continue
        crit = disk.get("critical") or {}
        if not isinstance(crit, dict):
            continue
        for k in keys:
            v = crit.get(k)
            if v is None:
                continue
            try:
                totals[k] = totals.get(k, 0) + int(v)
            except (TypeError, ValueError):
                pass
    return totals


def compute_health_score(
    *,
    status: str,
    consecutive_misses: int = 0,
    cpu_percent: float | None = None,
    memory_percent: float | None = None,
    disk_percent: float | None = None,
    temperature_c: float | None = None,
    smart_status: str | None = None,
    smart_details: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    """Return (score 0-100, factors breakdown)."""
    score = 100
    factors: dict[str, Any] = {
        "status": status,
        "consecutive_misses": consecutive_misses,
        "cpu_percent": cpu_percent,
        "memory_percent": memory_percent,
        "disk_percent": disk_percent,
        "temperature_c": temperature_c,
        "smart_status": smart_status,
        "penalties": {},
    }
    penalties = factors["penalties"]

    st = (status or "unknown").lower()
    if st == "offline":
        penalties["offline"] = -40
        score -= 40
    elif st == "overdue":
        penalties["overdue"] = -20
        score -= 20
    elif st == "unknown":
        penalties["unknown"] = -15
        score -= 15

    misses = max(0, int(consecutive_misses or 0))
    if misses > 1:
        pen = min(30, (misses - 1) * 5)
        penalties["missed_heartbeats"] = -pen
        score -= pen

    if cpu_percent is not None:
        if cpu_percent >= CPU_CRIT:
            penalties["cpu_critical"] = -20
            score -= 20
        elif cpu_percent >= CPU_WARN:
            penalties["cpu_warning"] = -10
            score -= 10

    if memory_percent is not None:
        if memory_percent >= MEM_CRIT:
            penalties["memory_critical"] = -15
            score -= 15
        elif memory_percent >= MEM_WARN:
            penalties["memory_warning"] = -8
            score -= 8

    if disk_percent is not None:
        if disk_percent >= DISK_CRIT:
            penalties["disk_critical"] = -25
            score -= 25
        elif disk_percent >= DISK_WARN:
            penalties["disk_warning"] = -15
            score -= 15
        elif disk_percent >= 85:
            penalties["disk_elevated"] = -8
            score -= 8

    if temperature_c is not None:
        if temperature_c >= TEMP_CRIT:
            penalties["temp_critical"] = -20
            score -= 20
        elif temperature_c >= TEMP_WARN:
            penalties["temp_warning"] = -10
            score -= 10

    smart = (smart_status or "").lower()
    if smart in {"failing", "failed", "critical", "bad"}:
        penalties["smart_failing"] = -30
        score -= 30
    elif smart in {"warning", "degraded", "prefail"}:
        penalties["smart_warning"] = -15
        score -= 15

    # Attribute-level penalties (additive with status, but capped)
    crit_totals = _aggregate_smart_critical(smart_details)
    if crit_totals:
        factors["smart_critical"] = crit_totals
        realloc = crit_totals.get("reallocated_sectors", 0)
        pending = crit_totals.get("current_pending_sectors", 0)
        uncorr = (
            crit_totals.get("offline_uncorrectable", 0)
            + crit_totals.get("reported_uncorrectable", 0)
        )
        media = crit_totals.get("media_errors", 0)

        attr_pen = 0
        if realloc >= SMART_REALLOC_CRIT:
            attr_pen += 25
            penalties["smart_reallocated_critical"] = -25
        elif realloc >= SMART_REALLOC_WARN:
            attr_pen += 10
            penalties["smart_reallocated_warning"] = -10

        if pending >= SMART_PENDING_WARN:
            attr_pen += 12
            penalties["smart_pending_sectors"] = -12

        if uncorr >= SMART_UNCORRECT_WARN:
            attr_pen += 20
            penalties["smart_uncorrectable"] = -20

        if media > 10:
            attr_pen += 20
            penalties["smart_media_errors"] = -20
        elif media > 0:
            attr_pen += 8
            penalties["smart_media_errors"] = -8

        # Avoid double-counting when status already applied a large SMART penalty
        if smart in {"failing", "failed", "critical", "bad"}:
            attr_pen = min(attr_pen, 10)
        elif smart in {"warning", "degraded", "prefail"}:
            attr_pen = min(attr_pen, 15)

        score -= attr_pen

    score = max(0, min(100, score))
    factors["score"] = score
    if score >= 90:
        factors["grade"] = "A"
    elif score >= 80:
        factors["grade"] = "B"
    elif score >= 70:
        factors["grade"] = "C"
    elif score >= 60:
        factors["grade"] = "D"
    else:
        factors["grade"] = "F"
    return score, factors


class DeviceHealthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def on_heartbeat(
        self,
        *,
        agent_id: str,
        hostname: str | None = None,
        cpu_percent: float | None = None,
        memory_percent: float | None = None,
        disk_percent: float | None = None,
        temperature_c: float | None = None,
        smart_status: str | None = None,
        smart_details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        status: str = "online",
        raise_alerts: bool = True,
    ) -> dict[str, Any]:
        """Reset miss counters, recompute score, optionally fire threshold alerts."""
        from app.models.agent import Agent
        from app.models.device import Device

        now = _utcnow()
        score, factors = compute_health_score(
            status="online",
            consecutive_misses=0,
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_percent=disk_percent,
            temperature_c=temperature_c,
            smart_status=smart_status,
            smart_details=smart_details,
        )

        agent_uuid: UUID | None = None
        try:
            agent_uuid = UUID(str(agent_id))
        except Exception:
            agent_uuid = None

        if agent_uuid is not None:
            agent = self.db.get(Agent, agent_uuid)
            if agent:
                agent.status = "online"
                agent.last_seen = now
                agent.last_heartbeat = now
                agent.health_score = score
                if hostname:
                    agent.hostname = hostname
                if ip_address:
                    agent.ip_address = ip_address
                    agent.last_ip_address = ip_address

            device = (
                self.db.query(Device).filter(Device.id == agent_uuid).first()
            )
            if device is None and agent and agent.device_id:
                device = self.db.get(Device, agent.device_id)
            if device:
                device.status = "online"
                device.last_seen = now
                device.health_score = score
                device.consecutive_misses = 0
                device.missed_heartbeats = 0
                if hostname:
                    device.hostname = hostname
                if ip_address:
                    device.ip = ip_address
                    device.ip_address = ip_address
                if cpu_percent is not None:
                    device.cpu = int(cpu_percent)
                if memory_percent is not None:
                    device.ram = int(memory_percent)
                if disk_percent is not None:
                    device.disk = int(disk_percent)

        try:
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            logger.warning("health on_heartbeat commit failed: %s", exc)

        alerts: list[dict[str, Any]] = []
        if raise_alerts:
            alerts = self._evaluate_resource_alerts(
                target=hostname or agent_id,
                agent_id=agent_id,
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_percent=disk_percent,
                temperature_c=temperature_c,
                smart_status=smart_status,
                smart_details=smart_details,
            )

        return {
            "health_score": score,
            "grade": factors.get("grade"),
            "factors": factors,
            "status": "online",
            "alerts": alerts,
            "smart_details": smart_details,
        }

    def _evaluate_resource_alerts(
        self,
        *,
        target: str,
        agent_id: str,
        cpu_percent: float | None,
        memory_percent: float | None,
        disk_percent: float | None,
        temperature_c: float | None,
        smart_status: str | None,
        smart_details: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        from app.services.monitoring_service import MonitoringService

        svc = MonitoringService(self.db)
        out: list[dict[str, Any]] = []
        checks = [
            ("cpu", "cpu_percent", cpu_percent, CPU_WARN, CPU_CRIT),
            ("memory", "memory_percent", memory_percent, MEM_WARN, MEM_CRIT),
            ("disk", "disk_percent", disk_percent, DISK_WARN, DISK_CRIT),
            ("temperature", "temperature_c", temperature_c, TEMP_WARN, TEMP_CRIT),
        ]
        for check_type, metric_name, value, warn, crit in checks:
            if value is None:
                continue
            try:
                check, alerts = svc.evaluate_check(
                    provider="agent",
                    check_type=check_type,
                    target=target,
                    payload={"agent_id": agent_id, metric_name: value},
                    status="healthy",
                    metric_name=metric_name,
                    metric_value=float(value),
                    warning_threshold=warn,
                    critical_threshold=crit,
                    correlation_key=f"agent:{agent_id}:{check_type}",
                    use_rules=True,
                )
                for a in alerts:
                    out.append(
                        {
                            "id": str(a.id),
                            "severity": a.severity,
                            "message": a.message,
                            "check_type": check_type,
                            "metric_value": value,
                        }
                    )
            except Exception as exc:
                logger.debug("resource alert %s failed: %s", check_type, exc)

        smart = (smart_status or "").lower()
        crit_totals = _aggregate_smart_critical(smart_details)
        if crit_totals and smart in {"ok", "passed", "healthy", "good", ""}:
            if (
                crit_totals.get("offline_uncorrectable", 0)
                or crit_totals.get("reported_uncorrectable", 0)
                or crit_totals.get("media_errors", 0) > 10
                or crit_totals.get("reallocated_sectors", 0) >= SMART_REALLOC_CRIT
            ):
                smart = "failing"
            else:
                smart = "warning"

        if smart and smart not in {"ok", "passed", "healthy", "good", ""}:
            try:
                payload: dict[str, Any] = {
                    "agent_id": agent_id,
                    "smart_status": smart_status or smart,
                }
                if crit_totals:
                    payload["smart_critical"] = crit_totals
                check, alerts = svc.evaluate_check(
                    provider="agent",
                    check_type="smart",
                    target=target,
                    payload=payload,
                    status="critical" if smart in {"failing", "failed", "critical"} else "warning",
                    state_value=smart_status or smart,
                    correlation_key=f"agent:{agent_id}:smart",
                    use_rules=True,
                )
                for a in alerts:
                    out.append(
                        {
                            "id": str(a.id),
                            "severity": a.severity,
                            "message": a.message,
                            "check_type": "smart",
                            "metric_value": smart_status or smart,
                        }
                    )
            except Exception as exc:
                logger.debug("smart alert failed: %s", exc)

        return out

    def process_stale_endpoints(self) -> dict[str, int]:
        """Increment miss counters, set offline/overdue, recompute scores."""
        from app.models.agent import Agent
        from app.models.device import Device

        now = _utcnow()

        stats = {"agents_updated": 0, "devices_updated": 0, "offline": 0, "overdue": 0}

        agents = (
            self.db.query(Agent)
            .filter(Agent.revoked.is_(False))
            .filter(Agent.status.in_(["online", "overdue", "unknown"]))
            .all()
        )
        for agent in agents:
            seen = _aware(agent.last_heartbeat or agent.last_seen)
            if seen is None:
                continue
            age = (now - seen).total_seconds()
            new_status = status_from_age(age)
            if new_status == "online":
                continue

            interval = max(10, int(agent.heartbeat_interval or 30))
            misses = max(1, int(age // interval))

            score, _ = compute_health_score(
                status=new_status,
                consecutive_misses=misses,
            )
            agent.status = new_status
            agent.health_score = score
            stats["agents_updated"] += 1
            if new_status == "offline":
                stats["offline"] += 1
            elif new_status == "overdue":
                stats["overdue"] += 1

        devices = (
            self.db.query(Device)
            .filter(Device.status.in_(["online", "overdue", "unknown"]))
            .all()
        )
        for device in devices:
            seen = _aware(device.last_seen)
            if seen is None:
                continue
            age = (now - seen).total_seconds()
            new_status = status_from_age(age)
            if new_status == "online":
                continue

            prev_misses = int(device.consecutive_misses or 0)
            device.consecutive_misses = prev_misses + 1
            device.missed_heartbeats = int(device.missed_heartbeats or 0) + 1
            device.status = new_status

            score, _ = compute_health_score(
                status=new_status,
                consecutive_misses=device.consecutive_misses,
                cpu_percent=float(device.cpu) if device.cpu is not None else None,
                memory_percent=float(device.ram) if device.ram is not None else None,
                disk_percent=float(device.disk) if device.disk is not None else None,
            )
            device.health_score = score
            stats["devices_updated"] += 1

        try:
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            logger.warning("process_stale_endpoints commit failed: %s", exc)
            return {**stats, "error": 1}

        return stats

    def get_health_snapshot(self, agent_or_device_id: str) -> dict[str, Any] | None:
        from app.models.agent import Agent
        from app.models.device import Device

        try:
            uid = UUID(str(agent_or_device_id))
        except Exception:
            return None

        agent = self.db.get(Agent, uid)
        device = self.db.get(Device, uid)

        cpu = ram = disk = None
        temp = smart = None
        smart_details = None
        status = "unknown"
        misses = 0
        last_seen = None
        hostname = None
        health_score = 100

        if agent:
            status = agent.status or "unknown"
            last_seen = agent.last_heartbeat or agent.last_seen
            hostname = agent.hostname
            health_score = agent.health_score
        if device:
            status = device.status or status
            last_seen = device.last_seen or last_seen
            hostname = device.hostname or hostname
            health_score = device.health_score if device.health_score is not None else health_score
            misses = int(device.consecutive_misses or 0)
            cpu = float(device.cpu) if device.cpu is not None else None
            ram = float(device.ram) if device.ram is not None else None
            disk = float(device.disk) if device.disk is not None else None

        try:
            from app.api.v1.endpoints import agent_runtime

            rt = (getattr(agent_runtime, "_agents", {}) or {}).get(str(agent_or_device_id))
            if rt:
                cpu = rt.get("cpu_percent", cpu)
                ram = rt.get("memory_percent", ram)
                disk = rt.get("disk_percent", disk)
                temp = rt.get("temperature_c", temp)
                smart = rt.get("smart_status", smart)
                smart_details = rt.get("smart_details", smart_details)
                hostname = rt.get("hostname") or hostname
                status = rt.get("status") or status
        except Exception:
            pass

        age = None
        seen = _aware(last_seen)
        if seen:
            age = (_utcnow() - seen).total_seconds()
            derived = status_from_age(age)
            if derived != "online" and status == "online":
                status = derived

        score, factors = compute_health_score(
            status=status,
            consecutive_misses=misses,
            cpu_percent=cpu,
            memory_percent=ram,
            disk_percent=disk,
            temperature_c=temp,
            smart_status=smart,
            smart_details=smart_details,
        )

        return {
            "id": str(agent_or_device_id),
            "hostname": hostname,
            "status": status,
            "health_score": score,
            "stored_health_score": health_score,
            "grade": factors.get("grade"),
            "factors": factors,
            "smart_details": smart_details,
            "last_seen": seen.isoformat() if seen else None,
            "age_seconds": age,
            "thresholds": {
                "cpu_warn": CPU_WARN,
                "cpu_crit": CPU_CRIT,
                "mem_warn": MEM_WARN,
                "mem_crit": MEM_CRIT,
                "disk_warn": DISK_WARN,
                "disk_crit": DISK_CRIT,
                "temp_warn": TEMP_WARN,
                "temp_crit": TEMP_CRIT,
                "online_secs": ONLINE_SECS,
                "overdue_secs": OVERDUE_SECS,
                "offline_secs": OFFLINE_SECS,
            },
        }
