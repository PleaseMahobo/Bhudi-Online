from fastapi import APIRouter
from app.services.device_service import get_devices

router = APIRouter()

@router.get("/")
def list_devices():
    result = get_devices()
    return result.data