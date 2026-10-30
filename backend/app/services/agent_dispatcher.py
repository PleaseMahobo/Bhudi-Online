from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.agent_command import AgentCommand
from app.repositories.agent_repository import AgentRepository
from app.repositories.agent_command_repository import AgentCommandRepository

logger = logging.getLogger(__name__)


class AgentDispatcher:
    """Tenant-scoped command dispatcher. Never queue without verified scope."""

    def __init__(self, db: Session):
        self.db = db
        self.agent_repo = AgentRepository(db)
        self.command_repo = AgentCommandRepository(db)

    def _authorized_agent(self, agent_id: uuid.UUID, tenant_id: uuid.UUID | None) -> Agent:
        # Missing tenant context must fail closed; unscoped repository lookup is forbidden.
        if tenant_id is None:
            logger.warning(
                "remote_dispatch.authorization_decision",
                extra={"reason_code": "missing_tenant_scope", "agent_id": str(agent_id),
                       "tenant_scope_present": False, "allowed": False},
            )
            raise PermissionError("Trusted tenant scope is required for command dispatch.")

        agent = self.agent_repo.get(agent_id, tenant_id=tenant_id)
        if agent is None:
            # Deliberately do not distinguish nonexistent IDs from cross-tenant ownership.
            logger.warning(
                "remote_dispatch.authorization_decision",
                extra={"reason_code": "agent_not_found_or_wrong_tenant", "agent_id": str(agent_id),
                       "tenant_id": str(tenant_id), "tenant_scope_present": True, "allowed": False},
            )
            raise PermissionError("Agent is not owned by the authorized tenant.")

        # Snapshot only authorization facts. Never log credentials, payloads, or endpoint data.
        state = {
            "agent_id": str(agent_id),
            "tenant_id": str(tenant_id),
            "tenant_scope_present": True,
            "enabled": bool(agent.enabled),
            "revoked": bool(getattr(agent, "revoked", False)),
            "quarantined": bool(getattr(agent, "quarantined", False)),
            "registration_state": getattr(agent, "registration_state", None),
        }
        logger.info("remote_dispatch.authorization_snapshot", extra=state)

        reason = None
        if not agent.enabled:
            reason = "agent_disabled"
        elif getattr(agent, "revoked", False):
            reason = "agent_revoked"
        elif getattr(agent, "quarantined", False):
            reason = "agent_quarantined"
        elif getattr(agent, "registration_state", None) != "approved":
            reason = "agent_not_approved"

        if reason is not None:
            logger.warning(
                "remote_dispatch.authorization_decision",
                extra={**state, "reason_code": reason, "allowed": False},
            )
            if reason == "agent_disabled":
                raise PermissionError("Agent disabled.")
            if reason == "agent_revoked":
                raise PermissionError("Agent revoked.")
            if reason == "agent_quarantined":
                raise PermissionError("Agent quarantined.")
            raise PermissionError("Agent is not approved for command execution.")

        logger.info(
            "remote_dispatch.authorization_decision",
            extra={**state, "reason_code": "all_authorization_checks_passed", "allowed": True},
        )
        return agent

    def queue_command(
        self,
        *,
        agent_id: uuid.UUID,
        command_type: str,
        payload: dict[str, Any] | None = None,
        requested_by: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
        priority: int = 5,
        timeout_seconds: int | None = None,
        requires_reboot: bool = False,
    ) -> AgentCommand:
        agent = self._authorized_agent(agent_id, tenant_id)
        command = AgentCommand(
            id=uuid.uuid4(),
            agent_id=agent.id,
            command_type=command_type,
            payload=payload or {},
            priority=priority,
            issued_by=requested_by,
            timeout_seconds=timeout_seconds or agent.command_timeout,
            requires_reboot=requires_reboot,
        )
        command = self.command_repo.create(command)
        self.db.commit()
        self.db.refresh(command)
        return command

    def get_pending_commands(
        self,
        agent_id: uuid.UUID,
        *,
        tenant_id: uuid.UUID | None = None,
    ) -> list[AgentCommand]:
        self._authorized_agent(agent_id, tenant_id)
        return self.command_repo.get_pending_commands(agent_id)

    def mark_sent(
        self,
        command_id: uuid.UUID,
        *,
        agent_id: uuid.UUID,
        tenant_id: uuid.UUID | None = None,
    ) -> AgentCommand:
        self._authorized_agent(agent_id, tenant_id)
        command = self.command_repo.get(command_id)
        if command is None or command.agent_id != agent_id:
            raise PermissionError("Command is not assigned to the authenticated agent.")
        self.command_repo.mark_dispatched(command_id)
        self.db.commit()
        self.db.refresh(command)
        return command

    def mark_completed(
        self,
        command_id: uuid.UUID,
        result: dict | None = None,
        *,
        agent_id: uuid.UUID,
        tenant_id: uuid.UUID | None = None,
    ) -> AgentCommand:
        self._authorized_agent(agent_id, tenant_id)
        command = self.command_repo.get(command_id)
        if command is None or command.agent_id != agent_id:
            raise PermissionError("Command is not assigned to the authenticated agent.")
        if command.started_at is None:
            self.command_repo.mark_running(command_id)
        exit_code = int((result or {}).get("exit_code", 0))
        stdout = (result or {}).get("stdout", "")
        stderr = (result or {}).get("stderr", "")
        self.command_repo.complete(command_id, exit_code, stdout, stderr, result or {})
        self.db.commit()
        self.db.refresh(command)
        return command

    def mark_failed(
        self,
        command_id: uuid.UUID,
        error: str,
        *,
        agent_id: uuid.UUID,
        tenant_id: uuid.UUID | None = None,
    ) -> AgentCommand:
        self._authorized_agent(agent_id, tenant_id)
        command = self.command_repo.get(command_id)
        if command is None or command.agent_id != agent_id:
            raise PermissionError("Command is not assigned to the authenticated agent.")
        self.command_repo.fail(
            command_id,
            error,
            {"error": error, "failed_at": datetime.now(timezone.utc).isoformat()},
        )
        self.db.commit()
        self.db.refresh(command)
        return command
