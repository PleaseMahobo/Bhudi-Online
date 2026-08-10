"""Device org/site assignment."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.state import device_state

router = APIRouter(prefix="/devices", tags=["devices"])


class DeviceAssignment(BaseModel):
    organization_id: str | None = None
    organization_name: str | None = None
    site_id: str | None = None
    site_name: str | None = None


def _find_agent(device_id: str) -> dict[str, Any] | None:
    try:
        from app.api.v1.endpoints import agent_runtime

        agents = getattr(agent_runtime, "_agents", {}) or {}
        if device_id in agents:
            return agents[device_id]
        for a in agents.values():
            if str(a.get("agent_id")) == device_id or str(a.get("hostname")) == device_id:
                return a
    except Exception:
        pass
    for d in device_state.get_devices():
        if str(d.get("device_id") or d.get("id")) == device_id:
            return d
    return None


@router.patch("/{device_id}/assignment")
def assign_device(device_id: str, body: DeviceAssignment, db: Session = Depends(get_db)):
    agent = _find_agent(device_id)
    if not agent:
        raise HTTPException(404, "Device not found")
    agent_id = str(agent.get("agent_id") or device_id)
    try:
        from app.api.v1.endpoints import agent_runtime

        live = agent_runtime._agents.get(agent_id)
        if live is not None:
            if body.organization_id is not None:
                live["organization_id"] = body.organization_id
            if body.organization_name is not None:
                live["organization_name"] = body.organization_name
            if body.site_id is not None:
                live["site_id"] = body.site_id
            if body.site_name is not None:
                live["site_name"] = body.site_name
            agent = live
    except Exception:
        pass
    if agent_id in device_state.devices:
        d = device_state.devices[agent_id]
        for k in ("organization_id", "organization_name", "site_id", "site_name"):
            v = getattr(body, k)
            if v is not None:
                d[k] = v
    return {
        "id": agent_id,
        "device_id": agent_id,
        "agent_id": agent_id,
        "hostname": agent.get("hostname"),
        "organization_id": agent.get("organization_id"),
        "organization_name": agent.get("organization_name"),
        "site_id": agent.get("site_id"),
        "site_name": agent.get("site_name"),
        "status": agent.get("status"),
    }
