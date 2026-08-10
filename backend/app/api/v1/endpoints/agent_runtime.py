"""
Practical agent runtime API for Phase A/B testing.

Endpoints (under /api/v1):
  POST /runtime/enroll
  POST /runtime/heartbeat
  GET  /runtime/agents
  POST /runtime/agents/{agent_id}/commands
  GET  /runtime/agents/{agent_id}/commands/pending
  POST /runtime/agents/{agent_id}/commands/{command_id}/result
  POST /runtime/remote/terminal
  POST /runtime/remote/desktop

Agents are persisted to disk (BHUDI_RUNTIME_STORE) so process restarts
do not invalidate enrolled agent tokens.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path as _Path
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

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
            print(f"[runtime] restored {len(agents)} agents from {_RUNTIME_STORE}")
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
    _persist_agents()
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
        if req.hostname:
            device_state.devices[req.agent_id]["hostname"] = req.hostname
        if req.ip_address:
            device_state.devices[req.agent_id]["ip_address"] = req.ip_address

    pending = sum(
        1 for c in _commands.get(req.agent_id, []) if c["status"] in ("pending", "dispatched")
    )
    _persist_agents()
    return {
        "ok": True,
        "pending_commands": pending,
        "heartbeat_interval": 30,
    }


@router.get("/agents")
def list_runtime_agents():
    return {"agents": list(_agents.values()), "count": len(_agents)}


def _translate_package_command(platform_name: str, command: str) -> str | None:
    normalized = command.strip().lower()
    package = command.strip().split(" ", 1)[-1] if " " in command.strip() else ""
    if normalized.startswith("install ") and package:
        if "darwin" in platform_name or platform_name == "macos":
            return f"brew install {package}"
        if "linux" in platform_name:
            return f"sudo apt-get install -y {package}"
    if normalized.startswith("uninstall ") and package:
        if "darwin" in platform_name or platform_name == "macos":
            return f"brew uninstall {package}"
        if "linux" in platform_name:
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
                    "command": c.get("command") or "",
                    "shell": c.get("shell", True),
                    "command_type": c.get("command_type"),
                    "payload": c.get("payload") or {},
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
                "command": item.get("command"),
                "shell": item.get("shell", True),
                "status": item["status"],
                "command_type": item.get("command_type"),
            }
            for item in _commands.get(agent_id, [])
        ],
    }


class RuntimeRemoteTerminalRequest(BaseModel):
    agent_id: str
    shell: str = "powershell"
    working_directory: str | None = None
    interactive: bool = True


class RuntimeRemoteDesktopRequest(BaseModel):
    agent_id: str
    session_mode: str = "control"
    display_protocol: str = "native"
    monitor_index: int = 0


def _queue_structured(agent_id: str, command_type: str, payload: dict) -> dict:
    if agent_id not in _agents:
        raise HTTPException(
            status_code=404,
            detail="Agent not found — is the native agent online and enrolled against this backend?",
        )
    cmd_id = str(uuid.uuid4())
    item = {
        "command_id": cmd_id,
        "command": "",
        "shell": False,
        "command_type": command_type,
        "payload": payload,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "result": None,
    }
    _commands.setdefault(agent_id, []).append(item)
    return {"command_id": cmd_id, "agent_id": agent_id, "command_type": command_type, "payload": payload}


@router.post("/remote/terminal")
def runtime_remote_terminal(body: RuntimeRemoteTerminalRequest):
    session = remote_session_manager.create_session(
        agent_id=body.agent_id,
        session_type="terminal",
        metadata={"shell": body.shell, "working_directory": body.working_directory},
    )
    payload = {
        "session_id": session.session_id,
        "shell": body.shell,
        "working_directory": body.working_directory,
        "interactive": body.interactive,
        "session_type": "terminal",
    }
    queued = _queue_structured(body.agent_id, "remote.terminal.start", payload)
    remote_session_manager.attach_command(session.session_id, queued["command_id"])
    return {
        **queued,
        "session_id": session.session_id,
        "session_status": session.status,
        "stream_path": f"/api/v1/remote-access/sessions/{session.session_id}/dashboard",
        "operation": "remote_terminal",
    }


@router.post("/remote/desktop")
def runtime_remote_desktop(body: RuntimeRemoteDesktopRequest):
    session = remote_session_manager.create_session(
        agent_id=body.agent_id,
        session_type="desktop",
        metadata={
            "session_mode": body.session_mode,
            "display_protocol": body.display_protocol,
            "monitor_index": body.monitor_index,
        },
    )
    payload = {
        "session_id": session.session_id,
        "session_mode": body.session_mode,
        "display_protocol": body.display_protocol,
        "session_type": "desktop",
        "monitor_index": body.monitor_index,
    }
    queued = _queue_structured(body.agent_id, "remote.desktop.start", payload)
    remote_session_manager.attach_command(session.session_id, queued["command_id"])
    return {
        **queued,
        "session_id": session.session_id,
        "session_status": session.status,
        "stream_path": f"/api/v1/remote-access/sessions/{session.session_id}/dashboard",
        "operation": "remote_desktop",
    }
