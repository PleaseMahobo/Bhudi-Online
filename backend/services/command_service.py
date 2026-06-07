from sqlalchemy.orm import Session
from app.models.command import Command
from datetime import datetime
import uuid


def create_command(db: Session, device_id: str, command: str):
    cmd = Command(
        id=str(uuid.uuid4()),
        device_id=device_id,
        command=command,
        status="pending"
    )

    db.add(cmd)
    db.commit()
    db.refresh(cmd)
    return cmd


def get_pending_commands(db: Session, device_id: str):
    return db.query(Command).filter(
        Command.device_id == device_id,
        Command.status == "pending"
    ).all()


def update_command_result(db: Session, command_id: str, result: str):
    cmd = db.query(Command).filter(Command.id == command_id).first()

    if not cmd:
        return None

    cmd.result = result
    cmd.status = "done"
    cmd.executed_at = datetime.utcnow()

    db.commit()
    db.refresh(cmd)
    return cmd