from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websocket.manager import ConnectionManager
from app.core.database import SessionLocal
from app.models.command import Command

router = APIRouter()
manager = ConnectionManager()


@router.websocket("/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: int):

    await manager.connect(device_id, websocket)

    db = SessionLocal()

    try:
        while True:

            data = await websocket.receive_json()

            # CASE 1: heartbeat
            if data.get("type") == "heartbeat":
                device = data.get("device")

                # update device instantly
                # (lightweight inline update)
                from app.models.device import Device

                d = db.query(Device).filter(Device.id == device_id).first()

                if d:
                    d.status = "online"
                    from datetime import datetime
                    d.last_seen = datetime.utcnow()
                    db.commit()

            # CASE 2: command result
            elif data.get("type") == "result":

                cmd_id = data.get("command_id")
                result = data.get("result")

                cmd = db.query(Command).filter(Command.id == cmd_id).first()

                if cmd:
                    cmd.result = result
                    cmd.status = "done"
                    db.commit()

    except WebSocketDisconnect:
        manager.disconnect(device_id)

        # mark offline immediately
        from datetime import datetime
        from app.models.device import Device

        d = db.query(Device).filter(Device.id == device_id).first()

        if d:
            d.status = "offline"
            db.commit()

    finally:
        db.close()