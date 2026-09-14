"""Device health snapshot API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.services.device_health_service import DeviceHealthService

router = APIRouter(prefix="/device-health", tags=["Device Health"])


@router.get("/{device_id}")
def get_device_health(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    snap = DeviceHealthService(db).get_health_snapshot(device_id)
    if not snap:
        raise HTTPException(404, "Device/agent not found or invalid id")
    return snap


@router.post("/recompute-stale")
def recompute_stale(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admin-triggered pass of missed-heartbeat processing."""
    stats = DeviceHealthService(db).process_stale_endpoints()
    return {"ok": True, **stats}
