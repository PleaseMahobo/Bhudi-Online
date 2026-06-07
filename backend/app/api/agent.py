from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.command_service import get_pending_commands
from app.services.command_service import update_command_result

router = APIRouter()


@router.get("/agent/commands/{device_id}")
def fetch_commands(device_id: str, db: Session = Depends(get_db)):
    cmds = get_pending_commands(db, device_id)

    return [
        {
            "id": c.id,
            "command": c.command
        }
        for c in cmds
    ]

@router.post("/agent/result")
def submit_result(payload: dict, db: Session = Depends(get_db)):
    cmd_id = payload["command_id"]
    result = payload["result"]

    cmd = update_command_result(db, cmd_id, result)

    return {"status": "updated", "command_id": cmd_id}