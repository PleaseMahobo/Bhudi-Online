from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ==========================================================
# Enrollment
# ==========================================================

class AgentEnrollRequest(BaseModel):
    device_id: uuid.UUID
    hostname: str
    agent_version: str
    enrollment_secret: str


class AgentEnrollResponse(BaseModel):
    agent_uuid: uuid.UUID
    registration_state: str
    heartbeat_interval: int
    poll_interval: int


# ==========================================================
# Authentication
# ==========================================================

class AgentAuthenticationRequest(BaseModel):
    agent_uuid: uuid.UUID
    enrollment_secret: str


# ==========================================================
# Heartbeat
# ==========================================================

class AgentHeartbeatRequest(BaseModel):
    agent_uuid: uuid.UUID

    ip_address: str | None = None
    username: str | None = None

    cpu_percent: float | None = None
    memory_percent: float | None = None
    disk_percent: float | None = None

    uptime_seconds: int | None = None

    agent_version: str

    status: str = "online"


class AgentHeartbeatResponse(BaseModel):
    status: Literal["ok"]
    server_time: datetime
    poll_interval: int
    heartbeat_interval: int
    update_available: bool
    target_version: str | None


# ==========================================================
# Updates
# ==========================================================

class AgentUpdateRequest(BaseModel):
    target_version: str


# ==========================================================
# Agent View
# ==========================================================

class AgentResponse(BaseModel):

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: uuid.UUID

    agent_uuid: uuid.UUID

    tenant_id: uuid.UUID | None

    device_id: uuid.UUID | None

    hostname: str

    registration_state: str

    status: str

    trust_level: str

    agent_version: str

    target_version: str | None

    update_available: bool

    update_channel: str

    heartbeat_interval: int

    poll_interval: int

    health_score: int

    last_ip_address: str | None

    last_logged_on_user: str | None

    registered_at: datetime

    enrolled_at: datetime | None

    approved_at: datetime | None

    last_seen: datetime

    last_heartbeat: datetime | None

    last_checkin: datetime | None

    quarantined: bool

    revoked: bool

    auto_update: bool

    tamper_protection: bool

    restart_count: int

    last_error: str | None

    last_error_at: datetime | None

    created_at: datetime

    updated_at: datetime


# ==========================================================
# Commands
# ==========================================================

class AgentCommandRequest(BaseModel):

    command: str

    arguments: dict | None = None


class AgentCommandResponse(BaseModel):

    accepted: bool

    command_id: uuid.UUID


# ==========================================================
# Approval
# ==========================================================

class AgentApprovalRequest(BaseModel):

    approved_by: uuid.UUID


# ==========================================================
# Revocation
# ==========================================================

class AgentRevocationRequest(BaseModel):

    reason: str = Field(
        min_length=5,
        max_length=500,
    )


# ==========================================================
# Quarantine
# ==========================================================

class AgentQuarantineRequest(BaseModel):

    reason: str | None = None