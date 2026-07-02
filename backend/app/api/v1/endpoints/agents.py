from fastapi import APIRouter
from datetime import datetime
from app.services.device_service import upsert_device

router = APIRouter()

@router.post("/heartbeat")
def heartbeat(payload: dict):

    device_id = payload.get("device_id")

    device = {
        "device_id": device_id,
        "status": "online",
        "last_seen": datetime.utcnow().isoformat(),
        "cpu": payload.get("cpu"),
        "ram": payload.get("ram")
    }

    upsert_device(device)

    return {
        "status": "stored",
        "device_id": device_id
    }

    print("HEARTBEAT RECEIVED:", device)    