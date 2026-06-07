import asyncio
from datetime import datetime, timedelta
from app.core.database import SessionLocal
from app.models.device import Device

OFFLINE_THRESHOLD = 60

async def offline_worker():
    while True:
        db = SessionLocal()
        devices = db.query(Device).all()

        now = datetime.utcnow()

        for d in devices:
            if d.last_seen and (now - d.last_seen).seconds > OFFLINE_THRESHOLD:
                d.status = "offline"

        db.commit()
        db.close()

        await asyncio.sleep(10)