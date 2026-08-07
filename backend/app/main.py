from dotenv import load_dotenv
load_dotenv()

import asyncio
from typing import Dict

from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect

from app.api.v1.router import api_router
from app.core.bootstrap import initialize_database
from app.core.cors import setup_cors
from app.core.ws_manager import manager

app = FastAPI(
    title="Bhudi RMM API",
    description="Enterprise Remote Monitoring & Management Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

setup_cors(app)

try:
    from app.core.rate_limit import RateLimitMiddleware

    app.add_middleware(RateLimitMiddleware)
except Exception as e:
    print(f"[startup] rate limit middleware skipped: {e}")

# OpenTelemetry must instrument the app object before serving traffic
try:
    from app.core.telemetry import setup_tracing

    if setup_tracing(app):
        print("[startup] OpenTelemetry tracing enabled")
    else:
        print("[startup] OpenTelemetry tracing inactive")
except Exception as e:
    print(f"[startup] OpenTelemetry skipped: {e}")

# Optional schema router (ignore if service missing)
try:
    from app.api.schema_routes import router as schema_router
    app.include_router(schema_router)
except Exception as e:
    print(f"[startup] schema router skipped: {e}")

app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    print("Bhudi RMM API starting...")
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
        from app.core.telemetry import shutdown_tracing

        shutdown_tracing()
    except Exception:
        pass
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
    return {"status": "running", "service": "Bhudi RMM API", "version": "1.0.0"}


@app.get("/", tags=["Health"])
async def root():
    return {"message": "Bhudi RMM API is running", "docs": "/docs", "health": "/health"}


@app.get("/metrics", tags=["Observability"])
async def metrics():
    """Prometheus text exposition (best-effort if client installed)."""
    try:
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
    except Exception:
        return Response(
            content=(
                "# HELP bhudi_up 1 if process is up\n"
                "# TYPE bhudi_up gauge\n"
                "bhudi_up 1\n"
            ),
            media_type="text/plain; version=0.0.4",
        )


# Device heartbeat state (kept for backward compatibility)
device_heartbeats: Dict[str, dict] = {}


async def handle_heartbeat(device_id: str, data: dict):
    device_heartbeats[device_id] = {
        "status": "online",
        "timestamp": data.get("timestamp"),
        **data,
    }
    await manager.broadcast(
        {
            "type": "heartbeat",
            "device_id": device_id,
            "status": "online",
            "data": device_heartbeats[device_id],
        },
        channel="heartbeats",
    )
    # Also broadcast on general for legacy clients
    await manager.broadcast(
        {
            "type": "heartbeat",
            "device_id": device_id,
            "status": "online",
            "data": device_heartbeats[device_id],
        },
        channel="general",
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket, channel="general")
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "heartbeat" and data.get("device_id"):
                await handle_heartbeat(data["device_id"], data)
            elif data.get("type") == "subscribe":
                # Client can request channel switch via message
                channel = data.get("channel", "general")
                await manager.disconnect(websocket)
                await manager.connect(websocket, channel=channel)
                await websocket.send_json({"type": "subscribed", "channel": channel})
    except WebSocketDisconnect:
        await manager.disconnect(websocket)


@app.websocket("/ws/alerts")
async def alerts_websocket(websocket: WebSocket):
    """Dedicated real-time channel for Alert Engine events."""
    await manager.connect(websocket, channel="alerts")
    try:
        await websocket.send_json({
            "type": "connected",
            "channel": "alerts",
            "message": "Subscribed to live alerts",
        })
        while True:
            # Keep connection alive; ignore client messages or handle ping
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        await manager.disconnect(websocket)


@app.websocket("/ws/{device_id}")
async def device_ws(websocket: WebSocket, device_id: str):
    await manager.connect(websocket, channel="general")
    try:
        while True:
            data = await websocket.receive_json()
            data["device_id"] = device_id
            if data.get("type") == "heartbeat":
                await handle_heartbeat(device_id, data)
            else:
                await manager.broadcast(
                    {"type": "message", "device_id": device_id, "data": data},
                    channel="general",
                )
    except WebSocketDisconnect:
        await manager.disconnect(websocket)


print("Bhudi RMM API initialized")
