"""Device metrics history API for dashboard charts."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from app.services.metrics_service import get_metrics, latest_for_agents

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/devices/{device_id}")
def device_metrics_history(
    device_id: str,
    minutes: int = Query(60, ge=5, le=10080),
    limit: int = Query(500, ge=10, le=5000),
) -> dict[str, Any]:
    points = get_metrics(device_id, minutes=minutes, limit=limit)
    latest = points[-1] if points else None
    return {
        "device_id": device_id,
        "minutes": minutes,
        "count": len(points),
        "latest": latest,
        "points": points,
    }


@router.get("/latest")
def metrics_latest() -> dict[str, Any]:
    return {"latest": latest_for_agents()}
