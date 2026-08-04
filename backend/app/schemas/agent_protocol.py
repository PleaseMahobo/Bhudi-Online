from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ==========================================================
# Base Message
# ==========================================================

class AgentMessage(BaseModel):

    protocol_version: int = 1

    message_id: uuid.UUID

    timestamp: datetime

    agent_id: uuid.UUID


# ==========================================================
# Heartbeat
# ==========================================================

class HeartbeatMessage(AgentMessage):

    hostname: str

    ip_address: str | None = None

    platform: str

    os_version: str

    agent_version: str

    cpu_usage: float

    memory_usage: float

    disk_usage: float

    uptime_seconds: int

    logged_in_user: str | None = None


# ==========================================================
# Poll Request
# ==========================================================

class PollRequest(AgentMessage):

    last_command: uuid.UUID | None = None


# ==========================================================
# Poll Response
# ==========================================================

class PollResponse(BaseModel):

    protocol_version: int = 1

    server_time: datetime

    commands: list[Any]

    next_poll_seconds: int = 30


# ==========================================================
# Command ACK
# ==========================================================

class CommandAcknowledgement(AgentMessage):

    command_id: uuid.UUID


# ==========================================================
# Command Result
# ==========================================================

class CommandResultMessage(AgentMessage):

    command_id: uuid.UUID

    exit_code: int | None = None

    stdout: str | None = None

    stderr: str | None = None

    execution_time_ms: int

    success: bool


# ==========================================================
# Agent Registration
# ==========================================================

class RegistrationRequest(BaseModel):

    hostname: str

    machine_guid: str

    platform: str

    architecture: str

    os_version: str

    serial_number: str | None = None

    bios_serial: str | None = None

    manufacturer: str | None = None

    model: str | None = None

    public_key: str


class RegistrationResponse(BaseModel):

    approved: bool

    agent_id: uuid.UUID

    poll_interval: int

    heartbeat_interval: int

    api_token: str

    server_version: str