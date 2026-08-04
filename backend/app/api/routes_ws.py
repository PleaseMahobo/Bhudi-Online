from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.state.device_state import register_device, heartbeat

router = APIRouter()

active_connections = {}

@router.websocket("/ws/agent/{device_id}")
async def agent_ws(websocket: WebSocket, device_id: str):
    await websocket.accept()

    register_device(device_id)
    active_connections[device_id] = websocket

    try:
        while True:
            data = await websocket.receive_text()

            heartbeat(device_id)

            for ws in list(active_connections.values()):
                await ws.send_json({
                    "device_id": device_id,
                    "message": data,
                    "status": "online"
                })

    except WebSocketDisconnect:
        active_connections.pop(device_id, None)