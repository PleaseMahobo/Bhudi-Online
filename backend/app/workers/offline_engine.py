from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.device import Device
from datetime import datetime, timedelta
import time


OFFLINE_THRESHOLD_SECONDS = 30


def run_offline_detector():
    while True:
        db: Session = SessionLocal()

        cutoff = datetime.utcnow() - timedelta(seconds=OFFLINE_THRESHOLD_SECONDS)

        devices = db.query(Device).all()

        for d in devices:
            if d.last_seen and d.last_seen < cutoff:
                d.status = "offline"

        db.commit()
        db.close()

        time.sleep(10)