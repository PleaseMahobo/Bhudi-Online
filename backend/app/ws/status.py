from fastapi import WebSocket, APIRouter
from app.core.database import SessionLocal
from app.models.device import Device
import asyncio

router = APIRouter()


@router.websocket("/ws/status")
async def status_ws(websocket: WebSocket):
    await websocket.accept()

    while True:
        db = SessionLocal()
        devices = db.query(Device).all()

        data = [
            {
                "id": d.id,
                "status": d.status,
                "last_seen": str(d.last_seen)
            }
            for d in devices
        ]

        await websocket.send_json(data)

        db.close()
        await asyncio.sleep(5)