from fastapi import APIRouter
from app.state.device_state import get_devices

router = APIRouter()

@router.get("/devices")
def list_devices():
    return {
        "devices": get_devices()
    }