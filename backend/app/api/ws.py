from fastapi import APIRouter, WebSocket
from app.ws.manager import manager
from app.ws.agent_shell import shell
import json

router = APIRouter()

@router.websocket("/ws/agent/{device_id}")
async def agent_ws(websocket: WebSocket, device_id: str):
    await manager.connect(device_id, websocket)

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg["type"] == "command":
                await shell.execute(device_id, msg["command"])

    except Exception:
        manager.disconnect(device_id)