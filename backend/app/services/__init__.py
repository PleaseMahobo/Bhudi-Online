from sqlalchemy.orm import Session
from app.models.device import Device
from datetime import datetime


def update_device(
    db: Session,
    device_id: str,
    hostname: str,
    ip: str
):
    device = db.query(Device).filter(
        Device.device_id == device_id
    ).first()

    if not device:
        device = Device(
            device_id=device_id,
            hostname=hostname,
            ip=ip,
            status="online",
            last_seen=datetime.utcnow()
        )

        db.add(device)

    else:
        device.hostname = hostname
        device.ip = ip
        device.status = "online"
        device.last_seen = datetime.utcnow()

    db.commit()
    db.refresh(device)

    return device