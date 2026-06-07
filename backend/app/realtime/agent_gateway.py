from fastapi import WebSocket, WebSocketDisconnect
from app.core.device_security import DeviceSecurity

active_agents = {}
security = DeviceSecurity()


async def agent_socket(websocket: WebSocket, device_id: str, api_key: str):

    # 🔐 AUTH STEP (CRITICAL)
    if not security.verify_device(device_id, api_key):
        await websocket.close(code=1008)
        return

    await websocket.accept()
    active_agents[device_id] = websocket

    try:
        while True:
            data = await websocket.receive_json()

            # MARK DEVICE AS ACTIVE (heartbeat inside WS)
            if data.get("type") == "heartbeat":
                print(f"[SECURE HEARTBEAT] {device_id}")

            # HANDLE COMMAND RESULT
            if data.get("type") == "result":
                print(f"[SIGNED RESULT] {device_id}: {data}")

    except WebSocketDisconnect:
        active_agents.pop(device_id, None)


def send_command_to_agent(device_id: str, payload: dict):
    import asyncio

    ws = active_agents.get(device_id)

    if ws:
        asyncio.create_task(ws.send_json(payload))