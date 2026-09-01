import os
import psycopg

conn = psycopg.connect(os.environ["DATABASE_URL"])
try:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'alembic_version'
            )
        """)
        has_version = cur.fetchone()[0]
        print(f"ALEMBIC_VERSION_TABLE={has_version}")

        if has_version:
            cur.execute("SELECT version_num FROM alembic_version ORDER BY version_num")
            versions = [row[0] for row in cur.fetchall()]
            print(f"ALEMBIC_VERSION_ROWS={versions}")

        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cur.fetchall()]
        print(f"PUBLIC_TABLE_COUNT={len(tables)}")
        print("PUBLIC_TABLES=" + ",".join(tables))

        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'agents'
            ORDER BY ordinal_position
        """)
        agent_columns = [row[0] for row in cur.fetchall()]
        print("AGENTS_COLUMNS=" + ",".join(agent_columns))
finally:
    conn.close()
