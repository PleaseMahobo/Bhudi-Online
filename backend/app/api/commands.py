from fastapi import APIRouter
from app.schemas.command import CommandCreate, CommandResult

router = APIRouter(prefix="/commands", tags=["commands"])


@router.post("/send", response_model=CommandResult)
def send_command(cmd: CommandCreate):

    return CommandResult(
        command_id="cmd_123",
        device_id=cmd.device_id,
        status="queued",
        output=None
    )