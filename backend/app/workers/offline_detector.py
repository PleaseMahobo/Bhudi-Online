from datetime import datetime, timedelta
from app.core.database import SessionLocal
from app.models.device import Device


OFFLINE_THRESHOLD_SECONDS = 120  # 2 minutes


def run_offline_detection():

    db = SessionLocal()

    try:
        cutoff = datetime.utcnow() - timedelta(seconds=OFFLINE_THRESHOLD_SECONDS)

        stale_devices = db.query(Device).filter(
            Device.last_seen < cutoff,
            Device.status == "online"
        ).all()

        for device in stale_devices:
            device.status = "offline"

        db.commit()

        if stale_devices:
            print(f"[OFFLINE ENGINE] Marked {len(stale_devices)} devices offline")

    except Exception as e:
        print("[OFFLINE ENGINE ERROR]", e)

    finally:
        db.close()