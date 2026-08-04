from datetime import datetime

from sqlalchemy.orm import Session

from app.models.device import Device


def get_devices(db: Session):
    """
    Return all registered devices.
    """

    return (
        db.query(Device)
        .order_by(Device.device_id.asc())
        .all()
    )


def get_device(
    db: Session,
    device_id: str,
):
    """
    Return a single device by its device_id.
    """

    return (
        db.query(Device)
        .filter(Device.device_id == device_id)
        .first()
    )


def update_device_status(
    db: Session,
    device_id: str,
    status: str,
):
    """
    Update a device's status and last_seen timestamp.
    """

    device = (
        db.query(Device)
        .filter(Device.device_id == device_id)
        .first()
    )

    if device is None:
        return None

    device.status = status
    device.last_seen = datetime.utcnow()

    db.commit()
    db.refresh(device)

    return device