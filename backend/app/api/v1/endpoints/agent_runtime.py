"""
Practical agent runtime API for Phase A/B testing.

Endpoints (under /api/v1):
  POST /runtime/enroll
  POST /runtime/heartbeat
  GET  /runtime/agents
  POST /runtime/agents/{agent_id}/commands
  GET  /runtime/agents/{agent_id}/commands/pending
  POST /runtime/agents/{agent_id}/commands/{command_id}/result

This store is process-local so the agent loop works even when Postgres
models/services are partially incomplete. Production will persist to DB.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.state import device_state

router = APIRouter(prefix="/runtime")

# --------------- in-memory stores ---------------
_agents: dict[str, dict[str, Any]] = {}
_commands: dict[str, list[dict[str, Any]]] = {}  # agent_id -> commands


class EnrollRequest(BaseModel):
    hostname: str
    agent_version: str = "1.0.0"
    platform: str | None = None
    enrollment_secret: str | None = None


class EnrollResponse(BaseModel):
    agent_id: str
    agent_token: str
    heartbeat_interval: int = 30
    poll_interval: int = 5


class HeartbeatRequest(BaseModel):
    agent_id: str
    agent_token: str
    status: str = "online"
    cpu_percent: float | None = None
    memory_percent: float | None = None
    disk_percent: float | None = None
    ip_address: str | None = None
    hostname: str | None = None


class CommandCreate(BaseModel):
    command: str
    shell: bool = True


class CommandResult(BaseModel):
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""


@router.post("/enroll", response_model=EnrollResponse)
def enroll(req: EnrollRequest):
    agent_id = str(uuid.uuid4())
    token = str(uuid.uuid4())
    _agents[agent_id] = {
        "agent_id": agent_id,
        "agent_token": token,
        "hostname": req.hostname,
        "agent_version": req.agent_version,
        "platform": req.platform,
        "status": "online",
        "registered_at": datetime.utcnow().isoformat() + "Z",
        "last_seen": datetime.utcnow().isoformat() + "Z",
        "cpu_percent": None,
        "memory_percent": None,
        "disk_percent": None,
    }
    _commands[agent_id] = []
    device_state.register_device(agent_id)
    device_state.devices[agent_id]["hostname"] = req.hostname
    return EnrollResponse(agent_id=agent_id, agent_token=token)


@router.post("/heartbeat")
def heartbeat(req: HeartbeatRequest):
    agent = _agents.get(req.agent_id)
    if not agent or agent["agent_token"] != req.agent_token:
        raise HTTPException(status_code=401, detail="Invalid agent credentials")

    agent["status"] = req.status
    agent["last_seen"] = datetime.utcnow().isoformat() + "Z"
    if req.cpu_percent is not None:
        agent["cpu_percent"] = req.cpu_percent
    if req.memory_percent is not None:
        agent["memory_percent"] = req.memory_percent
    if req.disk_percent is not None:
        agent["disk_percent"] = req.disk_percent
    if req.ip_address:
        agent["ip_address"] = req.ip_address
    if req.hostname:
        agent["hostname"] = req.hostname

    device_state.heartbeat(req.agent_id)
    if req.agent_id in device_state.devices:
        device_state.devices[req.agent_id].update(
            {
                "hostname": agent.get("hostname"),
                "cpu_percent": agent.get("cpu_percent"),
                "memory_percent": agent.get("memory_percent"),
                "disk_percent": agent.get("disk_percent"),
                "status": "online",
            }
        )

    pending = [
        c
        for c in _commands.get(req.agent_id, [])
        if c["status"] in ("pending", "dispatched")
    ]
    return {
        "status": "ok",
        "server_time": datetime.utcnow().isoformat() + "Z",
        "pending_commands": len(pending),
        "poll_interval": 5,
        "heartbeat_interval": 30,
    }


@router.get("/agents")
def list_runtime_agents():
    return {"agents": list(_agents.values()), "count": len(_agents)}


@router.post("/agents/{agent_id}/commands")
def queue_command(agent_id: str, body: CommandCreate):
    if agent_id not in _agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    cmd_id = str(uuid.uuid4())
    item = {
        "command_id": cmd_id,
        "command": body.command,
        "shell": body.shell,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "result": None,
    }
    _commands.setdefault(agent_id, []).append(item)
    device_state.add_command(agent_id, body.command)
    return {"accepted": True, "command_id": cmd_id, "status": "pending"}


@router.get("/agents/{agent_id}/commands/pending")
def pending_commands(agent_id: str, agent_token: str):
    agent = _agents.get(agent_id)
    if not agent or agent["agent_token"] != agent_token:
        raise HTTPException(status_code=401, detail="Invalid agent credentials")
    out = []
    for c in _commands.get(agent_id, []):
        if c["status"] in ("pending", "dispatched"):
            c["status"] = "dispatched"
            out.append(
                {
                    "command_id": c["command_id"],
                    "command": c["command"],
                    "shell": c.get("shell", True),
                }
            )
    return {"commands": out}


@router.post("/agents/{agent_id}/commands/{command_id}/result")
def post_result(agent_id: str, command_id: str, body: CommandResult, agent_token: str):
    agent = _agents.get(agent_id)
    if not agent or agent["agent_token"] != agent_token:
        raise HTTPException(status_code=401, detail="Invalid agent credentials")
    for c in _commands.get(agent_id, []):
        if c["command_id"] == command_id:
            c["status"] = "completed" if body.exit_code == 0 else "failed"
            c["result"] = body.model_dump()
            c["finished_at"] = datetime.utcnow().isoformat() + "Z"
            return {"status": "recorded", "command_id": command_id}
    raise HTTPException(status_code=404, detail="Command not found")


@router.get("/agents/{agent_id}/commands/{command_id}")
def get_command(agent_id: str, command_id: str):
    for c in _commands.get(agent_id, []):
        if c["command_id"] == command_id:
            return c
    raise HTTPException(status_code=404, detail="Command not found")
