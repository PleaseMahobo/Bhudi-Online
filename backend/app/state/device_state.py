from datetime import datetime, timedelta, timezone

devices = {}

def register_device(device_id: str):
    devices[device_id] = {
        "device_id": device_id,
        "status": "online",
        "last_seen": datetime.now(timezone.utc),
        "last_command": None
    }

def heartbeat(device_id: str):
    if device_id in devices:
        devices[device_id]["status"] = "online"
        devices[device_id]["last_seen"] = datetime.now(timezone.utc)

def mark_offline(device_id: str):
    if device_id in devices:
        devices[device_id]["status"] = "offline"

def get_devices():
    now = datetime.now(timezone.utc)

    for d in devices.values():
        if (now - d["last_seen"]) > timedelta(seconds=30):
            d["status"] = "offline"

    return list(devices.values())

def add_command(device_id: str, command: str):
    if device_id in devices:
        devices[device_id]["last_command"] = {
            "command": command,
            "timestamp": datetime.now(timezone.utc)
        }