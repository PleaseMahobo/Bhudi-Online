from fastapi import APIRouter
from fastapi import WebSocket
from fastapi import WebSocketDisconnect

from app.core.connection_manager import manager

router = APIRouter()


@router.websocket("/ws/agent/{device_id}")
async def agent_ws(
    websocket: WebSocket,
    device_id: str
):
    await manager.connect_agent(
        device_id,
        websocket
    )

    try:

        await manager.broadcast({
            "type": "agent_connected",
            "device_id": device_id
        })

        while True:

            data = await websocket.receive_json()

            await manager.broadcast({
                "type": "agent_message",
                "device_id": device_id,
                "data": data
            })

    except WebSocketDisconnect:

        manager.disconnect_agent(device_id)

        await manager.broadcast({
            "type": "agent_disconnected",
            "device_id": device_id
        })