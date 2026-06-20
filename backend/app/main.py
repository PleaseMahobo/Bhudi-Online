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
setup_cors(app)

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