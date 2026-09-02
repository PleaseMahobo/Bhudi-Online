import os
import subprocess
import sys
import psycopg

TARGET = "m7n8o9p0q1r2"

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
    required = {"revoked", "revoked_at", "revocation_reason"}
    with connection() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name='agents'
        """)
        present = {r[0] for r in cur.fetchall()}
    return sorted(required - present)

before = versions()
print(f"[reconcile] production alembic state before: {before}")
missing = missing_agent_columns()
if missing:
    print(f"[reconcile] applying authoritative agents schema reconciliation; missing={missing}")
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", TARGET], check=True)
else:
    print("[reconcile] agents schema already contains required runtime columns")
    if before != [TARGET]:
        print("[reconcile] stamping verified converged migration graph at authoritative target")
        subprocess.run([sys.executable, "-m", "alembic", "stamp", TARGET], check=True)

after = versions()
remaining = missing_agent_columns()
print(f"[reconcile] production alembic state after: {after}")
if after != [TARGET] or remaining:
    print(f"[reconcile] incomplete reconciliation: state={after}, missing_agent_columns={remaining}", file=sys.stderr)
    sys.exit(3)
print("[reconcile] SUCCESS")
