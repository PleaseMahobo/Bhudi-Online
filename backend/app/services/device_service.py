from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.device import Device


def get_devices(db: Session, tenant_id: UUID | None = None):
    """Return registered devices, scoped to the supplied tenant when present."""
    query = db.query(Device)
    if tenant_id is not None:
        query = query.filter(Device.tenant_id == tenant_id)
    return query.order_by(Device.id.asc()).all()


def get_device(
    db: Session,
    device_id: str,
    tenant_id: UUID | None = None,
):
    """Return a single device, optionally constrained to a tenant."""
    query = db.query(Device).filter(Device.id == device_id)
    if tenant_id is not None:
        query = query.filter(Device.tenant_id == tenant_id)
    return query.first()


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
        .filter(Device.id == device_id)
        .first()
    )

    if device is None:
        return None

    device.status = status
    device.last_seen = datetime.now(timezone.utc)

    db.commit()
    db.refresh(device)

    return device
