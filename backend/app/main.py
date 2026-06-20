from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

from app.core.cors import setup_cors
from app.api.routes_health import router as health_router
from app.api.routes_commands import router as commands_router
from app.api.routes_ws import router as ws_router
from app.api import routes_health, routes_devices, routes_commands, routes_ws

app = FastAPI(title="Bhudi RMM API")

setup_cors(app)

app.include_router(health_router)
app.include_router(commands_router)
app.include_router(ws_router)
# -----------------------------
# CORS (frontend connection)
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://bhudi.online",
        "https://www.bhudi.online",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# HEALTH CHECK
# -----------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "Bhudi RMM API"
    }

# -----------------------------
# ROOT ROUTE
# -----------------------------
@app.get("/")
def root():
    return {
        "status": "running",
        "service": "Bhudi RMM API"
    }
# -----------------------------
# ACTIVE DEVICE CONNECTIONS
# -----------------------------
active_connections = {}

# -----------------------------
# WEBSOCKET (DEVICE AGENT)
# -----------------------------
@app.websocket("/ws/agent/{device_id}")
async def agent_ws(websocket: WebSocket, device_id: str):
    await websocket.accept()
    active_connections[device_id] = websocket

    try:
        while True:
            data = await websocket.receive_text()

            # broadcast to all connected clients (dashboard view)
            for ws in list(active_connections.values()):
                await ws.send_text(f"{device_id}: {data}")

    except WebSocketDisconnect:
        active_connections.pop(device_id, None)