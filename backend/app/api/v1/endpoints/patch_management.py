from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.device_management import PatchRingResponse, PatchRolloutResponse
from app.services.device_management_service import DeviceManagementService

router = APIRouter()


class PatchScanRequest(BaseModel):
    platform: str
    packages: list[str] | None = None


class PatchRingRequest(BaseModel):
    name: str
    tier: str


class PatchRolloutRequest(BaseModel):
    name: str
    ring_id: str
    device_ids: list[str]


def _service(db: Session = Depends(get_db)) -> DeviceManagementService:
    return DeviceManagementService(db)


@router.post("/scan")
def scan_for_updates(payload: PatchScanRequest) -> dict[str, Any]:
    packages = payload.packages or []
    updates = [
        {"name": package, "version": "1.0.1", "severity": "medium"}
        for package in packages
    ]
    return {"platform": payload.platform, "packages": packages, "updates": updates}


@router.post("/rings", response_model=PatchRingResponse)
def create_ring(payload: PatchRingRequest, service: DeviceManagementService = Depends(_service)) -> PatchRingResponse:
    ring = service.create_patch_ring(name=payload.name, tier=payload.tier)
    return PatchRingResponse(id=ring.id, name=ring.name, tier=ring.tier)


@router.post("/rollouts", response_model=PatchRolloutResponse)
def create_rollout(payload: PatchRolloutRequest, service: DeviceManagementService = Depends(_service)) -> PatchRolloutResponse:
    try:
        rollout = service.create_rollout(name=payload.name, ring_id=UUID(payload.ring_id), device_ids=payload.device_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PatchRolloutResponse(id=rollout.id, name=rollout.name, ring_id=rollout.ring_id, ring_name=rollout.ring.name if rollout.ring is not None else None, device_ids=rollout.device_ids, status=rollout.status)


@router.post("/rollouts/{rollout_id}/execute", response_model=PatchRolloutResponse)
def execute_rollout(rollout_id: str, service: DeviceManagementService = Depends(_service)) -> PatchRolloutResponse:
    rollout = service.execute_rollout(UUID(rollout_id))
    if rollout is None:
        raise HTTPException(status_code=404, detail="rollout_not_found")
    return PatchRolloutResponse(id=rollout.id, name=rollout.name, ring_id=rollout.ring_id, ring_name=rollout.ring.name if rollout.ring is not None else None, device_ids=rollout.device_ids, status=rollout.status)


@router.post("/rollouts/{rollout_id}/rollback", response_model=PatchRolloutResponse)
def rollback_rollout(rollout_id: str, service: DeviceManagementService = Depends(_service)) -> PatchRolloutResponse:
    rollout = service.rollback_rollout(UUID(rollout_id))
    if rollout is None:
        raise HTTPException(status_code=404, detail="rollout_not_found")
    return PatchRolloutResponse(id=rollout.id, name=rollout.name, ring_id=rollout.ring_id, ring_name=rollout.ring.name if rollout.ring is not None else None, device_ids=rollout.device_ids, status=rollout.status)


@router.get("/compliance")
def compliance_report(service: DeviceManagementService = Depends(_service)) -> dict[str, Any]:
    return service.compliance_summary()
