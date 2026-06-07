from fastapi import APIRouter
from app.api.routes import ws

api_router = APIRouter()

api_router.include_router(ws.router)