import os
import subprocess
import sys
import psycopg

BASELINE = "l6m7n8o9p0q1"
TARGET = "m7n8o9p0q1r2"

def versions():
    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1)
    conn = psycopg.connect(url)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema='public' AND table_name='alembic_version'
                )
            """)
            if not cur.fetchone()[0]:
                return None
            cur.execute("SELECT version_num FROM alembic_version ORDER BY version_num")
            return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()

before = versions()
print(f"[reconcile] production alembic state before: {before}")

if before is None or before == []:
    print(f"[reconcile] stamping existing production schema at merge baseline {BASELINE}")
    subprocess.run([sys.executable, "-m", "alembic", "stamp", BASELINE], check=True)
elif before == [TARGET]:
    print("[reconcile] production database is already at target revision")
    sys.exit(0)
elif before != [BASELINE]:
    print(f"[reconcile] REFUSING to overwrite unexpected Alembic state: {before}", file=sys.stderr)
    sys.exit(2)
else:
    print(f"[reconcile] merge baseline already present: {BASELINE}")

print("[reconcile] running forward migrations to head")
subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)

after = versions()
print(f"[reconcile] production alembic state after: {after}")
if after != [TARGET]:
    print(f"[reconcile] unexpected final state: {after}", file=sys.stderr)
    sys.exit(3)

print("[reconcile] SUCCESS")
