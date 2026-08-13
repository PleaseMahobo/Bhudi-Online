"""Prometheus metrics for Bhudi RMM API.

Expose at GET /metrics for Prometheus scrapes.
Safe if prometheus_client is missing (no-op registry).
"""
from __future__ import annotations

from typing import Any

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
        multiprocess,
        REGISTRY,
    )

    _PROM_AVAILABLE = True
except Exception:  # pragma: no cover
    _PROM_AVAILABLE = False
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"
    REGISTRY = None  # type: ignore


def _registry():
    if not _PROM_AVAILABLE:
        return None
    # Prefer process registry; multiprocess mode optional via PROMETHEUS_MULTIPROC_DIR
    import os

    if os.getenv("PROMETHEUS_MULTIPROC_DIR"):
        reg = CollectorRegistry()
        multiprocess.MultiProcessCollector(reg)
        return reg
    return REGISTRY


if _PROM_AVAILABLE:
    HTTP_REQUESTS = Counter(
        "bhudi_http_requests_total",
        "Total HTTP requests",
        ["method", "path", "status"],
    )
    HTTP_LATENCY = Histogram(
        "bhudi_http_request_duration_seconds",
        "HTTP request latency",
        ["method", "path"],
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
    )
    HEARTBEATS = Counter(
        "bhudi_agent_heartbeats_total",
        "Agent heartbeats received",
        ["status"],
    )
    METRIC_SAMPLES = Counter(
        "bhudi_metric_samples_total",
        "Device metric samples recorded",
        ["source"],  # memory|db
    )
    AGENTS_ONLINE = Gauge(
        "bhudi_agents_online",
        "Agents currently marked online in runtime registry",
    )
    DEVICE_CPU = Gauge(
        "bhudi_device_cpu_percent",
        "Last reported CPU percent by agent",
        ["agent_id", "hostname"],
    )
    DEVICE_MEMORY = Gauge(
        "bhudi_device_memory_percent",
        "Last reported memory percent by agent",
        ["agent_id", "hostname"],
    )
    DEVICE_DISK = Gauge(
        "bhudi_device_disk_percent",
        "Last reported disk percent by agent",
        ["agent_id", "hostname"],
    )
    AUTH_EVENTS = Counter(
        "bhudi_auth_events_total",
        "Auth events",
        ["event"],  # login_ok|login_fail|register_ok|register_fail
    )
else:  # pragma: no cover
    HTTP_REQUESTS = HTTP_LATENCY = HEARTBEATS = METRIC_SAMPLES = None  # type: ignore
    AGENTS_ONLINE = DEVICE_CPU = DEVICE_MEMORY = DEVICE_DISK = AUTH_EVENTS = None  # type: ignore


def observe_http(method: str, path: str, status: int, duration_s: float) -> None:
    if not _PROM_AVAILABLE:
        return
    # Collapse high-cardinality IDs in path
    safe = _normalize_path(path)
    try:
        HTTP_REQUESTS.labels(method=method, path=safe, status=str(status)).inc()
        HTTP_LATENCY.labels(method=method, path=safe).observe(duration_s)
    except Exception:
        pass


def _normalize_path(path: str) -> str:
    parts = []
    for p in (path or "/").split("/"):
        if not p:
            continue
        # UUID-like or long hex ids
        if len(p) >= 32 and all(c in "0123456789abcdef-" for c in p.lower()):
            parts.append(":id")
        else:
            parts.append(p)
    return "/" + "/".join(parts) if parts else "/"


def record_heartbeat(
    *,
    status: str = "online",
    agent_id: str | None = None,
    hostname: str | None = None,
    cpu: float | None = None,
    memory: float | None = None,
    disk: float | None = None,
) -> None:
    if not _PROM_AVAILABLE:
        return
    try:
        HEARTBEATS.labels(status=status or "online").inc()
        METRIC_SAMPLES.labels(source="memory").inc()
        if agent_id:
            host = (hostname or agent_id)[:64]
            aid = agent_id[:64]
            if cpu is not None:
                DEVICE_CPU.labels(agent_id=aid, hostname=host).set(float(cpu))
            if memory is not None:
                DEVICE_MEMORY.labels(agent_id=aid, hostname=host).set(float(memory))
            if disk is not None:
                DEVICE_DISK.labels(agent_id=aid, hostname=host).set(float(disk))
    except Exception:
        pass


def set_agents_online(count: int) -> None:
    if not _PROM_AVAILABLE or AGENTS_ONLINE is None:
        return
    try:
        AGENTS_ONLINE.set(int(count))
    except Exception:
        pass


def record_auth(event: str) -> None:
    if not _PROM_AVAILABLE or AUTH_EVENTS is None:
        return
    try:
        AUTH_EVENTS.labels(event=event).inc()
    except Exception:
        pass


def render_metrics() -> tuple[bytes, str]:
    """Return (body, content_type) for GET /metrics."""
    if not _PROM_AVAILABLE:
        return b"# prometheus_client not installed\n", "text/plain; charset=utf-8"
    reg = _registry()
    body = generate_latest(reg)
    return body, CONTENT_TYPE_LATEST
