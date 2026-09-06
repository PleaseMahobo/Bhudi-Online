from datetime import datetime, timedelta, timezone
from typing import Any

devices: dict[str, dict[str, Any]] = {}

ONLINE = timedelta(seconds=45)
OVERDUE = timedelta(seconds=300)


def register_device(
    device_id: str,
    *,
    tenant_id: str | None = None,
    hostname: str | None = None,
) -> None:
    now = datetime.now(timezone.utc)
    existing = devices.get(device_id) or {}
    devices[device_id] = {
        **existing,
        "device_id": device_id,
        "id": device_id,
        "agent_id": device_id,
        "status": "online",
        "last_seen": now,
        "last_command": existing.get("last_command"),
        "tenant_id": tenant_id or existing.get("tenant_id"),
        "hostname": hostname or existing.get("hostname"),
        "source": "memory",
    }


def heartbeat(device_id: str, tenant_id: str | None = None) -> None:
    now = datetime.now(timezone.utc)
    if device_id not in devices:
        register_device(device_id, tenant_id=tenant_id)
    devices[device_id]["status"] = "online"
    devices[device_id]["last_seen"] = now
    if tenant_id:
        devices[device_id]["tenant_id"] = tenant_id


def mark_offline(device_id: str) -> None:
    if device_id in devices:
        devices[device_id]["status"] = "offline"


def _apply_staleness(d: dict) -> None:
    now = datetime.now(timezone.utc)
    seen = d.get("last_seen")
    if not isinstance(seen, datetime):
        return
    if seen.tzinfo is None:
        seen = seen.replace(tzinfo=timezone.utc)
    age = now - seen
    if age <= ONLINE:
        d["status"] = "online"
    elif age <= OVERDUE:
        d["status"] = "offline"
    else:
        d["status"] = "overdue"


def get_devices() -> list[dict[str, Any]]:
    for d in devices.values():
        _apply_staleness(d)
    return list(devices.values())


def add_command(device_id: str, command: str) -> None:
    if device_id in devices:
        devices[device_id]["last_command"] = {
            "command": command,
            "timestamp": datetime.now(timezone.utc),
        }
