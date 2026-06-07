from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websocket.manager import ConnectionManager

router = APIRouter()
manager = ConnectionManager()

@router.websocket("/ws/soc")
async def soc_stream(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            # optional: receive messages from frontend
            data = await websocket.receive_json()

            await manager.broadcast({
                "type": "client_event",
                "payload": data
            })

    except WebSocketDisconnect:
        manager.disconnect(websocket)