"""Hardware monitoring (SMART / temperature) backed by agent-reported data."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.monitoring_service import MonitoringService

router = APIRouter(tags=["Monitoring"])


class SmartMonitoringRequest(BaseModel):
    provider: str = "smart"
    device: str | None = None
    agent_id: str | None = None


class TemperatureMonitoringRequest(BaseModel):
    provider: str = "temperature"
    sensors: list[str] | None = None
    agent_id: str | None = None


class MonitoringResponse(BaseModel):
    provider: str
    status: str
    summary: dict[str, Any]
    resources: list[dict[str, Any]]


def _runtime_agents() -> dict[str, dict[str, Any]]:
    try:
        from app.api.v1.endpoints import agent_runtime

        return getattr(agent_runtime, "_agents", {}) or {}
    except Exception:
        return {}


def _build_response(
    provider: str, items: list[dict[str, Any]], *, extra: dict[str, Any] | None = None
) -> MonitoringResponse:
    has_warning = any(item.get("status") in {"warning", "critical", "failing"} for item in items)
    has_crit = any(item.get("status") in {"critical", "failing"} for item in items)
    summary = {
        "resource_count": len(items),
        "healthy_count": sum(1 for item in items if item.get("status") in {"ok", "healthy"}),
        "warning_count": sum(1 for item in items if item.get("status") == "warning"),
        "critical_count": sum(1 for item in items if item.get("status") in {"critical", "failing"}),
        "source": "agent" if items and items[0].get("source") == "agent" else "catalog",
    }
    if extra:
        summary.update(extra)
    status = "critical" if has_crit else ("warning" if has_warning else "healthy")
    return MonitoringResponse(provider=provider, status=status, summary=summary, resources=items)


@router.post("/smart", response_model=MonitoringResponse)
def smart_monitoring(
    payload: SmartMonitoringRequest,
    db: Session = Depends(get_db),
) -> MonitoringResponse:
    agents = _runtime_agents()
    resources: list[dict[str, Any]] = []

    def _agent_row(aid: str, a: dict[str, Any]) -> dict[str, Any] | None:
        status = (a.get("smart_status") or "").lower()
        if not status and not a.get("smart_details"):
            return None
        mapped = "ok"
        if status in {"failing", "failed", "critical", "bad"}:
            mapped = "failing"
        elif status in {"warning", "degraded", "prefail"}:
            mapped = "warning"
        elif status in {"unknown", "unavailable"}:
            mapped = "warning"
        return {
            "type": "smart",
            "status": mapped,
            "health": status or "unknown",
            "agent_id": aid,
            "hostname": a.get("hostname"),
            "details": a.get("smart_details"),
            "source": "agent",
        }

    if payload.agent_id and payload.agent_id in agents:
        row = _agent_row(payload.agent_id, agents[payload.agent_id])
        if row:
            resources.append(row)
    else:
        for aid, a in agents.items():
            row = _agent_row(aid, a)
            if row:
                resources.append(row)

    if not resources:
        # No agent data yet — honest empty result rather than fake OK
        resources = [
            {
                "type": "smart",
                "status": "warning",
                "health": "no_agent_data",
                "device": payload.device or "any",
                "message": "No agent has reported SMART status yet",
                "source": "catalog",
            }
        ]

    overall = "healthy"
    if any(r.get("status") == "failing" for r in resources):
        overall = "critical"
    elif any(r.get("status") == "warning" for r in resources):
        overall = "warning"

    MonitoringService(db).record_check(
        provider="smart",
        check_type="smart",
        target=payload.agent_id or payload.device or "fleet",
        payload={"agent_id": payload.agent_id, "device": payload.device},
        status=overall,
        details={"resource_count": len(resources)},
    )
    return _build_response("smart", resources)


@router.post("/temperature", response_model=MonitoringResponse)
def temperature_monitoring(
    payload: TemperatureMonitoringRequest,
    db: Session = Depends(get_db),
) -> MonitoringResponse:
    agents = _runtime_agents()
    resources: list[dict[str, Any]] = []

    def _agent_row(aid: str, a: dict[str, Any]) -> dict[str, Any] | None:
        temp = a.get("temperature_c")
        if temp is None:
            return None
        try:
            t = float(temp)
        except Exception:
            return None
        status = "ok"
        if t >= 90:
            status = "critical"
        elif t >= 80:
            status = "warning"
        return {
            "type": "temperature",
            "status": status,
            "health": status,
            "sensor": "package",
            "value_c": t,
            "agent_id": aid,
            "hostname": a.get("hostname"),
            "source": "agent",
        }

    if payload.agent_id and payload.agent_id in agents:
        row = _agent_row(payload.agent_id, agents[payload.agent_id])
        if row:
            resources.append(row)
    else:
        for aid, a in agents.items():
            row = _agent_row(aid, a)
            if row:
                resources.append(row)

    if not resources:
        resources = [
            {
                "type": "temperature",
                "status": "warning",
                "health": "no_agent_data",
                "message": "No agent has reported temperature yet",
                "source": "catalog",
            }
        ]

    overall = "healthy"
    if any(r.get("status") == "critical" for r in resources):
        overall = "critical"
    elif any(r.get("status") == "warning" for r in resources):
        overall = "warning"

    MonitoringService(db).record_check(
        provider="temperature",
        check_type="temperature",
        target=payload.agent_id or "fleet",
        payload={"agent_id": payload.agent_id, "sensors": payload.sensors},
        status=overall,
        details={"resource_count": len(resources)},
    )
    return _build_response("temperature", resources)
