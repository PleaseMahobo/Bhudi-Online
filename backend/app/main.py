from fastapi import FastAPI

from app.core.cors import setup_cors
from app.api.routes_health import router as health_router
from app.api.routes_commands import router as commands_router
from app.api.routes_ws import router as ws_router

app = FastAPI(title="Bhudi RMM API")

# CORS (ONLY ONCE)
setup_cors(app)

# ROUTERS (ONLY SOURCE OF ENDPOINTS)
app.include_router(health_router)
app.include_router(commands_router)
app.include_router(ws_router)