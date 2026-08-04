from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.device import Device


class DeviceRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_all(self) -> list[Device]:
        return (
            self.db.query(Device)
            .order_by(Device.last_seen.desc().nullslast())
            .all()
        )

    def get(self, device_id: Any) -> Device | None:
        return self.db.query(Device).filter(Device.id == device_id).first()

    def touch(self, device: Device, status: str = "online") -> Device:
        device.status = status
        device.last_seen = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(device)
        return device
