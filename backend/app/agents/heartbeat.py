from fastapi import APIRouter
from datetime import datetime
from app.websocket.event_stream import EventStream

router = APIRouter()

# fake in-memory store (replace with DB later)
AGENT_STATE = {}

@router.post("/agent/heartbeat")
async def heartbeat(payload: dict):

    agent_id = payload["agent_id"]

    AGENT_STATE[agent_id] = {
        "last_seen": datetime.utcnow(),
        "status": payload.get("status", "online"),
        "cpu": payload.get("cpu"),
        "ram": payload.get("ram"),
        "disk": payload.get("disk"),
    }

    event = {
        "type": "heartbeat",
        "device_id": agent_id,
        "severity": "low",
        "payload": AGENT_STATE[agent_id]
    }

    await EventStream.publish(event)

    return {"status": "ok"}