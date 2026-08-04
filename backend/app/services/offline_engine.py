import asyncio
from datetime import datetime, timedelta, timezone
from app.services.device_registry import DeviceRegistry


class OfflineDetectionEngine:
    def __init__(self, registry: DeviceRegistry, timeout_seconds: int = 60):
        self.registry = registry
        self.timeout = timedelta(seconds=timeout_seconds)

    async def run(self):
        while True:
            now = datetime.now(timezone.utc)

            for device_id, device in self.registry.devices.items():
                last_seen = device["last_seen"]

                if now - last_seen > self.timeout:
                    self.registry.mark_offline(device_id)

            await asyncio.sleep(10)