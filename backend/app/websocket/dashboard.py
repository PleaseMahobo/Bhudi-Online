from fastapi import APIRouter
from fastapi import WebSocket
from fastapi import WebSocketDisconnect

from app.core.connection_manager import manager

router = APIRouter()


@router.websocket("/ws/dashboard")
async def dashboard_ws(
    websocket: WebSocket
):

    await manager.connect_dashboard(websocket)

    try:

        while True:

            data = await websocket.receive_json()

            if data["type"] == "execute":

                await manager.send_to_agent(
                    data["device_id"],
                    {
                        "type": "execute",
                        "command": data["command"]
                    }
                )

    except WebSocketDisconnect:

        manager.disconnect_dashboard(websocket)