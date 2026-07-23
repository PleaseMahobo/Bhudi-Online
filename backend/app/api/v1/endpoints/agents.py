from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter()


class CommandRequest(BaseModel):
    command: str


class CommandResponse(BaseModel):
    id: str
    status: str
    command: str
    device_id: str


@router.post("/{device_id}/commands", response_model=CommandResponse)
async def send_command(device_id: str, request: CommandRequest) -> CommandResponse:
    return CommandResponse(
        id=str(uuid4()),
        status="queued",
        command=request.command,
        device_id=device_id,
    )