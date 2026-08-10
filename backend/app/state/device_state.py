from datetime import datetime, timedelta, timezone

devices = {}

ONLINE = timedelta(seconds=45)
OVERDUE = timedelta(seconds=300)


def register_device(device_id: str):
    devices[device_id] = {
        "device_id": device_id,
        "status": "online",
        "last_seen": datetime.now(timezone.utc),
        "last_command": None,
    }


def heartbeat(device_id: str):
    if device_id in devices:
        devices[device_id]["status"] = "online"
        devices[device_id]["last_seen"] = datetime.now(timezone.utc)


def mark_offline(device_id: str):
    if device_id in devices:
        devices[device_id]["status"] = "offline"


def _apply_staleness(d: dict):
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


def get_devices():
    for d in devices.values():
        _apply_staleness(d)
    return list(devices.values())


def add_command(device_id: str, command: str):
    if device_id in devices:
        devices[device_id]["last_command"] = {
            "command": command,
            "timestamp": datetime.now(timezone.utc),
        }
