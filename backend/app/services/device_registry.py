from datetime import datetime, timezone
from typing import Dict

class DeviceRegistry:
    def __init__(self):
        self.devices: Dict[str, dict] = {}

    def register(self, device_id: str, data: dict):
        self.devices[device_id] = {
            "device_id": device_id,
            "data": data,
            "last_seen": datetime.now(timezone.utc),
            "status": "online"
        }

    def heartbeat(self, device_id: str):
        if device_id in self.devices:
            self.devices[device_id]["last_seen"] = datetime.now(timezone.utc)
            self.devices[device_id]["status"] = "online"

    def mark_offline(self, device_id: str):
        if device_id in self.devices:
            self.devices[device_id]["status"] = "offline"

    def get_all(self):
        return self.devices