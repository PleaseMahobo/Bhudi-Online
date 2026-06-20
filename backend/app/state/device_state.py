from datetime import datetime

devices = {}

def register_device(device_id: str):
    devices[device_id] = {
        "device_id": device_id,
        "status": "online",
        "last_seen": datetime.utcnow().isoformat()
    }

def heartbeat(device_id: str):
    if device_id in devices:
        devices[device_id]["status"] = "online"
        devices[device_id]["last_seen"] = datetime.utcnow().isoformat()

def get_devices():
    return list(devices.values())

def mark_offline(device_id: str):
    if device_id in devices:
        devices[device_id]["status"] = "offline"