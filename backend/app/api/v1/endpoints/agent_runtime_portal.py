from __future__ import annotations

from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.core.access_tiers import require_mfa_for_actions
from app.core.dependencies import current_tenant_user
from app.api.v1.endpoints.agent_runtime import (
    CommandCreate,
    RemoteDesktopBody,
    RemoteTerminalBody,
    _agents,
    _commands,
    _persist_agents,
    _platform_metadata,
    _translate_command,
)
from app.services.remote_session_manager import remote_session_manager

router = APIRouter(prefix="/runtime", tags=["agent-runtime-portal"])


def _tenant_agent(agent_id: str, user):
    agent = _agents.get(agent_id)
    if not agent or str(agent.get("tenant_id")) != str(user.tenant_id):
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


def _is_supportable(agent: dict) -> bool:
    if agent.get("supportable") is False:
        return False
    if agent.get("status") == "unlicensed":
        return False
    return True


@router.get("/agents")
def list_runtime_agents(user=Depends(current_tenant_user), include_unlicensed: bool = False):
    agents = [a for a in _agents.values() if str(a.get("tenant_id")) == str(user.tenant_id)]
    if not include_unlicensed:
        # Technicians only see supportable devices by default
        agents = [a for a in agents if _is_supportable(a)]
    return {"agents": agents, "count": len(agents)}


@router.get("/agents/{agent_id}")
def agent_details(agent_id: str, user=Depends(current_tenant_user)):
    agent = _tenant_agent(agent_id, user)
    if not _is_supportable(agent):
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/agents/{agent_id}/platform")
def agent_platform(agent_id: str, user=Depends(current_tenant_user)):
    agent = _tenant_agent(agent_id, user)
    if not _is_supportable(agent):
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"agent_id": agent_id, "platform": agent.get("platform"), **_platform_metadata(agent.get("platform"))}


@router.post("/agents/{agent_id}/commands")
def create_command(
    agent_id: str,
    body: CommandCreate,
    _mfa_user=Depends(require_mfa_for_actions),
    user=Depends(current_tenant_user),
):
    agent = _tenant_agent(agent_id, user)
    if not _is_supportable(agent):
        raise HTTPException(status_code=403, detail="Device is not supportable under your current seat limit")
    command_id = str(uuid.uuid4())
    profile = _platform_metadata(agent.get("platform"))
    cmd = {
        "id": command_id,
        "command_id": command_id,
        "agent_id": agent_id,
        "command": body.command,
        "shell": body.shell,
        "status": "pending",
        "retry_count": 0,
        "execution_profile": {
            **profile,
            "platform": agent.get("platform"),
            "translated_command": _translate_command(agent.get("platform"), body.command),
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _commands.setdefault(agent_id, []).append(cmd)
    _persist_agents()
    return cmd


@router.get("/agents/{agent_id}/commands")
def command_history(agent_id: str, user=Depends(current_tenant_user)):
    agent = _tenant_agent(agent_id, user)
    if not _is_supportable(agent):
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"commands": list(reversed(_commands.get(agent_id, [])))}


@router.get("/agents/{agent_id}/commands/{command_id}")
def command_details(agent_id: str, command_id: str, user=Depends(current_tenant_user)):
    agent = _tenant_agent(agent_id, user)
    if not _is_supportable(agent):
        raise HTTPException(status_code=404, detail="Agent not found")
    for command in _commands.get(agent_id, []):
        if command.get("id") == command_id or command.get("command_id") == command_id:
            return command
    raise HTTPException(status_code=404, detail="Command not found")


@router.post("/remote/desktop")
def remote_desktop(
    body: RemoteDesktopBody,
    _mfa_user=Depends(require_mfa_for_actions),
    user=Depends(current_tenant_user),
):
    agent = _tenant_agent(body.agent_id, user)
    if not _is_supportable(agent):
        raise HTTPException(status_code=403, detail="Device is not supportable under your current seat limit")
    session = remote_session_manager.create_session(
        agent_id=body.agent_id,
        session_type="desktop",
        metadata=body.model_dump(),
    )
    return {
        "session_id": session.session_id,
        "session_type": "desktop",
        "stream_path": f"/api/v1/remote-access/sessions/{session.session_id}/dashboard",
        "status": session.status,
    }


@router.post("/remote/terminal")
def remote_terminal(
    body: RemoteTerminalBody,
    _mfa_user=Depends(require_mfa_for_actions),
    user=Depends(current_tenant_user),
):
    agent = _tenant_agent(body.agent_id, user)
    if not _is_supportable(agent):
        raise HTTPException(status_code=403, detail="Device is not supportable under your current seat limit")
    session = remote_session_manager.create_session(
        agent_id=body.agent_id,
        session_type="terminal",
        metadata=body.model_dump(),
    )
    return {
        "session_id": session.session_id,
        "session_type": "terminal",
        "stream_path": f"/api/v1/remote-access/sessions/{session.session_id}/dashboard",
        "status": session.status,
    }
