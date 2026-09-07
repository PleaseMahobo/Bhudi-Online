from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

# Agent is "online" (green) if a heartbeat/last_seen is within this window.
# Independent of whether a console user is logged on — service heartbeats only.
ONLINE_THRESHOLD_SECONDS = 180


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

    def _seen_at(self) -> datetime | None:
        """Most recent proof the agent service is alive (not tied to interactive logon)."""
        for candidate in (self.last_heartbeat, self.last_checkin, self.last_seen):
            if candidate is None:
                continue
            if candidate.tzinfo is None:
                return candidate.replace(tzinfo=timezone.utc)
            return candidate
        return None

    def _age_seconds(self) -> int | None:
        seen = self._seen_at()
        if seen is None:
            return None
        return max(0, int((datetime.now(timezone.utc) - seen).total_seconds()))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def presence(self) -> Literal["online", "offline"]:
        """Service reachability: online while the PC is on and the agent heartbeats."""
        if self.revoked or self.quarantined:
            return "offline"
        age = self._age_seconds()
        if age is None:
            return "offline"
        if age <= ONLINE_THRESHOLD_SECONDS:
            return "online"
        return "offline"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def presence_color(self) -> Literal["green", "red"]:
        """Portal indicator: green = machine reachable, red = offline / powered off / no agent."""
        return "green" if self.presence == "online" else "red"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def presence_label(self) -> str:
        if self.revoked:
            return "Revoked"
        if self.quarantined:
            return "Quarantined"
        if self.presence == "online":
            return "Online"
        return "Offline"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def seconds_since_seen(self) -> int | None:
        return self._age_seconds()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def online_threshold_seconds(self) -> int:
        return ONLINE_THRESHOLD_SECONDS


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
