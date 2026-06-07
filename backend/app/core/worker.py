import asyncio
from datetime import datetime, timedelta

# simple in-memory heartbeat tracker (replace with DB later)
device_last_seen = {}


def update_heartbeat(device_id: str):
    if not device_id or device_id == "string":
        return
    device_last_seen[device_id] = datetime.utcnow()


def get_offline_devices(timeout_seconds: int = 60):
    now = datetime.utcnow()
    offline = []

    for device_id, last_seen in device_last_seen.items():
        if now - last_seen > timedelta(seconds=timeout_seconds):
            offline.append(device_id)

    return offline


async def offline_monitor():
    while True:
        offline = get_offline_devices()

        if offline:
            print(f"[OFFLINE DETECTED] {offline}")

        await asyncio.sleep(10)

