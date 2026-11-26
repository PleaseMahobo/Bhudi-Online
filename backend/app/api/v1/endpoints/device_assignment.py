"""Device org/site assignment."""
from __future__ import annotations

from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.state import device_state
from app.models.agent import Agent
from app.models.device import Device
from app.models.msp import Organization, Site

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
    """Persist RMM assignment on the canonical Device/Agent hierarchy."""
    agent = db.get(Agent, device_id)
    if agent is None:
        # Legacy runtime identity compatibility: resolve an agent UUID stored
        # under the runtime store, but do not make that store authoritative.
        agent = db.query(Agent).filter(Agent.agent_uuid == device_id).first()
    if agent is None:
        raise HTTPException(404, "Device/agent not found")

    organization = None
    site = None
    if body.organization_id:
        try:
            organization = db.get(Organization, uuid.UUID(body.organization_id))
        except ValueError:
            raise HTTPException(400, "Invalid organization_id")
        if organization is None or (
            agent.tenant_id is not None and organization.tenant_id != agent.tenant_id
        ):
            raise HTTPException(400, "Organization is outside the agent tenant")

    if body.site_id:
        try:
            site = db.get(Site, uuid.UUID(body.site_id))
        except ValueError:
            raise HTTPException(400, "Invalid site_id")
        if site is None:
            raise HTTPException(400, "Site not found")
        if organization is not None and site.organization_id != organization.id:
            raise HTTPException(400, "Site does not belong to organization")
        if agent.tenant_id is not None and site.tenant_id != agent.tenant_id:
            raise HTTPException(400, "Site is outside the agent tenant")
        if organization is None:
            organization = db.get(Organization, site.organization_id)

    device = db.get(Device, agent.device_id) if agent.device_id else db.get(Device, agent.id)
    if device is None:
        device = Device(
            id=agent.id,
            tenant_id=agent.tenant_id,
            organization_id=organization.id if organization else agent.organization_id,
            site_id=site.id if site else agent.site_id,
            hostname=agent.hostname,
            status=agent.status,
            agent_version=agent.agent_version,
            version=agent.agent_version,
            last_seen=agent.last_seen,
        )
        db.add(device)

    if body.organization_id is not None:
        agent.organization_id = organization.id if organization else None
        device.organization_id = organization.id if organization else None
    if body.site_id is not None:
        agent.site_id = site.id if site else None
        device.site_id = site.id if site else None

    agent.device_id = device.id
    db.commit()
    db.refresh(agent)
    db.refresh(device)

    # Keep the existing runtime projection synchronized for clients that have
    # not yet moved to the canonical RMM API.
    try:
        from app.api.v1.endpoints import agent_runtime
        live = agent_runtime._agents.get(str(agent.id))
        if live is not None:
            live["organization_id"] = str(agent.organization_id) if agent.organization_id else None
            live["organization_name"] = organization.name if organization else None
            live["site_id"] = str(agent.site_id) if agent.site_id else None
            live["site_name"] = site.name if site else None
    except Exception:
        pass

    return {
        "id": str(device.id),
        "device_id": str(device.id),
        "agent_id": str(agent.id),
        "hostname": device.hostname,
        "organization_id": str(device.organization_id) if device.organization_id else None,
        "organization_name": organization.name if organization else None,
        "site_id": str(device.site_id) if device.site_id else None,
        "site_name": site.name if site else None,
        "status": device.status,
    }
