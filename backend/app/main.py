from dotenv import load_dotenv
load_dotenv()

import asyncio
from typing import Dict, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from app.api.v1.router import api_router
from app.core.bootstrap import initialize_database
from app.core.cors import setup_cors

app = FastAPI(
    title="Bhudi RMM API",
    description="Enterprise Remote Monitoring & Management Platform",
    version="1.0.0-phase-ab",
    docs_url="/docs",
    redoc_url="/redoc",
)

setup_cors(app)

# Optional schema router (ignore if service missing)
try:
    from app.api.schema_routes import router as schema_router
    app.include_router(schema_router)
except Exception as e:
    print(f"[startup] schema router skipped: {e}")

app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    print("Bhudi RMM API starting (Phase A+B)...")
    bootstrap_result = initialize_database()
    print(f"[startup] bootstrap: {bootstrap_result}")
    try:
        from app.core.monitor import monitor_devices
        asyncio.create_task(monitor_devices())
    except Exception as e:
        print(f"[startup] monitor_devices skipped: {e}")
    import os
    if os.getenv("BHUDI_DISABLE_WORKERS", "0") == "1":
        print("[startup] workers disabled (BHUDI_DISABLE_WORKERS=1)")
    else:
        try:
            from app.workers.command_dispatcher import dispatcher
            dispatcher.start()
        except Exception as e:
            print(f"[startup] command_dispatcher skipped: {e}")
        try:
            from app.workers.executor_worker import executor_worker
            executor_worker.start()
        except Exception as e:
            print(f"[startup] executor_worker skipped: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    print("Bhudi RMM API shutting down...")
    try:
        from app.workers.command_dispatcher import dispatcher
        dispatcher.stop()
    except Exception:
        pass
    try:
        from app.workers.executor_worker import executor_worker
        executor_worker.stop()
    except Exception:
        pass


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "running", "service": "Bhudi RMM API", "version": "1.0.0-phase-ab"}


@app.get("/", tags=["Health"])
async def root():
    return {"message": "Bhudi RMM API is running", "docs": "/docs", "health": "/health"}


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
            "timestamp": data.get("timestamp"),
            **data,
        }
        await self.broadcast(
            {"type": "heartbeat", "device_id": device_id, "status": "online", "data": self.device_heartbeats[device_id]}
        )


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


@app.websocket("/ws/{device_id}")
async def device_ws(websocket: WebSocket, device_id: str):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            data["device_id"] = device_id
            if data.get("type") == "heartbeat":
                await manager.handle_heartbeat(device_id, data)
            else:
                await manager.broadcast({"type": "message", "device_id": device_id, "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


print("Bhudi RMM API initialized (Phase A+B)")
