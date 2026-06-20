from fastapi import APIRouter

from app.api import ws
from app.api import heartbeat
from app.api import devices
from app.api import commands
from app.api import auth

api_router = APIRouter(prefix="/api")

api_router.include_router(ws.router)
api_router.include_router(heartbeat.router)
api_router.include_router(devices.router)
api_router.include_router(commands.router)
api_router.include_router(auth.router)