try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
except ModuleNotFoundError as exc:
    raise RuntimeError(
        "FastAPI is required to run this application. Install it with 'pip install fastapi' "
        "and activate the correct Python environment."
    ) from exc

app = FastAPI()

active_connections = {}

@app.websocket("/ws/agent/{device_id}")
async def agent_ws(websocket: WebSocket, device_id: str):
    await websocket.accept()
    active_connections[device_id] = websocket

    try:
        while True:
            data = await websocket.receive_text()

            # broadcast to dashboard (simple version)
            for ws in active_connections.values():
                await ws.send_text(f"{device_id}: {data}")

    except WebSocketDisconnect:
        active_connections.pop(device_id, None)