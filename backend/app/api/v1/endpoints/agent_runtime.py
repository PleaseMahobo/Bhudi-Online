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
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
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


class CommandAck(BaseModel):
    status: str = "running"


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
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "cpu_percent": None,
        "memory_percent": None,
        "disk_percent": None,
        "ip_address": None,
        "enrollment_secret": req.enrollment_secret,
        "commands_completed": 0,
        "commands_failed": 0,
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
    agent["last_seen"] = datetime.now(timezone.utc).isoformat()
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
        "server_time": datetime.now(timezone.utc).isoformat(),
        "pending_commands": len(pending),
        "poll_interval": 5,
        "heartbeat_interval": 30,
    }


@router.get("/agents")
def list_runtime_agents():
    return {"agents": list(_agents.values()), "count": len(_agents)}


def _translate_package_command(platform_name: str, command: str) -> str | None:
    normalized = command.strip().lower()
    if not normalized:
        return None
    if platform_name.startswith("darwin") or platform_name == "macos":
        if normalized.startswith("install "):
            package = command.strip().split(maxsplit=1)[1]
            return f"brew update && brew install {package}"
        if normalized.startswith("update "):
            package = command.strip().split(maxsplit=1)[1]
            return f"brew update && brew upgrade {package}"
        if normalized.startswith("uninstall "):
            package = command.strip().split(maxsplit=1)[1]
            return f"brew uninstall {package}"
    if platform_name.startswith("linux") or platform_name == "linux":
        if normalized.startswith("install "):
            package = command.strip().split(maxsplit=1)[1]
            return f"sudo apt-get update && sudo apt-get install -y {package}"
        if normalized.startswith("update "):
            package = command.strip().split(maxsplit=1)[1]
            return f"sudo apt-get update && sudo apt-get install -y {package}"
        if normalized.startswith("uninstall "):
            package = command.strip().split(maxsplit=1)[1]
            return f"sudo apt-get remove -y {package}"
    return None


def _execution_profile(agent: dict[str, Any], command: str) -> dict[str, Any]:
    platform_name = str(agent.get("platform") or "unknown")
    if platform_name.startswith("darwin") or platform_name == "macos":
        default_shell = "/bin/zsh"
        package_manager = "brew"
    elif platform_name.startswith("linux") or platform_name == "linux":
        default_shell = "/bin/bash"
        package_manager = "apt"
    else:
        default_shell = "/bin/sh"
        package_manager = "unknown"

    normalized = command.strip().lower()
    if normalized.startswith("install ") or normalized.startswith("upgrade ") or normalized.startswith("apt ") or normalized.startswith("brew ") or normalized.startswith("update ") or normalized.startswith("uninstall "):
        task_kind = "package-management"
    else:
        task_kind = "shell"

    translated_command = _translate_package_command(platform_name, command)
    return {
        "default_shell": default_shell,
        "package_manager": package_manager,
        "task_kind": task_kind,
        "translated_command": translated_command or command,
    }


@router.post("/agents/{agent_id}/commands")
def queue_command(agent_id: str, body: CommandCreate):
    if agent_id not in _agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent = _agents[agent_id]
    cmd_id = str(uuid.uuid4())
    item = {
        "command_id": cmd_id,
        "command": body.command,
        "shell": body.shell,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "result": None,
        "retry_count": 0,
        "acknowledged": False,
        "execution_profile": _execution_profile(agent, body.command),
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
            c["status"] = "completed" if body.exit_code == 0 else "pending"
            c["result"] = body.model_dump()
            c["finished_at"] = datetime.now(timezone.utc).isoformat()
            if body.exit_code == 0:
                c["retry_count"] = c.get("retry_count", 0)
            else:
                c["retry_count"] = c.get("retry_count", 0) + 1
            if c["status"] == "completed":
                agent["commands_completed"] = agent.get("commands_completed", 0) + 1
            else:
                agent["commands_failed"] = agent.get("commands_failed", 0) + 1
            return {"status": "recorded", "command_id": command_id}
    raise HTTPException(status_code=404, detail="Command not found")


@router.get("/agents/{agent_id}")
def get_agent(agent_id: str):
    agent = _agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {
        "agent_id": agent["agent_id"],
        "hostname": agent.get("hostname"),
        "agent_version": agent.get("agent_version"),
        "platform": agent.get("platform"),
        "status": agent.get("status"),
        "registered_at": agent.get("registered_at"),
        "last_seen": agent.get("last_seen"),
        "cpu_percent": agent.get("cpu_percent"),
        "memory_percent": agent.get("memory_percent"),
        "disk_percent": agent.get("disk_percent"),
        "ip_address": agent.get("ip_address"),
        "commands_completed": agent.get("commands_completed", 0),
        "commands_failed": agent.get("commands_failed", 0),
    }


@router.get("/agents/{agent_id}/platform")
def get_agent_platform(agent_id: str):
    agent = _agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    platform_name = str(agent.get("platform") or "unknown")
    if platform_name.startswith("linux") or platform_name == "linux":
        family = "linux"
    elif platform_name.startswith("darwin") or platform_name == "macos":
        family = "macos"
    else:
        family = "unknown"
    return {
        "agent_id": agent_id,
        "platform": platform_name,
        "platform_family": family,
        "supports_shell": family in {"linux", "macos"},
    }


@router.get("/agents/{agent_id}/commands")
def list_agent_commands(agent_id: str):
    if agent_id not in _agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {
        "agent_id": agent_id,
        "commands": [
            {
                "command_id": item["command_id"],
                "command": item["command"],
                "shell": item.get("shell", True),
                "status": item["status"],
                "created_at": item.get("created_at"),
                "result": item.get("result"),
                "finished_at": item.get("finished_at"),
                "retry_count": item.get("retry_count", 0),
                "acknowledged": item.get("acknowledged", False),
                "execution_profile": item.get("execution_profile"),
            }
            for item in _commands.get(agent_id, [])
        ],
    }


@router.post("/agents/{agent_id}/commands/{command_id}/ack")
def acknowledge_command(agent_id: str, command_id: str, body: CommandAck, agent_token: str):
    agent = _agents.get(agent_id)
    if not agent or agent["agent_token"] != agent_token:
        raise HTTPException(status_code=401, detail="Invalid agent credentials")
    for c in _commands.get(agent_id, []):
        if c["command_id"] == command_id:
            c["acknowledged"] = True
            c["status"] = body.status
            return {"status": "acknowledged", "command_id": command_id, "acknowledged": True}
    raise HTTPException(status_code=404, detail="Command not found")


@router.websocket("/agents/{agent_id}/stream")
async def stream_agent_output(websocket: WebSocket, agent_id: str):
    if agent_id not in _agents:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    await websocket.send_json({"event": "connected", "agent_id": agent_id})
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await websocket.close()


@router.get("/agents/{agent_id}/commands/{command_id}")
def get_command(agent_id: str, command_id: str):
    for c in _commands.get(agent_id, []):
        if c["command_id"] == command_id:
            return c
    raise HTTPException(status_code=404, detail="Command not found")
