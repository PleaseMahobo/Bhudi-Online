from app.websocket.manager import ConnectionManager
from app.core.database import SessionLocal
from app.models.command import Command

manager = ConnectionManager()


class WSCommandService:

    @staticmethod
    async def push_command(device_id: int, command_id: int):

        db = SessionLocal()

        try:
            cmd = db.query(Command).filter(Command.id == command_id).first()

            if not cmd:
                return

            payload = {
                "type": "command",
                "command_id": cmd.id,
                "command": cmd.command
            }

            await manager.send_command(device_id, payload)

            cmd.status = "running"
            db.commit()

        finally:
            db.close()