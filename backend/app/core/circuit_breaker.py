"""
In-process circuit breaker (CLOSED → OPEN → HALF_OPEN → CLOSED).

Use per logical key (e.g. backup provider id, verification scope) to stop
repeated calls against a failing dependency. State is process-local; for
multi-worker deployments, pair with a shared store later.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(RuntimeError):
    """Raised when the circuit is open and calls are rejected."""

    def __init(
        self,
        message: str,
        *,
        key: str,
        state: CircuitState,
        opened_at: float | None = None,
        failure_count: int = 0,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.key = key
        self.state = state
        self.opened_at = opened_at
        self.failure_count = failure_count
        self.retry_after_seconds = retry_after_seconds


@dataclass
class CircuitStats:
    key: str
    state: CircuitState
    failure_count: int
    success_count: int
    consecutive_successes: int
    opened_at: float | None
    last_failure_at: float | None
    last_success_at: float | None
    failure_threshold: int
    recovery_timeout_seconds: float
    half_open_max_calls: int

    def to_dict(self) -> dict[str, Any]:
        now = time.time()
        retry_after = None
        if self.state == CircuitState.OPEN and self.opened_at is not None:
            elapsed = now - self.opened_at
            remaining = max(0.0, self.recovery_timeout_seconds - elapsed)
            retry_after = round(remaining, 2)
        return {
            "key": self.key,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "consecutive_successes": self.consecutive_successes,
            "opened_at": self.opened_at,
            "last_failure_at": self.last_failure_at,
            "last_success_at": self.last_success_at,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout_seconds": self.recovery_timeout_seconds,
            "half_open_max_calls": self.half_open_max_calls,
            "retry_after_seconds": retry_after,
        }


@dataclass
class _Breaker:
    key: str
    failure_threshold: int = 5
    recovery_timeout_seconds: float = 60.0
    half_open_max_calls: int = 1
    success_threshold: int = 1  # consecutive successes in half-open to close

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    consecutive_successes: int = 0
    half_open_inflight: int = 0
    opened_at: float | None = None
    last_failure_at: float | None = None
    last_success_at: float | None = None
    lock: threading.RLock = field(default_factory=threading.RLock)

    def stats(self) -> CircuitStats:
        return CircuitStats(
            key=self.key,
            state=self.state,
            failure_count=self.failure_count,
            success_count=self.success_count,
            consecutive_successes=self.consecutive_successes,
            opened_at=self.opened_at,
            last_failure_at=self.last_failure_at,
            last_success_at=self.last_success_at,
            failure_threshold=self.failure_threshold,
            recovery_timeout_seconds=self.recovery_timeout_seconds,
            half_open_max_calls=self.half_open_max_calls,
        )

    def _transition_to_half_open_if_ready(self) -> None:
        if self.state != CircuitState.OPEN or self.opened_at is None:
            return
        if (time.time() - self.opened_at) >= self.recovery_timeout_seconds:
            self.state = CircuitState.HALF_OPEN
            self.half_open_inflight = 0
            self.consecutive_successes = 0

    def allow(self) -> bool:
        with self.lock:
            self._transition_to_half_open_if_ready()
            if self.state == CircuitState.CLOSED:
                return True
            if self.state == CircuitState.OPEN:
                return False
            # HALF_OPEN — limited probe traffic
            if self.half_open_inflight < self.half_open_max_calls:
                self.half_open_inflight += 1
                return True
            return False

    def record_success(self) -> None:
        with self.lock:
            self.success_count += 1
            self.last_success_at = time.time()
            self.failure_count = 0
            if self.state == CircuitState.HALF_OPEN:
                self.consecutive_successes += 1
                self.half_open_inflight = max(0, self.half_open_inflight - 1)
                if self.consecutive_successes >= self.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.opened_at = None
                    self.consecutive_successes = 0
            else:
                self.state = CircuitState.CLOSED
                self.opened_at = None

    def record_failure(self) -> None:
        with self.lock:
            self.failure_count += 1
            self.last_failure_at = time.time()
            self.consecutive_successes = 0
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_inflight = max(0, self.half_open_inflight - 1)
                self.state = CircuitState.OPEN
                self.opened_at = time.time()
                return
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.opened_at = time.time()

    def reset(self) -> None:
        with self.lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.consecutive_successes = 0
            self.half_open_inflight = 0
            self.opened_at = None

    def force_open(self) -> None:
        with self.lock:
            self.state = CircuitState.OPEN
            self.opened_at = time.time()


class CircuitBreakerRegistry:
    """Thread-safe registry of named circuit breakers."""

    def __init__(self) -> None:
        self._breakers: dict[str, _Breaker] = {}
        self._lock = threading.RLock()

    def get(
        self,
        key: str,
        *,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 60.0,
        half_open_max_calls: int = 1,
        success_threshold: int = 1,
    ) -> _Breaker:
        with self._lock:
            b = self._breakers.get(key)
            if b is None:
                b = _Breaker(
                    key=key,
                    failure_threshold=failure_threshold,
                    recovery_timeout_seconds=recovery_timeout_seconds,
                    half_open_max_calls=half_open_max_calls,
                    success_threshold=success_threshold,
                )
                self._breakers[key] = b
            return b

    def stats(self, key: str | None = None) -> list[CircuitStats]:
        with self._lock:
            if key:
                b = self._breakers.get(key)
                return [b.stats()] if b else []
            return [b.stats() for b in self._breakers.values()]

    def reset(self, key: str) -> bool:
        with self._lock:
            b = self._breakers.get(key)
            if not b:
                return False
            b.reset()
            return True

    def reset_all(self) -> int:
        with self._lock:
            for b in self._breakers.values():
                b.reset()
            return len(self._breakers)

    def call(
        self,
        key: str,
        fn: Callable[[], T],
        *,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 60.0,
        half_open_max_calls: int = 1,
        success_threshold: int = 1,
        on_open: Callable[[CircuitOpenError], None] | None = None,
    ) -> T:
        """
        Execute ``fn`` if the circuit allows it.

        Records success/failure. Raises CircuitOpenError when open.
        """
        breaker = self.get(
            key,
            failure_threshold=failure_threshold,
            recovery_timeout_seconds=recovery_timeout_seconds,
            half_open_max_calls=half_open_max_calls,
            success_threshold=success_threshold,
        )
        if not breaker.allow():
            stats = breaker.stats()
            retry_after = None
            if stats.opened_at is not None:
                elapsed = time.time() - stats.opened_at
                retry_after = max(0.0, stats.recovery_timeout_seconds - elapsed)
            err = CircuitOpenError(
                f"Circuit '{key}' is open; rejecting call",
                key=key,
                state=stats.state,
                opened_at=stats.opened_at,
                failure_count=stats.failure_count,
                retry_after_seconds=retry_after,
            )
            if on_open:
                on_open(err)
            raise err
        try:
            result = fn()
        except Exception:
            breaker.record_failure()
            raise
        breaker.record_success()
        return result


# Process-wide default registry (backup providers, verification, etc.)
circuit_registry = CircuitBreakerRegistry()


def backup_provider_key(provider_id: str | Any) -> str:
    return f"backup:provider:{provider_id}"


def backup_verification_key(provider_id: str | Any) -> str:
    return f"backup:verification:{provider_id}"
