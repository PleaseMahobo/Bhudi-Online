from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from app.api.v1.router import api_router
from app.core.cors import setup_cors
from app.core.monitor import monitor_devices

# ====================== MAIN APP ======================
app = FastAPI(
    title="Bhudi RMM API",
    description="Enterprise Remote Monitoring & Management Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ====================== CORS ======================
setup_cors(app)

# ====================== ROUTERS ======================
app.include_router(api_router, prefix="/api/v1")

# ====================== STARTUP EVENTS ======================
@app.on_event("startup")
async def startup_event():
    """Start background tasks"""
    print("🚀 Bhudi RMM API starting...")
    asyncio.create_task(monitor_devices())

@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 Bhudi RMM API shutting down...")

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

# ====================== WebSocket Device Heartbeat ======================
from fastapi import WebSocket, WebSocketDisconnect
from typing import List
import asyncio

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections[:]:
            try:
                await connection.send_json(message)
            except:
                self.disconnect(connection)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast({
                "type": "live_update",
                "timestamp": asyncio.get_event_loop().time(),
                "message": data
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)