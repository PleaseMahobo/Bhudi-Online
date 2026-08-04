from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.shell_manager import shell_manager
from app.core.ws_manager import manager

router = APIRouter()


# =========================================
# AGENT WEBSOCKET
# =========================================
@router.websocket("/agent/{device_id}")
async def agent_socket(websocket: WebSocket, device_id: str):

    await shell_manager.connect_agent(device_id, websocket)

    try:

        while True:

            data = await websocket.receive_json()

            # forward output to dashboard
            await manager.broadcast({
                "type": "shell_output",
                "device_id": device_id,
                "output": data.get("output", "")
            })

    except WebSocketDisconnect:
        shell_manager.disconnect_agent(device_id)


# =========================================
# DASHBOARD SEND COMMAND
# =========================================
@router.post("/send/{device_id}")
async def send_shell_command(device_id: str, payload: dict):

    command = payload.get("command")

    success = await shell_manager.send_command(
        device_id,
        command
    )

    return {
        "success": success
    }