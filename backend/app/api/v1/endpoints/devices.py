"""Device listing + status for dashboard (unified DB + runtime agents)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
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
        "organization_id": str(raw["organization_id"]) if raw.get("organization_id") else None,
        "organization_name": raw.get("organization_name"),
        "site_id": str(raw["site_id"]) if raw.get("site_id") else None,
        "site_name": raw.get("site_name"),
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
                        "organization_id": getattr(d, "organization_id", None),
                        "site_id": getattr(d, "site_id", None),
                    }
                )
                if not row["id"]:
                    continue
                if row["id"] not in by_id:
                    by_id[row["id"]] = row
        except Exception as exp:
            print(f"[devices] DB list failed: {exp}")

    devices = sorted(
        by_id.values(),
        key=lambda r: (0 if r.get("status") == "online" else 1, str(r.get("hostname") or "").lower()),
    )
    counts = {"online": 0, "offline": 0, "overdue": 0, "unknown": 0}
    for d in devices:
        s = d.get("status") or "unknown"
        counts[s] = counts.get(s, 0) + 1

    return {"devices": devices, "count": len(devices), "counts": counts}


def _find_agent(device_id: str) -> dict[str, Any] | None:
    try:
        from app.api.v1.endpoints import agent_runtime

        agents = getattr(agent_runtime, "_agents", {}) or {}
        if device_id in agents:
            return agents[device_id]
        for a in agents.values():
            if str(a.get("agent_id")) == device_id or str(a.get("hostname")) == device_id:
                return a
    except Exception:
        pass
    for d in device_state.get_devices():
        if str(d.get("device_id") or d.get("id")) == device_id:
            return d
    return None


@router.get("/{device_id}")
def get_device(device_id: str, db: Session = Depends(get_db)):
    unified = list_devices_unified(db)
    for d in unified["devices"]:
        if d.get("id") == device_id or d.get("hostname") == device_id:
            return d
    raise HTTPException(status_code=404, detail="Device not found")


@router.post("/{device_id}/inventory/{kind}")
def request_inventory(device_id: str, kind: str):
    kind = kind.lower().strip()
    if kind not in ("processes", "software"):
        raise HTTPException(400, "kind must be processes or software")

    agent = _find_agent(device_id)
    if not agent:
        raise HTTPException(404, "Agent not found — device must be enrolled and online")

    agent_id = str(agent.get("agent_id") or device_id)
    platform = str(agent.get("platform") or "").lower()

    if kind == "processes":
        if "win" in platform:
            cmd = "tasklist /fo csv /nh"
        else:
            cmd = "ps -eo pid,user,%cpu,%mem,comm --sort=-%cpu | head -80"
    else:
        if "win" in platform:
            cmd = (
                "powershell -NoProfile -Command "
                '"Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* '
                ", HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* "
                "| Select-Object DisplayName, DisplayVersion | Where-Object DisplayName | "
                'ConvertTo-Csv -NoTypeInformation"'
            )
        elif "darwin" in platform or "macos" in platform:
            cmd = "ls /Applications | head -100"
        else:
            cmd = "dpkg-query -W -f='${Package}\\t${Version}\\n' 2>/dev/null | head -100 || rpm -qa | head -100"

    try:
        from app.api.v1.endpoints import agent_runtime

        if agent_id not in agent_runtime._agents:
            raise HTTPException(404, "Runtime agent not found")
        body = agent_runtime.CommandCreate(command=cmd, shell=True)
        result = agent_runtime.queue_command(agent_id, body)
        return {
            "accepted": True,
            "command_id": result.get("command_id"),
            "kind": kind,
            "command": cmd,
            "agent_id": agent_id,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"Failed to queue inventory: {exc}") from exc


@router.get("/{device_id}/commands/{command_id}")
def get_device_command(device_id: str, command_id: str):
    try:
        from app.api.v1.endpoints import agent_runtime

        agent_id = device_id
        agent = _find_agent(device_id)
        if agent:
            agent_id = str(agent.get("agent_id") or device_id)
        for c in agent_runtime._commands.get(agent_id, []):
            if c.get("command_id") == command_id:
                return {
                    "command_id": command_id,
                    "status": c.get("status"),
                    "command": c.get("command"),
                    "result": c.get("result"),
                    "finished_at": c.get("finished_at"),
                }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc
    raise HTTPException(404, "Command not found")
