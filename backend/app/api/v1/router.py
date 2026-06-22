# app/api/v1/router.py

from fastapi import APIRouter
from app.api.v1.endpoints import health, devices, agents, auth

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])