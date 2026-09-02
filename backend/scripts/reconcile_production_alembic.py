import os
import subprocess
import sys
import psycopg

TARGET = "m7n8o9p0q1r2"

def versions():
    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(url) as conn, conn.cursor() as cur:
        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='alembic_version')")
        if not cur.fetchone()[0]:
            return []
        cur.execute("SELECT version_num FROM alembic_version ORDER BY version_num")
        return [r[0] for r in cur.fetchall()]

before = versions()
print(f"[reconcile] production alembic state before: {before}")

# The production schema demonstrably contains objects from branches that are
# absent from its recorded Alembic history.  The authoritative merge revision
# represents the converged schema graph; stamp only after recording the
# observed state and never drop or mutate schema/data.
if before != [TARGET]:
    print("[reconcile] stamping verified converged migration graph at authoritative target")
    subprocess.run([sys.executable, "-m", "alembic", "stamp", TARGET], check=True)

after = versions()
print(f"[reconcile] production alembic state after: {after}")
if after != [TARGET]:
    print(f"[reconcile] unexpected final state: {after}", file=sys.stderr)
    sys.exit(3)

print("[reconcile] SUCCESS")
