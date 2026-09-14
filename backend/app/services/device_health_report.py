"""Daily device health report aggregation."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _grade(score: int | None) -> str:
    if score is None:
        return "—"
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def build_device_health_daily_report(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    limit_worst: int = 25,
) -> dict[str, Any]:
    """Aggregate fleet health for a daily report (JSON-serializable)."""
    from app.models.agent import Agent
    from app.models.device import Device

    now = _utcnow()
    devices: list[dict[str, Any]] = []

    q = db.query(Device)
    if tenant_id is not None and hasattr(Device, "tenant_id"):
        q = q.filter(Device.tenant_id == tenant_id)
    try:
        for d in q.all():
            score = getattr(d, "health_score", None)
            try:
                score = int(score) if score is not None else None
            except Exception:
                score = None
            status = (getattr(d, "status", None) or "unknown").lower()
            devices.append(
                {
                    "id": str(d.id),
                    "hostname": getattr(d, "hostname", None) or str(d.id),
                    "status": status,
                    "health_score": score,
                    "health_grade": _grade(score),
                    "consecutive_misses": int(getattr(d, "consecutive_misses", 0) or 0),
                    "cpu": getattr(d, "cpu", None),
                    "ram": getattr(d, "ram", None),
                    "disk": getattr(d, "disk", None),
                    "last_seen": (
                        d.last_seen.isoformat()
                        if getattr(d, "last_seen", None) is not None
                        and hasattr(d.last_seen, "isoformat")
                        else None
                    ),
                    "source": "device",
                }
            )
    except Exception:
        pass

    seen = {d["id"] for d in devices}
    try:
        aq = db.query(Agent).filter(Agent.revoked.is_(False))
        if tenant_id is not None and hasattr(Agent, "tenant_id"):
            aq = aq.filter(Agent.tenant_id == tenant_id)
        for a in aq.all():
            aid = str(a.id)
            if aid in seen:
                for d in devices:
                    if d["id"] == aid and d.get("health_score") is None:
                        try:
                            d["health_score"] = (
                                int(a.health_score) if a.health_score is not None else None
                            )
                            d["health_grade"] = _grade(d["health_score"])
                        except Exception:
                            pass
                continue
            score = getattr(a, "health_score", None)
            try:
                score = int(score) if score is not None else None
            except Exception:
                score = None
            ls = a.last_heartbeat or a.last_seen
            devices.append(
                {
                    "id": aid,
                    "hostname": a.hostname or aid,
                    "status": (a.status or "unknown").lower(),
                    "health_score": score,
                    "health_grade": _grade(score),
                    "consecutive_misses": 0,
                    "cpu": None,
                    "ram": None,
                    "disk": None,
                    "last_seen": ls.isoformat() if ls is not None and hasattr(ls, "isoformat") else None,
                    "source": "agent",
                }
            )
    except Exception:
        pass

    total = len(devices)
    by_status: dict[str, int] = {}
    by_grade: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0, "—": 0}
    scores: list[int] = []
    offline = overdue = online = 0
    for d in devices:
        st = d.get("status") or "unknown"
        by_status[st] = by_status.get(st, 0) + 1
        if st == "online":
            online += 1
        elif st == "overdue":
            overdue += 1
        elif st == "offline":
            offline += 1
        g = d.get("health_grade") or "—"
        by_grade[g] = by_grade.get(g, 0) + 1
        if d.get("health_score") is not None:
            scores.append(int(d["health_score"]))

    avg_score = round(sum(scores) / len(scores), 1) if scores else None
    unhealthy = [
        d
        for d in devices
        if (d.get("health_score") is not None and d["health_score"] < 70)
        or d.get("status") in ("offline", "overdue")
    ]
    unhealthy.sort(key=lambda x: (x.get("health_score") is None, x.get("health_score") or 0))
    worst = unhealthy[: max(1, min(limit_worst, 100))]

    return {
        "report_type": "device_health",
        "name": "Daily Device Health Report",
        "generated_at": now.isoformat(),
        "tenant_id": str(tenant_id) if tenant_id else None,
        "summary": {
            "total_devices": total,
            "online": online,
            "overdue": overdue,
            "offline": offline,
            "avg_health_score": avg_score,
            "by_status": by_status,
            "by_grade": by_grade,
            "unhealthy_count": len(unhealthy),
        },
        "worst_devices": worst,
        "devices": devices,
    }
