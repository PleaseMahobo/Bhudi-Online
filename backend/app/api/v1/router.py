from fastapi import APIRouter

api_router.include_router(agent_commands.router)
from app.api.v1.endpoints import agent_commands
from app.api.v1.endpoints import commands
from app.api.v1.endpoints import (
    agents,
    auth,
    devices,
    health,
)

api_router = APIRouter()

api_router.include_router(
    commands.router
)
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

api_router.include_router(
    agent_commands.router,
)

api_router.include_router(
    agent_commands.router,
    )