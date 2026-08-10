"""Device listing + status for dashboard (unified DB + runtime agents)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.state import device_state
from app.services import device_service

router = APIRouter()

ONLINE_SECS = 45
OVERDUE_SECS = 300


def _parse_seen(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None
    return None


def _status_from_last_seen(last_seen: Any, explicit: str | None = None) -> str:
    seen = _parse_seen(last_seen)
    if seen is None:
        return (explicit or "unknown").lower()
    now = datetime.now(timezone.utc)
    age = (now - seen).total_seconds()
    if age <= ONLINE_SECS:
        return "online"
    if age <= OVERDUE_SECS:
        return "offline"
    return "overdue"


def _normalize_row(raw: dict[str, Any]) -> dict[str, Any]:
    agent_id = str(raw.get("agent_id") or raw.get("id") or raw.get("device_id") or "")
    last_seen = raw.get("last_seen")
    if hasattr(last_seen, "isoformat"):
        last_seen_s = last_seen.isoformat()
    else:
        last_seen_s = last_seen
    status = _status_from_last_seen(last_seen, raw.get("status"))
    return {
        "id": agent_id,
        "device_id": agent_id,
        "agent_id": agent_id,
        "hostname": raw.get("hostname") or raw.get("name") or agent_id or "Unknown",
        "name": raw.get("name") or raw.get("hostname"),
        "status": status,
        "online": status == "online",
        "platform": raw.get("platform"),
        "agent_version": raw.get("agent_version") or raw.get("version"),
        "ip_address": raw.get("ip_address") or raw.get("ip"),
        "cpu_percent": raw.get("cpu_percent"),
        "memory_percent": raw.get("memory_percent"),
        "disk_percent": raw.get("disk_percent"),
        "last_seen": last_seen_s,
        "source": raw.get("source") or "unknown",
    }


def _runtime_agents() -> list[dict[str, Any]]:
    try:
        from app.api.v1.endpoints import agent_runtime

        agents = getattr(agent_runtime, "_agents", {}) or {}
        out = []
        for a in agents.values():
            row = dict(a)
            row["source"] = "runtime"
            row["id"] = a.get("agent_id")
            row["device_id"] = a.get("agent_id")
            out.append(_normalize_row(row))
        return out
    except Exception as exc:
        print(f"[devices] runtime agents unavailable: {exc}")
        return []


@router.get("/status")
def device_status():
    """Lightweight status used by the frontend dashboard."""
    return list_devices_unified()


@router.get("/")
def list_devices(db: Session = Depends(get_db)):
    return list_devices_unified(db)


def list_devices_unified(db: Session | None = None) -> dict[str, Any]:
    by_id: dict[str, dict[str, Any]] = {}

    for row in _runtime_agents():
        if row["id"]:
            by_id[row["id"]] = row

    try:
        for d in device_state.get_devices():
            row = _normalize_row({**d, "source": d.get("source") or "memory"})
            if not row["id"]:
                continue
            if row["id"] in by_id:
                for k, v in row.items():
                    if by_id[row["id"]].get(k) in (None, "", "unknown") and v not in (None, ""):
                        by_id[row["id"]][k] = v
                by_id[row["id"]]["status"] = _status_from_last_seen(
                    by_id[row["id"]].get("last_seen"), by_id[row["id"]].get("status")
                )
                by_id[row["id"]]["online"] = by_id[row["id"]]["status"] == "online"
            else:
                by_id[row["id"]] = row
    except Exception as exc:
        print(f"[devices] memory list failed: {exc}")

    if db is not None:
        try:
            rows = device_service.get_devices(db)
            for d in rows:
                rid = str(getattr(d, "id", "") or "")
                row = _normalize_row(
                    {
                        "id": rid,
                        "device_id": rid,
                        "hostname": getattr(d, "hostname", None),
                        "status": getattr(d, "status", None),
                        "ip": getattr(d, "ip", None),
                        "last_seen": getattr(d, "last_seen", None),
                        "source": "db",
                    }
                )
                if not row["id"]:
                    continue
                if row["id"] not in by_id:
                    by_id[row["id"]] = row
        except Exception as exc:
            print(f"[devices] DB list failed: {exc}")

    devices = sorted(
        by_id.values(),
        key=lambda r: (0 if r.get("status") == "online" else 1, str(r.get("hostname") or "").lower()),
    )
    counts = {"online": 0, "offline": 0, "overdue": 0, "unknown": 0}
    for d in devices:
        s = d.get("status") or "unknown"
        counts[s] = counts.get(s, 0) + 1

    return {"devices": devices, "count": len(devices), "counts": counts}
