from fastapi import APIRouter

from app.api.v1.endpoints import (
    agents,
    auth,
    devices,
    health,
)

api_router = APIRouter()

api_router.include_router(
    health.router,
    prefix="/health",
    tags=["health"],
)

api_router.include_router(
    devices.router,
    prefix="/devices",
    tags=["devices"],
)

api_router.include_router(
    agents.router,
    prefix="/agents",
    tags=["agents"],
)

api_router.include_router(
    auth.router,
)