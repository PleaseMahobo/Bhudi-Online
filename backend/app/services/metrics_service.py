"""Device metrics: in-memory ring buffer + optional Postgres persistence."""
from __future__ import annotations

import threading
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

_lock = threading.Lock()
# agent_id -> deque of samples (newest last)
_MEMORY: dict[str, deque[dict[str, Any]]] = defaultdict(lambda: deque(maxlen=720))
_TABLE_READY = False


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def record_heartbeat_metrics(
    *,
    agent_id: str,
    hostname: str | None = None,
    cpu_percent: float | None = None,
    memory_percent: float | None = None,
    disk_percent: float | None = None,
    ip_address: str | None = None,
    status: str | None = None,
) -> None:
    """Record one sample. Always writes memory; best-effort DB."""
    if not agent_id:
        return
    if cpu_percent is None and memory_percent is None and disk_percent is None:
        return

    ts = _utcnow()
    sample = {
        "agent_id": agent_id,
        "device_id": agent_id,
        "hostname": hostname,
        "cpu_percent": cpu_percent,
        "memory_percent": memory_percent,
        "disk_percent": disk_percent,
        "recorded_at": ts.isoformat(),
        "ts": ts,
    }
    with _lock:
        _MEMORY[agent_id].append(sample)

    try:
        _persist_db(
            agent_id=agent_id,
            hostname=hostname,
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_percent=disk_percent,
            ip_address=ip_address,
            status=status or "online",
            recorded_at=ts,
        )
    except Exception as exc:
        print(f"[metrics] db persist failed: {exc}")


def _ensure_table(conn) -> None:
    global _TABLE_READY
    if _TABLE_READY:
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS device_metrics (
            id UUID PRIMARY KEY,
            device_id UUID NULL,
            cpu_usage NUMERIC NULL,
            ram_usage NUMERIC NULL,
            disk_usage NUMERIC NULL,
            recorded_at TIMESTAMPTZ DEFAULT now(),
            tenant_id UUID NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_device_metrics_device_recorded
        ON device_metrics (device_id, recorded_at DESC)
        """
    )
    # Soft device row so FK-less installs still have an identity
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS devices (
            id UUID PRIMARY KEY,
            hostname TEXT NULL,
            ip TEXT NULL,
            status TEXT NULL,
            cpu INTEGER NULL,
            ram INTEGER NULL,
            disk INTEGER NULL,
            last_seen TIMESTAMPTZ NULL,
            agent_version TEXT NULL,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    _TABLE_READY = True


def _persist_db(
    *,
    agent_id: str,
    hostname: str | None,
    cpu_percent: float | None,
    memory_percent: float | None,
    disk_percent: float | None,
    ip_address: str | None,
    status: str,
    recorded_at: datetime,
) -> None:
    from sqlalchemy import text

    from app.database.session import SessionLocal

    if SessionLocal is None:
        return

    try:
        device_uuid = uuid.UUID(str(agent_id))
    except Exception:
        device_uuid = uuid.uuid5(uuid.NAMESPACE_URL, f"bhudi-agent:{agent_id}")

    session = SessionLocal()
    try:
        _ensure_table(session.connection())
        # Upsert lightweight device snapshot
        session.execute(
            text(
                """
                INSERT INTO devices (id, hostname, ip, status, cpu, ram, disk, last_seen)
                VALUES (:id, :hostname, :ip, :status, :cpu, :ram, :disk, :last_seen)
                ON CONFLICT (id) DO UPDATE SET
                    hostname = COALESCE(EXCLUDED.hostname, devices.hostname),
                    ip = COALESCE(EXCLUDED.ip, devices.ip),
                    status = EXCLUDED.status,
                    cpu = COALESCE(EXCLUDED.cpu, devices.cpu),
                    ram = COALESCE(EXCLUDED.ram, devices.ram),
                    disk = COALESCE(EXCLUDED.disk, devices.disk),
                    last_seen = EXCLUDED.last_seen
                """
            ),
            {
                "id": str(device_uuid),
                "hostname": hostname,
                "ip": ip_address,
                "status": status,
                "cpu": int(cpu_percent) if cpu_percent is not None else None,
                "ram": int(memory_percent) if memory_percent is not None else None,
                "disk": int(disk_percent) if disk_percent is not None else None,
                "last_seen": recorded_at,
            },
        )
        session.execute(
            text(
                """
                INSERT INTO device_metrics (id, device_id, cpu_usage, ram_usage, disk_usage, recorded_at)
                VALUES (:id, :device_id, :cpu, :ram, :disk, :recorded_at)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "device_id": str(device_uuid),
                "cpu": Decimal(str(cpu_percent)) if cpu_percent is not None else None,
                "ram": Decimal(str(memory_percent)) if memory_percent is not None else None,
                "disk": Decimal(str(disk_percent)) if disk_percent is not None else None,
                "recorded_at": recorded_at,
            },
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_metrics(
    device_id: str,
    *,
    minutes: int = 60,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Return metrics newest-last for charts."""
    minutes = max(5, min(int(minutes or 60), 60 * 24 * 7))
    limit = max(10, min(int(limit or 500), 5000))
    cutoff = _utcnow() - timedelta(minutes=minutes)

    rows: list[dict[str, Any]] = []

    # Memory buffer
    with _lock:
        for s in list(_MEMORY.get(device_id, [])):
            ts = s.get("ts")
            if isinstance(ts, datetime) and ts < cutoff:
                continue
            rows.append(
                {
                    "device_id": device_id,
                    "cpu_percent": s.get("cpu_percent"),
                    "memory_percent": s.get("memory_percent"),
                    "disk_percent": s.get("disk_percent"),
                    "recorded_at": s.get("recorded_at"),
                    "source": "memory",
                }
            )

    # DB history
    try:
        from sqlalchemy import text

        from app.database.session import SessionLocal

        if SessionLocal is not None:
            try:
                device_uuid = str(uuid.UUID(str(device_id)))
            except Exception:
                device_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"bhudi-agent:{device_id}"))

            session = SessionLocal()
            try:
                result = session.execute(
                    text(
                        """
                        SELECT cpu_usage, ram_usage, disk_usage, recorded_at
                        FROM device_metrics
                        WHERE device_id = :device_id
                          AND recorded_at >= :cutoff
                        ORDER BY recorded_at ASC
                        LIMIT :limit
                        """
                    ),
                    {"device_id": device_uuid, "cutoff": cutoff, "limit": limit},
                )
                for cpu, ram, disk, recorded_at in result:
                    if hasattr(recorded_at, "isoformat"):
                        ra = recorded_at.isoformat()
                    else:
                        ra = str(recorded_at)
                    rows.append(
                        {
                            "device_id": device_id,
                            "cpu_percent": float(cpu) if cpu is not None else None,
                            "memory_percent": float(ram) if ram is not None else None,
                            "disk_percent": float(disk) if disk is not None else None,
                            "recorded_at": ra,
                            "source": "db",
                        }
                    )
            finally:
                session.close()
    except Exception as exc:
        print(f"[metrics] db query failed: {exc}")

    # Dedupe by recorded_at, sort ascending
    by_ts: dict[str, dict[str, Any]] = {}
    for r in rows:
        key = str(r.get("recorded_at") or "")
        if not key:
            continue
        by_ts[key] = r
    ordered = [by_ts[k] for k in sorted(by_ts.keys())]
    if len(ordered) > limit:
        ordered = ordered[-limit:]
    return ordered


def latest_for_agents(agent_ids: list[str] | None = None) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    with _lock:
        ids = agent_ids or list(_MEMORY.keys())
        for aid in ids:
            buf = _MEMORY.get(aid)
            if not buf:
                continue
            s = buf[-1]
            out[aid] = {
                "cpu_percent": s.get("cpu_percent"),
                "memory_percent": s.get("memory_percent"),
                "disk_percent": s.get("disk_percent"),
                "recorded_at": s.get("recorded_at"),
            }
    return out
