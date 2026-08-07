"""Circuit breaker helpers scoped to backup providers / verification."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.circuit_breaker import (
    CircuitOpenError,
    backup_provider_key,
    backup_verification_key,
    circuit_registry,
)

# Defaults tuned for backup vendor APIs / verification storms
BACKUP_FAILURE_THRESHOLD = 5
BACKUP_RECOVERY_SECONDS = 120.0
BACKUP_HALF_OPEN_MAX = 1


class BackupCircuitOpenError(ValueError):
    """API-friendly wrapper when backup circuit is open."""

    def __init__(self, message: str, *, key: str, retry_after_seconds: float | None = None,
                 failure_count: int = 0) -> None:
        super().__init__(message)
        self.key = key
        self.retry_after_seconds = retry_after_seconds
        self.failure_count = failure_count


def _breaker(key: str):
    return circuit_registry.get(
        key,
        failure_threshold=BACKUP_FAILURE_THRESHOLD,
        recovery_timeout_seconds=BACKUP_RECOVERY_SECONDS,
        half_open_max_calls=BACKUP_HALF_OPEN_MAX,
    )


def guard_verification(provider_id: UUID | str) -> None:
    """Raise BackupCircuitOpenError if verification circuit is open."""
    key = backup_verification_key(provider_id)
    b = _breaker(key)
    if not b.allow():
        stats = b.stats()
        retry_after = None
        if stats.opened_at is not None:
            import time
            elapsed = time.time() - stats.opened_at
            retry_after = max(0.0, stats.recovery_timeout_seconds - elapsed)
        raise BackupCircuitOpenError(
            f"Verification circuit open for provider {provider_id}; "
            f"backing off ({stats.failure_count} recent failures)",
            key=key,
            retry_after_seconds=retry_after,
            failure_count=stats.failure_count,
        )


def record_verification_success(provider_id: UUID | str) -> None:
    _breaker(backup_verification_key(provider_id)).record_success()


def record_verification_failure(provider_id: UUID | str) -> None:
    _breaker(backup_verification_key(provider_id)).record_failure()


def guard_provider(provider_id: UUID | str) -> None:
    key = backup_provider_key(provider_id)
    b = _breaker(key)
    if not b.allow():
        stats = b.stats()
        retry_after = None
        if stats.opened_at is not None:
            import time
            elapsed = time.time() - stats.opened_at
            retry_after = max(0.0, stats.recovery_timeout_seconds - elapsed)
        raise BackupCircuitOpenError(
            f"Provider circuit open for {provider_id}; rejecting operation",
            key=key,
            retry_after_seconds=retry_after,
            failure_count=stats.failure_count,
        )


def record_provider_success(provider_id: UUID | str) -> None:
    _breaker(backup_provider_key(provider_id)).record_success()


def record_provider_failure(provider_id: UUID | str) -> None:
    _breaker(backup_provider_key(provider_id)).record_failure()


def list_backup_circuits() -> list[dict[str, Any]]:
    return [
        s.to_dict()
        for s in circuit_registry.stats()
        if s.key.startswith("backup:")
    ]


def reset_backup_circuit(key: str) -> bool:
    return circuit_registry.reset(key)


def reset_all_backup_circuits() -> int:
    n = 0
    for s in list(circuit_registry.stats()):
        if s.key.startswith("backup:"):
            if circuit_registry.reset(s.key):
                n += 1
    return n


__all__ = [
    "BackupCircuitOpenError",
    "CircuitOpenError",
    "guard_verification",
    "record_verification_success",
    "record_verification_failure",
    "guard_provider",
    "record_provider_success",
    "record_provider_failure",
    "list_backup_circuits",
    "reset_backup_circuit",
    "reset_all_backup_circuits",
]
