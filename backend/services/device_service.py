from sqlalchemy.orm import Session
from app.models.device import Device
from datetime import datetime


def upsert_device(db: Session, device_id: str, hostname: str, ip: str):
    device = db.query(Device).filter(Device.device_id == device_id).first()

    if device:
        device.hostname = hostname
        device.ip = ip
        device.last_seen = datetime.utcnow()
    else:
        device = Device(
            device_id=device_id,
            hostname=hostname,
            ip=ip,
            last_seen=datetime.utcnow()
        )
        db.add(device)

    db.commit()
    db.refresh(device)
    return device