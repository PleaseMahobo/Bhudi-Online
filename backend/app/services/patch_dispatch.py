"""Dispatch patch commands onto the agent runtime queue.

Native agents poll GET /api/v1/runtime/agents/{id}/commands/pending and execute
command_type patch_scan / patch_install (Windows Update via PowerShell COM).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


def queue_patch_commands(
    *,
    device_ids: list[str],
    action: str = "install",
    payload: dict[str, Any] | None = None,
    rollout_id: str | None = None,
    rollout_name: str | None = None,
) -> dict[str, Any]:
    """Enqueue patch_scan and/or patch_install for each runtime agent id.

    action:
      - scan   → patch_scan only
      - install → patch_install only
      - both   → scan then install (two queued commands per device)
    """
    # Import here to avoid circular imports at module load; runtime module owns the queues.
    from app.api.v1.endpoints import agent_runtime as runtime

    action = (action or "install").strip().lower()
    if action not in {"scan", "install", "both"}:
        action = "install"

    base_payload = dict(payload or {})
    if rollout_id:
        base_payload.setdefault("rollout_id", rollout_id)
    if rollout_name:
        base_payload.setdefault("rollout_name", rollout_name)

    types: list[str] = []
    if action in {"scan", "both"}:
        types.append("patch_scan")
    if action in {"install", "both"}:
        types.append("patch_install")

    queued: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []

    for device_id in device_ids or []:
        agent_id = str(device_id).strip()
        if not agent_id:
            continue
        agent = runtime._agents.get(agent_id)
        if agent is None:
            skipped.append({"device_id": agent_id, "reason": "agent_not_in_runtime"})
            continue

        for cmd_type in types:
            command_id = str(uuid.uuid4())
            cmd = {
                "id": command_id,
                "command_id": command_id,
                "agent_id": agent_id,
                "command": cmd_type,
                "command_type": cmd_type,
                "shell": False,
                "payload": dict(base_payload),
                "status": "pending",
                "retry_count": 0,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "source": "patch_rollout",
            }
            runtime._commands.setdefault(agent_id, []).append(cmd)
            queued.append(
                {
                    "device_id": agent_id,
                    "command_id": command_id,
                    "command_type": cmd_type,
                }
            )

    try:
        runtime._persist_agents()
    except Exception as exc:
        print(f"[patch_dispatch] persist failed: {exc}")

    return {
        "action": action,
        "queued_count": len(queued),
        "skipped_count": len(skipped),
        "queued": queued,
        "skipped": skipped,
    }
