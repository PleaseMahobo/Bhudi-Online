from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

DEFAULT_VERIFICATION_TIMEOUT_SECONDS = 3600
DEFAULT_MAX_RETRIES = 3


class VerificationTimeoutError(ValueError):
    def __init__(
        self,
        message: str,
        restore_id: UUID | None = None,
        *,
        attempt: int | None = None,
        retries_remaining: int | None = None,
        can_retry: bool = False,
    ) -> None:
        super().__init__(message)
        self.restore_id = restore_id
        self.attempt = attempt
        self.retries_remaining = retries_remaining
        self.can_retry = can_retry


class VerificationRetryExhaustedError(ValueError):
    def __init__(self, message: str, restore_id: UUID | None = None) -> None:
        super().__init__(message)
        self.restore_id = restore_id


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _utcnow()).isoformat()


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (TypeError, ValueError):
        return None


PROVIDER_CATALOG: list[dict[str, str]] = [
    {"provider_key": "veeam", "display_name": "Veeam"},
    {"provider_key": "datto", "display_name": "Datto"},
    {"provider_key": "acronis", "display_name": "Acronis"},
    {"provider_key": "azure_backup", "display_name": "Azure Backup"},
    {"provider_key": "backblaze", "display_name": "Backblaze"},
    {"provider_key": "onedrive", "display_name": "OneDrive"},
    {"provider_key": "google_drive", "display_name": "Google Drive"},
]

_BASE_CHECKS: dict[str, list[dict[str, Any]]] = {
    "file": [
        {"id": "path_exists", "name": "Target path exists", "description": "Restored path is present on the target", "required": True},
        {"id": "size_nonzero", "name": "Non-zero size", "description": "Restored object has content", "required": True},
        {"id": "checksum_match", "name": "Checksum match", "description": "Hash matches backup catalog when available", "required": False},
    ],
    "folder": [
        {"id": "path_exists", "name": "Folder exists", "description": "Restored folder is present", "required": True},
        {"id": "child_count", "name": "Child objects present", "description": "Folder contains expected children", "required": True},
        {"id": "permissions_ok", "name": "Permissions intact", "description": "ACL/ownership roughly preserved", "required": False},
    ],
    "volume": [
        {"id": "volume_mounted", "name": "Volume mounted", "description": "Restored volume is mounted and readable", "required": True},
        {"id": "filesystem_clean", "name": "Filesystem clean", "description": "No critical FS errors on restored volume", "required": True},
        {"id": "boot_sector", "name": "Boot metadata", "description": "Boot sector / EFI data present if applicable", "required": False},
    ],
    "full_system": [
        {"id": "boot_check", "name": "System boots", "description": "Restored system reaches OS", "required": True},
        {"id": "service_health", "name": "Critical services", "description": "Core services are running", "required": True},
        {"id": "network_up", "name": "Network stack", "description": "NIC has link / IP", "required": True},
        {"id": "agent_heartbeat", "name": "RMM agent heartbeat", "description": "Bhudi agent reports healthy after restore", "required": False},
    ],
    "mailbox": [
        {"id": "mailbox_accessible", "name": "Mailbox accessible", "description": "Mailbox opens in provider API", "required": True},
        {"id": "item_sample", "name": "Sample items readable", "description": "Sample messages/folders open", "required": True},
    ],
    "database": [
        {"id": "db_online", "name": "Database online", "description": "Engine reports DB online", "required": True},
        {"id": "connection_test", "name": "Connection test", "description": "Can open a client connection", "required": True},
        {"id": "row_sample", "name": "Row sample", "description": "SELECT sample succeeds", "required": False},
    ],
}


def _checks_for(restore_type: str, policy: str) -> list[dict[str, Any]]:
    base = list(_BASE_CHECKS.get(restore_type, _BASE_CHECKS["file"]))
    if policy == "quick":
        base = [c for c in base if c.get("required")]
    elif policy == "strict":
        base = [{**c, "required": True} for c in base]
    return base


def _summarize_checks(checks: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total": len(checks),
        "passed": sum(1 for c in checks if c.get("status") == "passed"),
        "failed": sum(1 for c in checks if c.get("status") == "failed"),
        "skipped": sum(1 for c in checks if c.get("status") == "skipped"),
        "pending": sum(1 for c in checks if c.get("status") in ("pending", "running")),
        "required_failed": sum(1 for c in checks if c.get("required") and c.get("status") == "failed"),
    }


def _build_verification(
    restore_type: str,
    policy: str,
    enabled: bool = True,
    timeout_seconds: int | None = None,
    *,
    max_retries: int | None = None,
    auto_retry: bool = False,
    attempt: int = 1,
    retry_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    checks = []
    for c in _checks_for(restore_type, policy):
        checks.append({
            "id": c["id"], "name": c["name"], "description": c.get("description"),
            "required": bool(c.get("required", True)), "status": "pending",
            "message": None, "evidence": None, "started_at": None, "finished_at": None,
        })
    timeout = timeout_seconds or DEFAULT_VERIFICATION_TIMEOUT_SECONDS
    timeout = max(60, min(86400, timeout))
    mr = DEFAULT_MAX_RETRIES if max_retries is None else int(max_retries)
    mr = max(0, min(10, mr))
    attempt = max(1, int(attempt))
    history = list(retry_history or [])
    retries_remaining = max(0, mr - (attempt - 1))
    return {
        "enabled": enabled, "policy": policy,
        "status": "pending" if enabled else "skipped",
        "started_at": None, "finished_at": None,
        "timeout_seconds": timeout, "deadline_at": None,
        "timed_out_at": None, "timeout_error": None,
        "attempt": attempt, "max_retries": mr, "auto_retry": bool(auto_retry),
        "retries_remaining": retries_remaining, "retry_history": history,
        "checks": checks, "summary": _summarize_checks(checks),
    }


def _verification_deadline(verification: dict[str, Any]) -> datetime | None:
    explicit = _parse_iso(verification.get("deadline_at"))
    if explicit:
        return explicit
    started = _parse_iso(verification.get("started_at"))
    if not started:
        return None
    timeout = int(verification.get("timeout_seconds") or DEFAULT_VERIFICATION_TIMEOUT_SECONDS)
    return started + timedelta(seconds=timeout)


def _is_timed_out(verification: dict[str, Any], now: datetime | None = None) -> bool:
    if verification.get("status") in ("passed", "failed", "skipped", "timed_out"):
        return verification.get("status") == "timed_out"
    deadline = _verification_deadline(verification)
    if not deadline:
        return False
    return (now or _utcnow()) > deadline
