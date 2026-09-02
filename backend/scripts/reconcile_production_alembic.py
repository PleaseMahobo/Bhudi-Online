import os
import subprocess
import sys

import psycopg

BASELINE = "l6m7n8o9p0q1"
TARGET = "m7n8o9p0q1r2"


def versions():
    url = os.environ["DATABASE_URL"].replace(
        "postgresql+psycopg://", "postgresql://", 1
    )
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
    # An unversioned existing schema is the only state that needs an explicit
    # reconciliation baseline. Never overwrite a real recorded revision.
    print(f"[reconcile] stamping unversioned production schema at {BASELINE}")
    subprocess.run(
        [sys.executable, "-m", "alembic", "stamp", BASELINE],
        check=True,
    )
elif before == [TARGET]:
    print("[reconcile] production database is already at target revision")
    print("[reconcile] SUCCESS")
    sys.exit(0)
else:
    # Preserve the authoritative production history and let Alembic calculate
    # the valid graph path to the single merged head.
    print("[reconcile] preserving recorded production history and upgrading forward")

print("[reconcile] running forward migrations to head")
subprocess.run(
    [sys.executable, "-m", "alembic", "upgrade", "head"],
    check=True,
)

after = versions()
print(f"[reconcile] production alembic state after: {after}")
if after != [TARGET]:
    print(f"[reconcile] unexpected final state: {after}", file=sys.stderr)
    sys.exit(3)

print("[reconcile] SUCCESS")
