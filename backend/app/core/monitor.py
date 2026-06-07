import time
from datetime import datetime, timedelta
from app.core.db import SessionLocal
from app.models.device import Device


OFFLINE_THRESHOLD_SECONDS = 30


def monitor_loop():
    while True:
        db = SessionLocal()
        now = datetime.utcnow()

        devices = db.query(Device).all()

        for d in devices:
            if d.last_seen and now - d.last_seen > timedelta(seconds=OFFLINE_THRESHOLD_SECONDS):
                if d.status != "offline":
                    print(f"[OFFLINE] {d.device_id}")
                    d.status = "offline"

        db.commit()
        db.close()

        time.sleep(10)