from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.command import CommandStatus, CommandType


class CommandCreate(BaseModel):
    agent_id: uuid.UUID
    command_type: CommandType
    command_text: str = Field(min_length=1)
    arguments: str | None = None
    working_directory: str | None = None
    timeout_seconds: int = Field(default=300, ge=5, le=7200)
    run_as_system: bool = True


class AgentCommand(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    command_type: CommandType
    command_text: str
    arguments: str | None
    working_directory: str | None
    timeout_seconds: int
    run_as_system: bool
    created_at: datetime


class CommandResult(BaseModel):
    stdout: str | None = None
    stderr: str | None = None
    exit_code: int | None = None
    execution_time_ms: int | None = None
    metadata: dict[str, Any] | None = None


class CommandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    agent_id: uuid.UUID
    command_type: CommandStatus | str
    status: CommandStatus | str
    command_text: str
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    exit_code: int | None


class CommandHistoryResponse(BaseModel):
    total: int
    items: list[CommandResponse]


class AgentPollResponse(BaseModel):
    commands: list[AgentCommand]


class CommandCreateRequest(BaseModel):
    agent_id: uuid.UUID
    command_type: str = "shell"
    payload: dict[str, Any] | None = None
    priority: int = 5
    requested_by: uuid.UUID | None = None
    timeout_seconds: int | None = Field(default=None, ge=5, le=7200)
    requires_reboot: bool = False


CommandRequest = CommandCreateRequest
