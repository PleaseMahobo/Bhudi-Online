from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.agent_command import AgentCommand
from app.services.agent_dispatcher import AgentDispatcher
from app.services.remote_session_manager import RemoteSessionState, remote_session_manager


REMOTE_ACCESS_COMMAND_TYPES = {
    "remote_desktop": "remote.desktop.start",
    "remote_terminal": "remote.terminal.start",
    "file_browser": "remote.file_browser",
    "registry_editor": "remote.registry",
    "task_manager": "remote.task_manager",
    "remote_powershell": "remote.powershell",
    "remote_cmd": "remote.cmd",
    "remote_event_viewer": "remote.event_viewer",
    "wake_on_lan": "remote.wake_on_lan",
    "remote_reboot": "remote.reboot",
    "safe_mode_reboot": "remote.safe_mode_reboot",
}


class RemoteAccessService:
    def __init__(self, db: Session):
        self.db = db
        self.dispatcher = AgentDispatcher(db)

    def list_capabilities(self) -> list[dict[str, Any]]:
        return [
            {
                "operation": "remote_desktop",
                "command_type": REMOTE_ACCESS_COMMAND_TYPES["remote_desktop"],
                "category": "interactive",
                "required_fields": ["session_mode"],
            },
            {
                "operation": "remote_terminal",
                "command_type": REMOTE_ACCESS_COMMAND_TYPES["remote_terminal"],
                "category": "interactive",
                "required_fields": ["shell"],
            },
            {
                "operation": "file_browser",
                "command_type": REMOTE_ACCESS_COMMAND_TYPES["file_browser"],
                "category": "filesystem",
                "required_fields": ["operation", "path"],
            },
            {
                "operation": "registry_editor",
                "command_type": REMOTE_ACCESS_COMMAND_TYPES["registry_editor"],
                "category": "system",
                "required_fields": ["operation", "hive", "key_path"],
            },
            {
                "operation": "task_manager",
                "command_type": REMOTE_ACCESS_COMMAND_TYPES["task_manager"],
                "category": "system",
                "required_fields": ["operation"],
            },
            {
                "operation": "remote_powershell",
                "command_type": REMOTE_ACCESS_COMMAND_TYPES["remote_powershell"],
                "category": "shell",
                "required_fields": ["command"],
            },
            {
                "operation": "remote_cmd",
                "command_type": REMOTE_ACCESS_COMMAND_TYPES["remote_cmd"],
                "category": "shell",
                "required_fields": ["command"],
            },
            {
                "operation": "remote_event_viewer",
                "command_type": REMOTE_ACCESS_COMMAND_TYPES["remote_event_viewer"],
                "category": "diagnostics",
                "required_fields": ["log_name"],
            },
            {
                "operation": "wake_on_lan",
                "command_type": REMOTE_ACCESS_COMMAND_TYPES["wake_on_lan"],
                "category": "power",
                "required_fields": ["mac_address"],
            },
            {
                "operation": "remote_reboot",
                "command_type": REMOTE_ACCESS_COMMAND_TYPES["remote_reboot"],
                "category": "power",
                "required_fields": [],
            },
            {
                "operation": "safe_mode_reboot",
                "command_type": REMOTE_ACCESS_COMMAND_TYPES["safe_mode_reboot"],
                "category": "power",
                "required_fields": ["with_networking"],
            },
        ]

    def create_interactive_session(
        self,
        *,
        agent_id: uuid.UUID,
        session_type: str,
        metadata: dict[str, Any] | None = None,
        session_id: str | None = None,
        command_id: uuid.UUID | None = None,
    ) -> RemoteSessionState:
        return remote_session_manager.create_session(
            agent_id=agent_id,
            session_type=session_type,
            metadata=metadata,
            session_id=session_id,
            command_id=command_id,
        )

    def get_session(self, session_id: uuid.UUID | str) -> RemoteSessionState | None:
        return remote_session_manager.get_session(session_id)

    def attach_session_to_command(self, session_id: uuid.UUID | str, command_id: uuid.UUID) -> RemoteSessionState | None:
        return remote_session_manager.attach_command(session_id, command_id)

    def queue_operation(
        self,
        *,
        agent_id: uuid.UUID,
        operation: str,
        payload: dict[str, Any],
        priority: int,
        timeout_seconds: int | None = None,
        requested_by: uuid.UUID | None = None,
        requires_reboot: bool = False,
    ) -> AgentCommand:
        command_type = REMOTE_ACCESS_COMMAND_TYPES[operation]
        enriched_payload = {"operation": operation, **payload}
        return self.dispatcher.queue_command(
            agent_id=agent_id,
            command_type=command_type,
            payload=enriched_payload,
            requested_by=requested_by,
            priority=priority,
            timeout_seconds=timeout_seconds,
            requires_reboot=requires_reboot,
        )

    def get_operation(self, command_id: uuid.UUID) -> AgentCommand | None:
        return self.db.get(AgentCommand, command_id)

    def is_remote_access_command(self, command: AgentCommand) -> bool:
        return command.command_type in set(REMOTE_ACCESS_COMMAND_TYPES.values())