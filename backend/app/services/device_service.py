from datetime import datetime
from sqlalchemy.orm import Session
from app.models.device import Device

class DeviceService:

    @staticmethod
    def register(db: Session, device_id: str):

        device = (
            db.query(Device)
            .filter(Device.device_id == device_id)
            .first()
        )

        if device:
            device.last_seen = datetime.utcnow()
            device.status = "online"
        else:
            device = Device(
                device_id=device_id,
                status="online",
                last_seen=datetime.utcnow()
            )
            db.add(device)

        db.commit()
        db.refresh(device)

        return device