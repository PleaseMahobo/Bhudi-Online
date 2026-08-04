from fastapi import APIRouter
from pydantic import BaseModel
from app.services.command_service import CommandService

router = APIRouter()


class CommandCreate(BaseModel):
    device_id: int
    command: str


@router.post("/")
def create_command(payload: CommandCreate):

    cmd = CommandService.create_command(
        device_id=payload.device_id,
        command=payload.command
    )

    return {"status": "queued", "command_id": cmd.id}