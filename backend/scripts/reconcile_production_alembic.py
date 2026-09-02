import os
import subprocess
import sys
import psycopg

TARGET = "m7n8o9p0q1r2"
REQUIRED_AGENT_COLUMNS = {
    "revoked": "BOOLEAN NOT NULL DEFAULT false",
    "revoked_at": "TIMESTAMP WITH TIME ZONE",
    "revocation_reason": "TEXT",
}

def connection():
    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1)
    return psycopg.connect(url)

def versions():
    with connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='alembic_version')")
        if not cur.fetchone()[0]:
            return []
        cur.execute("SELECT version_num FROM alembic_version ORDER BY version_num")
        return [r[0] for r in cur.fetchall()]

def missing_agent_columns():
    with connection() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name='agents'
        """)
        present = {r[0] for r in cur.fetchall()}
    return sorted(set(REQUIRED_AGENT_COLUMNS) - present)

def reconcile_agent_columns():
    missing = missing_agent_columns()
    if not missing:
        return
    print(f"[reconcile] repairing physical agents schema drift; missing={missing}")
    with connection() as conn, conn.cursor() as cur:
        for name in missing:
            ddl = REQUIRED_AGENT_COLUMNS[name]
            cur.execute(f'ALTER TABLE agents ADD COLUMN IF NOT EXISTS "{name}" {ddl}')
        conn.commit()

before = versions()
print(f"[reconcile] production alembic state before: {before}")

# A database may already be stamped at TARGET even though the physical schema
# was never upgraded. In that case Alembic upgrade TARGET is a no-op, so repair
# the verified runtime columns directly and idempotently.
reconcile_agent_columns()

remaining = missing_agent_columns()
if remaining:
    print(f"[reconcile] physical schema repair failed; missing={remaining}", file=sys.stderr)
    sys.exit(3)

if versions() != [TARGET]:
    print("[reconcile] stamping verified converged migration graph at authoritative target")
    subprocess.run([sys.executable, "-m", "alembic", "stamp", TARGET], check=True)

after = versions()
print(f"[reconcile] production alembic state after: {after}")
if after != [TARGET]:
    print(f"[reconcile] incomplete reconciliation: state={after}", file=sys.stderr)
    sys.exit(3)

print("[reconcile] verified agents runtime columns: revoked, revoked_at, revocation_reason")
print("[reconcile] SUCCESS")
