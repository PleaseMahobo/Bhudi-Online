from datetime import datetime, timedelta, timezone
from app.api.devices import DEVICE_REGISTRY


OFFLINE_THRESHOLD_SECONDS = 60  # 1 minute for testing


def check_offline_devices():
    now = datetime.now(timezone.utc)

    for device_id, device in DEVICE_REGISTRY.items():
        last_seen = device.get("last_seen")

        if not last_seen:
            continue

        delta = now - last_seen

        if delta > timedelta(seconds=OFFLINE_THRESHOLD_SECONDS):
            device["status"] = "offline"