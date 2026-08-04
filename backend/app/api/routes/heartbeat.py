from datetime import datetime
from app.core.database import SessionLocal
from app.models.command import Command


class CommandService:

    @staticmethod
    def create_command(device_id: int, command: str):

        db = SessionLocal()

        try:
            cmd = Command(
                device_id=device_id,
                command=command,
                status="pending"
            )

            db.add(cmd)
            db.commit()
            db.refresh(cmd)

            return cmd

        finally:
            db.close()


    @staticmethod
    def save_result(command_id: int, result: str, status: str = "done"):

        db = SessionLocal()

        try:
            cmd = db.query(Command).filter(Command.id == command_id).first()

            if cmd:
                cmd.result = result
                cmd.status = status
                cmd.executed_at = datetime.utcnow()

                db.commit()

        finally:
            db.close()