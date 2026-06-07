from fastapi import WebSocket, APIRouter
from app.ws.agent_shell import agent_manager
import json

router = APIRouter()

connected_clients = []

@router.websocket("/ws/dashboard")
async def dashboard_socket(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            # forward command to agent layer
            if msg["type"] == "command":
                await agent_manager.send_command(
                    msg["device_id"],
                    {
                        "command": msg["command"]
                    }
                )

    except Exception:
        connected_clients.remove(websocket)