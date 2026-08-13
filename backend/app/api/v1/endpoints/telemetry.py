"""Telemetry routes — aliases onto metrics service."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from app.services.metrics_service import get_metrics

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.get("/devices/{device_id}")
def telemetry_device(
    device_id: str,
    minutes: int = Query(60, ge=5, le=10080),
) -> dict[str, Any]:
    points = get_metrics(device_id, minutes=minutes)
    return {"device_id": device_id, "count": len(points), "points": points}
