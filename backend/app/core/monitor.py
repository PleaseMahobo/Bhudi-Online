import asyncio
from app.state.device_state import devices, mark_offline
from datetime import datetime, timedelta

async def monitor_devices():
    while True:
        now = datetime.utcnow()

        for device_id, device in list(devices.items()):
            if (now - device["last_seen"]).seconds > 30:
                mark_offline(device_id)

        await asyncio.sleep(10)