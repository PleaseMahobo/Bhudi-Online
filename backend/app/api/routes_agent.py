from fastapi import APIRouter
from app.state.command_queue import get_pending_commands
from pydantic import BaseModel
from app.state.command_queue import complete_command

router = APIRouter()

class CommandResult(BaseModel):
    command_id: str
    result: str


@router.get("/agent/{device_id}/commands")
def agent_commands(device_id: str):

    complete_command(
        payload.command_id,
        payload.result
    )

    return {"status": "completed"}