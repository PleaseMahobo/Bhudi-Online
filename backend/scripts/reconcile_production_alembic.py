import os
import subprocess
import sys

import psycopg

TARGET = "m7n8o9p0q1r2"

# Keep this physical-schema guard aligned with app.models.agent.Agent. Alembic can
# be stamped at TARGET while a legacy production database is still missing columns,
# so runtime startup must verify the actual table rather than trust revision state.
REQUIRED_AGENT_COLUMNS = {
    "agent_uuid": "UUID",
    "agent_version": "TEXT",
    "agent_build": "TEXT",
    "update_channel": "TEXT NOT NULL DEFAULT 'stable'",
    "platform": "TEXT",
    "architecture": "TEXT",
    "operating_system": "TEXT",
    "os_version": "TEXT",
    "manufacturer": "TEXT",
    "model": "TEXT",
    "serial_number": "TEXT",
    "bios_serial": "TEXT",
    "cpu_model": "TEXT",
    "cpu_cores": "INTEGER",
    "memory_total_mb": "INTEGER",
    "disk_total_gb": "INTEGER",
    "ip_address": "TEXT",
    "ipv4_address": "TEXT",
    "ipv6_address": "TEXT",
    "mac_address": "TEXT",
    "fqdn": "TEXT",
    "domain": "TEXT",
    "api_key_hash": "TEXT",
    "enrollment_token": "TEXT",
    "enrollment_secret_hash": "TEXT",
    "registration_state": "TEXT NOT NULL DEFAULT 'pending'",
    "enrolled_at": "TIMESTAMP WITH TIME ZONE",
    "approved": "BOOLEAN NOT NULL DEFAULT false",
    "approved_by": "UUID",
    "approved_at": "TIMESTAMP WITH TIME ZONE",
    "trusted": "BOOLEAN NOT NULL DEFAULT false",
    "trust_level": "TEXT NOT NULL DEFAULT 'trusted'",
    "secret_version": "INTEGER NOT NULL DEFAULT 1",
    "public_key": "TEXT",
    "certificate_thumbprint": "TEXT",
    "status": "TEXT NOT NULL DEFAULT 'offline'",
    "registered_at": "TIMESTAMP WITH TIME ZONE",
    "last_seen": "TIMESTAMP WITH TIME ZONE",
    "last_heartbeat": "TIMESTAMP WITH TIME ZONE",
    "last_checkin": "TIMESTAMP WITH TIME ZONE",
    "heartbeat_interval": "INTEGER NOT NULL DEFAULT 30",
    "poll_interval": "INTEGER NOT NULL DEFAULT 30",
    "last_ip_address": "TEXT",
    "last_logged_on_user": "TEXT",
    "health_score": "INTEGER NOT NULL DEFAULT 100",
    "enabled": "BOOLEAN NOT NULL DEFAULT true",
    "tamper_protection": "BOOLEAN NOT NULL DEFAULT false",
    "quarantined": "BOOLEAN NOT NULL DEFAULT false",
    "revoked": "BOOLEAN NOT NULL DEFAULT false",
    "revoked_at": "TIMESTAMP WITH TIME ZONE",
    "revocation_reason": "TEXT",
    "auto_update": "BOOLEAN NOT NULL DEFAULT true",
    "update_available": "BOOLEAN NOT NULL DEFAULT false",
    "target_version": "TEXT",
    "last_update": "TIMESTAMP WITH TIME ZONE",
    "command_timeout": "INTEGER NOT NULL DEFAULT 300",
    "restart_count": "INTEGER NOT NULL DEFAULT 0",
    "last_error": "TEXT",
    "last_error_at": "TIMESTAMP WITH TIME ZONE",
    "tenant_id": "UUID",
    "device_id": "UUID",
}


def connection():
    url = os.environ["DATABASE_URL"].replace(
        "postgresql+psycopg://", "postgresql://", 1
    )
    return psycopg.connect(url)


def versions():
    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name='alembic_version')"
        )
        if not cur.fetchone()[0]:
            return []
        cur.execute("SELECT version_num FROM alembic_version ORDER BY version_num")
        return [row[0] for row in cur.fetchall()]


def missing_agent_columns():
    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name='agents'
            """
        )
        present = {row[0] for row in cur.fetchall()}
    return sorted(set(REQUIRED_AGENT_COLUMNS) - present)


def reconcile_agent_columns():
    missing = missing_agent_columns()
    if not missing:
        return

    print(f"[reconcile] repairing physical agents schema drift; missing={missing}")
    with connection() as conn, conn.cursor() as cur:
        for name in missing:
            cur.execute(
                f'ALTER TABLE agents ADD COLUMN IF NOT EXISTS "{name}" '
                f'{REQUIRED_AGENT_COLUMNS[name]}'
            )
        conn.commit()


before = versions()
print(f"[reconcile] production alembic state before: {before}")

# A database may already be stamped at TARGET even though the physical schema
# was never upgraded. Repair the actual runtime columns idempotently first.
reconcile_agent_columns()

remaining = missing_agent_columns()
if remaining:
    print(
        f"[reconcile] physical schema repair failed; missing={remaining}",
        file=sys.stderr,
    )
    sys.exit(3)

if versions() != [TARGET]:
    print("[reconcile] stamping verified converged migration graph at authoritative target")
    subprocess.run([sys.executable, "-m", "alembic", "stamp", TARGET], check=True)

after = versions()
print(f"[reconcile] production alembic state after: {after}")
if after != [TARGET]:
    print(f"[reconcile] incomplete reconciliation: state={after}", file=sys.stderr)
    sys.exit(3)

print("[reconcile] verified agents runtime schema columns")
print("[reconcile] SUCCESS")
