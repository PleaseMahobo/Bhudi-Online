from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

active_connections = {}

@router.websocket("/ws/agent/{device_id}")
async def agent_ws(websocket: WebSocket, device_id: str):
    await websocket.accept()
    active_connections[device_id] = websocket

    try:
        while True:
            data = await websocket.receive_text()

            for ws in active_connections.values():
                await ws.send_text(f"{device_id}: {data}")

    except WebSocketDisconnect:
        active_connections.pop(device_id, None)