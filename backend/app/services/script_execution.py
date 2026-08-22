"""Shared helpers for script / automation task execution outcomes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

MAX_OUTPUT_CHARS = 64_000
MAX_SCRIPT_CHARS = 100_000
ALLOWED_SHELLS = frozenset({"powershell", "bash", "sh", "python", "cmd"})

TERMINAL_SUCCESS = frozenset({"success", "completed", "ok"})
TERMINAL_FAILURE = frozenset(
    {"failed", "error", "timed_out", "timeout", "cancelled", "canceled"}
)


class ScriptExecutionError(Exception):
    """Raised for client-facing validation / execution contract errors."""

    def __init__(self, message: str, *, code: str = "script_error"):
        super().__init__(message)
        self.code = code


def validate_shell(shell: str | None) -> str:
    value = (shell or "powershell").strip().lower()
    if value not in ALLOWED_SHELLS:
        raise ScriptExecutionError(
            f"Unsupported shell '{shell}'. Allowed: {', '.join(sorted(ALLOWED_SHELLS))}",
            code="invalid_shell",
        )
    return value


def validate_script_content(content: str | None, *, required: bool = True) -> str:
    text = (content or "").strip()
    if required and not text:
        raise ScriptExecutionError("Script content is required", code="empty_script")
    if len(text) > MAX_SCRIPT_CHARS:
        raise ScriptExecutionError(
            f"Script exceeds maximum size of {MAX_SCRIPT_CHARS} characters",
            code="script_too_large",
        )
    return text


def truncate_output(value: str | None, limit: int = MAX_OUTPUT_CHARS) -> str | None:
    if value is None:
        return None
    text = str(value)
    if len(text) <= limit:
        return text
    omitted = len(text) - limit
    return text[:limit] + f"\n… [truncated {omitted} characters]"


def normalize_task_status(
    *,
    requested_status: str | None,
    exit_code: int | None,
    error_output: str | None,
    completed: bool,
) -> str:
    """Derive a stable terminal/non-terminal status for ScriptTask rows."""
    status = (requested_status or "").strip().lower() or None

    if status in {"timeout", "timed_out"}:
        return "timed_out"
    if status in {"canceled", "cancelled"}:
        return "cancelled"
    if status in {"failed", "error"}:
        return "failed"
    if status in TERMINAL_SUCCESS:
        if exit_code is not None and exit_code != 0:
            return "failed"
        return "success"

    if exit_code is not None and exit_code != 0:
        return "failed"

    if completed:
        if exit_code is not None and exit_code != 0:
            return "failed"
        return "success"

    if status in {"queued", "pending", "sent", "running"}:
        return status
    if status == "dispatched":
        return "running"

    return status or "running"


def classify_outcome(
    *,
    status: str,
    exit_code: int | None,
    error_output: str | None,
) -> dict[str, Any]:
    """Structured outcome for logs and API clients."""
    normalized = (status or "unknown").lower()
    failed = normalized in TERMINAL_FAILURE or (
        exit_code is not None and exit_code != 0
    )
    success = (not failed) and (
        normalized in TERMINAL_SUCCESS or exit_code == 0
    )

    reason = None
    if failed:
        if normalized in {"timed_out", "timeout"}:
            reason = "execution_timeout"
        elif normalized == "cancelled":
            reason = "cancelled"
        elif exit_code is not None and exit_code != 0:
            reason = f"exit_code_{exit_code}"
        elif error_output:
            reason = "stderr_present"
        else:
            reason = "execution_failed"

    return {
        "success": bool(success) and not failed,
        "failed": bool(failed),
        "status": "failed" if failed else ("success" if success else normalized),
        "reason": reason,
        "exit_code": exit_code,
    }


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
