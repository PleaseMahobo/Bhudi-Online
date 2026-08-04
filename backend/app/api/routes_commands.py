from fastapi import APIRouter
from app.models.command import CommandRequest
from app.state.command_queue import queue_command

router = APIRouter()

@router.post("/commands")
def send_command(payload: CommandRequest):

    command = queue_command(
        str(payload.device_id),
        payload.command
    )

    return {
        "status": "queued",
        "command": command
    }