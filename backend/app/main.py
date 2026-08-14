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

try:
    from app.middleware.prometheus_middleware import PrometheusMiddleware
    app.add_middleware(PrometheusMiddleware)
    print("[startup] Prometheus HTTP metrics middleware enabled")
except Exception as e:
    print(f"[startup] Prometheus middleware skipped: {e}")

try:
    from app.core.telemetry import setup_tracing
    if setup_tracing(app):
        print("[startup] OpenTelemetry tracing enabled")
    else:
        print("[startup] OpenTelemetry tracing inactive")
except Exception as e:
    print(f"[startup] OpenTelemetry skipped: {e}")

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
        try:
            from app.workers.itsm_sla_worker import itsm_sla_worker
            itsm_sla_worker.start()
            print("[startup] ITSM SLA escalation worker started")
        except Exception as e:
            print(f"[startup] itsm_sla_worker skipped: {e}")


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
    try:
        from app.workers.itsm_sla_worker import itsm_sla_worker
        itsm_sla_worker.stop()
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
    try:
        from app.api.v1.endpoints import agent_runtime
        from app.core.prometheus_metrics import set_agents_online
        agents = getattr(agent_runtime, "_agents", {}) or {}
        online = sum(1 for a in agents.values() if (a.get("status") or "").lower() == "online")
        set_agents_online(online)
    except Exception:
        pass
    try:
        from app.core.prometheus_metrics import render_metrics
        body, ctype = render_metrics()
        return Response(content=body, media_type=ctype)
    except Exception:
        return Response(content="# HELP bhudi_up 1 if process is up\n# TYPE bhudi_up gauge\nbhudi_up 1\n", media_type="text/plain; version=0.0.4")


device_heartbeats: Dict[str, dict] = {}


async def handle_heartbeat(device_id: str, data: dict):
    device_heartbeats[device_id] = {"status": "online", "timestamp": data.get("timestamp"), **data}
    await manager.broadcast({"type": "heartbeat", "device_id": device_id, "data": device_heartbeats[device_id]})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "heartbeat":
                device_id = str(data.get("device_id") or "unknown")
                await handle_heartbeat(device_id, data)
            else:
                await manager.broadcast(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast({"type": "alert", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.websocket("/ws/{device_id}")
async def websocket_device(websocket: WebSocket, device_id: str):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast({"type": "device", "device_id": device_id, "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


print("Bhudi RMM API initialized")
