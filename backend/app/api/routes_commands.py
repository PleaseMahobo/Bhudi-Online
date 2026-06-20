from fastapi import APIRouter
from app.models.command import CommandRequest

router = APIRouter()

@router.post("/commands")
def send_command(payload: CommandRequest):
    return {
        "status": "received",
        "device_id": payload.device_id,
        "command": payload.command
    }