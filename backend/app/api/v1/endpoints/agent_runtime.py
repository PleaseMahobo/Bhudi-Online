"""Practical agent runtime API."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path as _Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.core.access_tiers import require_mfa_for_actions
from app.models.user import User
from app.state import device_state
from app.services.remote_session_manager import remote_session_manager

router = APIRouter(prefix="/runtime")
_agents: dict[str, dict[str, Any]] = {}
_commands: dict[str, list[dict[str, Any]]] = {}
_RUNTIME_STORE = _Path(os.environ.get("BHUDI_RUNTIME_STORE", "/tmp/bhudi_runtime_agents.json"))


def _persist_agents() -> None:
    try:
        _RUNTIME_STORE.parent.mkdir(parents=True, exist_ok=True)
        tmp = _RUNTIME_STORE.with_suffix(".tmp")
        tmp.write_text(json.dumps({"agents": _agents}, default=str), encoding="utf-8")
        tmp.replace(_RUNTIME_STORE)
    except Exception as exc:
        print(f"[runtime] persist failed: {exc}")


def _restore_agents() -> None:
    try:
        if not _RUNTIME_STORE.exists():
            return
        data = json.loads(_RUNTIME_STORE.read_text(encoding="utf-8"))
        agents = data.get("agents") or {}
        if isinstance(agents, dict):
            _agents.update(agents)
            for agent_id in agents:
                _commands.setdefault(agent_id, [])
    except Exception as exc:
        print(f"[runtime] restore failed: {exc}")


_restore_agents()


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


class RemoteDesktopBody(BaseModel):
    agent_id: str
    session_mode: str = "control"
    display_protocol: str = "native"
    monitor_index: int = 0


class RemoteTerminalBody(BaseModel):
    agent_id: str
    shell: str = "powershell"


def _platform_metadata(platform: str | None) -> dict[str, str]:
    normalized = (platform or "windows").strip().lower()
    if normalized in {"darwin", "macos", "mac"}:
        return {"platform_family": "macos", "default_shell": "/bin/zsh", "package_manager": "brew"}
    if normalized in {"linux", "ubuntu", "debian", "rhel", "centos", "fedora"}:
        return {"platform_family": "linux", "default_shell": "/bin/bash", "package_manager": "apt"}
    return {"platform_family": "windows", "default_shell": "powershell.exe", "package_manager": "winget"}


def _translate_command(platform: str | None, command: str) -> str:
    normalized = " ".join(command.strip().lower().split())
    platform = (platform or "windows").lower()
    parts = normalized.split()
    if len(parts) == 2 and parts[0] in {"install", "update", "uninstall"} and parts[1] == "nginx":
        action = parts[0]
        if platform == "linux":
            return {"install": "sudo apt-get update && sudo apt-get install -y nginx", "update": "sudo apt-get update && sudo apt-get install -y nginx", "uninstall": "sudo apt-get remove -y nginx"}[action]
        if platform in {"darwin", "macos"}:
            return {"install": "brew update && brew install nginx", "update": "brew update && brew upgrade nginx", "uninstall": "brew uninstall nginx"}[action]
    return command


@router.post("/enroll", response_model=EnrollResponse)
def enroll(req: EnrollRequest):
    agent_id = str(uuid.uuid4())
    token = str(uuid.uuid4())
    _agents[agent_id] = {
        "agent_id": agent_id, "agent_token": token, "hostname": req.hostname, "agent_version": req.agent_version,
        "platform": req.platform, "platform_metadata": _platform_metadata(req.platform), "status": "online",
        "registered_at": datetime.now(timezone.utc).isoformat(), "last_seen": datetime.now(timezone.utc).isoformat(),
        "cpu_percent": None, "memory_percent": None, "disk_percent": None, "ip_address": None,
        "enrollment_secret": req.enrollment_secret, "commands_completed": 0, "commands_failed": 0,
    }
    _commands[agent_id] = []
    device_state.register_device(agent_id)
    device_state.devices[agent_id]["hostname"] = req.hostname
    _persist_agents()
    return EnrollResponse(agent_id=agent_id, agent_token=token)


@router.post("/heartbeat")
def heartbeat(req: HeartbeatRequest):
    agent = _agents.get(req.agent_id)
    if not agent or agent["agent_token"] != req.agent_token:
        raise HTTPException(status_code=401, detail="Invalid agent credentials")
    agent["status"] = req.status
    agent["last_seen"] = datetime.now(timezone.utc).isoformat()
    for field in ("cpu_percent", "memory_percent", "disk_percent", "ip_address", "hostname"):
        value = getattr(req, field)
        if value is not None:
            agent[field] = value
    device_state.heartbeat(req.agent_id)
    if req.agent_id in device_state.devices:
        if req.hostname:
            device_state.devices[req.agent_id]["hostname"] = req.hostname
        if req.ip_address:
            device_state.devices[req.agent_id]["ip_address"] = req.ip_address
    try:
        from app.services.metrics_service import record_heartbeat_metrics
        record_heartbeat_metrics(agent_id=req.agent_id, hostname=req.hostname or agent.get("hostname"), cpu_percent=req.cpu_percent,
                                 memory_percent=req.memory_percent, disk_percent=req.disk_percent,
                                 ip_address=req.ip_address or agent.get("ip_address"), status=req.status)
    except Exception as exc:
        print(f"[runtime] metrics persist skipped: {exc}")
    pending = sum(1 for c in _commands.get(req.agent_id, []) if c["status"] in ("pending", "dispatched"))
    _persist_agents()
    return {"ok": True, "pending_commands": pending, "heartbeat_interval": 30, "cpu_percent": agent.get("cpu_percent"),
            "memory_percent": agent.get("memory_percent"), "disk_percent": agent.get("disk_percent")}


@router.get("/agents")
def list_runtime_agents():
    return {"agents": list(_agents.values()), "count": len(_agents)}


@router.get("/agents/{agent_id}")
def agent_details(agent_id: str):
    agent = _agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/agents/{agent_id}/platform")
def agent_platform(agent_id: str):
    agent = _agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"agent_id": agent_id, "platform": agent.get("platform"), **_platform_metadata(agent.get("platform"))}


@router.post("/agents/{agent_id}/commands")
def create_command(agent_id: str, body: CommandCreate, _user: User = Depends(require_mfa_for_actions)):
    agent = _agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    command_id = str(uuid.uuid4())
    profile = _platform_metadata(agent.get("platform"))
    cmd = {
        "id": command_id, "command_id": command_id, "agent_id": agent_id, "command": body.command, "shell": body.shell,
        "status": "pending", "retry_count": 0,
        "execution_profile": {**profile, "platform": agent.get("platform"), "translated_command": _translate_command(agent.get("platform"), body.command)},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _commands.setdefault(agent_id, []).append(cmd)
    _persist_agents()
    return cmd


@router.get("/agents/{agent_id}/commands")
def command_history(agent_id: str):
    if agent_id not in _agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"commands": list(reversed(_commands.get(agent_id, [])))}


@router.get("/agents/{agent_id}/commands/pending")
def pending_commands(agent_id: str, agent_token: str | None = None):
    agent = _agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent_token is not None and agent_token != agent.get("agent_token"):
        raise HTTPException(status_code=401, detail="Invalid agent credentials")
    pending = [c for c in _commands.get(agent_id, []) if c.get("status") == "pending"]
    for command in pending:
        command["status"] = "dispatched"
    _persist_agents()
    return {"commands": pending}


@router.get("/agents/{agent_id}/commands/{command_id}")
def command_details(agent_id: str, command_id: str):
    for command in _commands.get(agent_id, []):
        if command.get("id") == command_id or command.get("command_id") == command_id:
            return command
    raise HTTPException(status_code=404, detail="Command not found")


@router.post("/agents/{agent_id}/commands/{command_id}/ack")
def acknowledge_command(agent_id: str, command_id: str, body: CommandAck, agent_token: str | None = None):
    agent = _agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent_token is not None and agent_token != agent.get("agent_token"):
        raise HTTPException(status_code=401, detail="Invalid agent credentials")
    for command in _commands.get(agent_id, []):
        if command.get("id") == command_id:
            command["status"] = body.status
            command["acknowledged_at"] = datetime.now(timezone.utc).isoformat()
            _persist_agents()
            return {"acknowledged": True, "command": command}
    raise HTTPException(status_code=404, detail="Command not found")


@router.post("/agents/{agent_id}/commands/{command_id}/result")
def command_result(agent_id: str, command_id: str, body: CommandResult, agent_token: str | None = None):
    agent = _agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent_token is not None and agent_token != agent.get("agent_token"):
        raise HTTPException(status_code=401, detail="Invalid agent credentials")
    for command in _commands.get(agent_id, []):
        if command.get("id") == command_id:
            command["exit_code"] = body.exit_code
            command["stdout"] = body.stdout
            command["stderr"] = body.stderr
            if body.exit_code == 0:
                command["status"] = "completed"
                agent["commands_completed"] = int(agent.get("commands_completed") or 0) + 1
            else:
                command["status"] = "pending"
                command["retry_count"] = int(command.get("retry_count") or 0) + 1
                agent["commands_failed"] = int(agent.get("commands_failed") or 0) + 1
            _persist_agents()
            return {"ok": True, "command": command}
    raise HTTPException(status_code=404, detail="Command not found")


@router.websocket("/agents/{agent_id}/stream")
async def agent_stream(websocket: WebSocket, agent_id: str):
    if agent_id not in _agents:
        await websocket.close(code=4404)
        return
    await websocket.accept()
    try:
        await websocket.send_json({"event": "connected", "agent_id": agent_id})
        while True:
            message = await websocket.receive_text()
            if message.lower() in {"ping", "heartbeat"}:
                await websocket.send_json({"event": "pong", "agent_id": agent_id})
    except WebSocketDisconnect:
        return


@router.post("/remote/desktop")
def remote_desktop(body: RemoteDesktopBody, _user: User = Depends(require_mfa_for_actions)):
    agent = _agents.get(body.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    session = remote_session_manager.create_session(agent_id=body.agent_id, session_type="desktop", metadata=body.model_dump())
    return {"session_id": session.session_id, "session_type": "desktop", "stream_path": f"/api/v1/remote-access/sessions/{session.session_id}/dashboard", "status": session.status}


@router.post("/remote/terminal")
def remote_terminal(body: RemoteTerminalBody, _user: User = Depends(require_mfa_for_actions)):
    agent = _agents.get(body.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    session = remote_session_manager.create_session(agent_id=body.agent_id, session_type="terminal", metadata=body.model_dump())
    return {"session_id": session.session_id, "session_type": "terminal", "stream_path": f"/api/v1/remote-access/sessions/{session.session_id}/dashboard", "status": session.status}
