from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from app.api.v1.router import api_router
from app.core.cors import setup_cors
from app.core.monitor import monitor_devices
from app.api.schema_routes import router as schema_router
from app.core.database import SessionLocal
from app.db.seeds.rbac_seed import seed_rbac
from app.workers.command_dispatcher import dispatcher
from app.workers.executor_worker import executor_worker

# ====================== MAIN APP ======================
app = FastAPI(
    title="Bhudi RMM API",
    description="Enterprise Remote Monitoring & Management Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.include_router(schema_router)

# ====================== CORS ======================
setup_cors(app)

# ====================== ROUTERS ======================
app.include_router(
    api_router, 
    prefix="/api/v1",
)

# ====================== STARTUP EVENTS ======================
@app.on_event("startup")
async def startup_event():
    """Start background tasks"""
    print("🚀 Bhudi RMM API starting...")
    asyncio.create_task(monitor_devices())
    dispatcher.start()
    executor_worker.start()

@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 Bhudi RMM API shutting down...")
    dispatcher.stop()
    executor_worker.stop()

# ====================== HEALTH CHECK ======================
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "running",
        "service": "Bhudi RMM API",
        "version": "1.0.0"
    }

# ====================== ROOT ======================
@app.get("/", tags=["Health"])
async def root():
    return {
        "message": "Bhudi RMM API is running",
        "docs": "/docs",
        "health": "/health"
    }

print("✅ Bhudi RMM API initialized successfully")

# ====================== WebSocket Heartbeat ======================
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.device_heartbeats: Dict[str, dict] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections[:]:
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

    async def handle_heartbeat(self, device_id: str, data: dict):
        self.device_heartbeats[device_id] = {
            "status": "online",
            "last_heartbeat": asyncio.get_event_loop().time(),
            "timestamp": data.get("timestamp"),
            **data
        }
        await self.broadcast({
            "type": "heartbeat",
            "device_id": device_id,
            "status": "online",
            "data": self.device_heartbeats[device_id]
        })

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "heartbeat" and data.get("device_id"):
                await manager.handle_heartbeat(data["device_id"], data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)