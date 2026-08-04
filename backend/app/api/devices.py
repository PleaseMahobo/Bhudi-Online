from fastapi import APIRouter
from app.schemas.device import DeviceRegister
from app.services.device_service import DeviceService

router = APIRouter()

@router.post("/register")
def register_device(device: DeviceRegister):
    return DeviceService.register(device)