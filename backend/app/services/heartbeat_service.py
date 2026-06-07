from datetime import datetime
from app.core.database import SessionLocal
from app.models.device import Device


class HeartbeatService:

    @staticmethod
    def beat(device_id: int, ip: str = None, hostname: str = None):

        db = SessionLocal()

        try:
            device = db.query(Device).filter(Device.id == device_id).first()

            if not device:
                device = Device(
                    id=device_id,
                    ip_address=ip,
                    hostname=hostname,
                    status="online",
                    last_seen=datetime.utcnow()
                )
                db.add(device)

            else:
                device.last_seen = datetime.utcnow()
                device.status = "online"

                if ip:
                    device.ip_address = ip

                if hostname:
                    device.hostname = hostname

            db.commit()

        finally:
            db.close()