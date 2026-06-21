from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from app.core.monitor import monitor_devices
from app.core.cors import setup_cors

from app.api.routes_health import router as health_router
from app.api.routes_commands import router as commands_router
from app.api.routes_ws import router as ws_router
from app.api.routes_devices import router as devices_router
from app.api.routes_agent import router as agent_router

app = FastAPI(title="Bhudi RMM API")

app.include_router(agent_router)

# -----------------------------
# CORS (must be first)
# -----------------------------
app.add_middleware( 
    CORSMiddleware,
    allow_origins=["https://bhudi-online-production.up.railway.app"],                    # Change to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# -----------------------------
# ROUTES (API LAYER)
# -----------------------------
app.include_router(health_router)
app.include_router(commands_router)
app.include_router(ws_router)
app.include_router(devices_router)
app.include_router(agent_router)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(monitor_devices())

# ==================== WebSocket Support ====================

from fastapi import WebSocket, WebSocketDisconnect
from typing import List

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # You can process incoming messages here if needed
            await manager.broadcast({
                "type": "update",
                "message": data,
                "timestamp": "now"
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)