"""Device listing + status for dashboard."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.state import device_state
from app.services import device_service

router = APIRouter()


@router.get("/status")
def device_status():
    """Lightweight status used by the frontend dashboard (no auth for Phase A smoke)."""
    live = device_state.get_devices()
    return {"devices": live, "count": len(live)}


@router.get("/")
def list_devices(db: Session = Depends(get_db)):
    """DB-backed device list. Falls back to in-memory state if DB empty/errors."""
    try:
        rows = device_service.get_devices(db)
        devices = []
        for d in rows:
            devices.append(
                {
                    "id": str(getattr(d, "id", "")),
                    "hostname": getattr(d, "hostname", None),
                    "status": getattr(d, "status", None),
                    "ip": getattr(d, "ip", None),
                    "last_seen": getattr(d, "last_seen", None).isoformat()
                    if getattr(d, "last_seen", None)
                    else None,
                }
            )
        if devices:
            return {"devices": devices, "count": len(devices)}
    except Exception as exc:
        # DB not ready — still serve runtime state
        print(f"[devices] DB list failed: {exc}")

    live = device_state.get_devices()
    return {"devices": live, "count": len(live)}
