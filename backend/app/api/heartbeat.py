from fastapi import APIRouter
from app.services.device_service import DeviceService
from app.schemas.device import HeartbeatIn

router = APIRouter(prefix="/api", tags=["heartbeat"])


@router.post("/heartbeat")
def heartbeat(payload: HeartbeatIn):
    return DeviceService.update_heartbeat(payload.device_id)