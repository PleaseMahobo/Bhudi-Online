"""
Smoke test for the Schema Synchronization subsystem.

Nothing is modified in the database.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

from tools.schema_sync.snapshot import SnapshotBuilder
from tools.schema_sync.comparator import SchemaComparator
from tools.schema_sync.drift import calculate_drift
from tools.schema_sync.report import ReportGenerator


def main():

    load_dotenv()

    database_url = os.environ["DATABASE_URL"]

    engine = create_engine(database_url)

    print("=" * 70)
    print("Bhudi Schema Synchronization Smoke Test")
    print("=" * 70)

    builder = SnapshotBuilder(engine)

    print("\nCollecting ORM snapshot...")
    orm = builder.orm_snapshot()

    print(f"ORM tables      : {orm.table_count}")
    print(f"ORM columns     : {orm.column_count}")

    print("\nCollecting Database snapshot...")
    db = builder.database_snapshot()

    print(f"Database tables : {db.table_count}")
    print(f"Database columns: {db.column_count}")

    print("\nRunning comparison...")

    comparator = SchemaComparator(
        orm.schema,
        db.schema,
    )

    result = comparator.compare()

    print("\nComparison complete.")

    print(f"Compared tables : {result.compared_tables}")
    print(f"Compared columns: {result.compared_columns}")
    print(f"Differences     : {result.total_differences}")
    print(f"Identical       : {result.identical}")

    #
    # Drift
    #

    drift = calculate_drift(result)

    print()
    print("=" * 70)
    print("Schema Health")
    print("=" * 70)

    print(f"Health Score : {drift.health_score:.2f}%")
    print(f"Drift Score  : {drift.drift_score:.2f}%")

    #
    # Reports
    #

    report = ReportGenerator(result)

    report.print_summary()

    reports = Path("reports/schema")
    reports.mkdir(exist_ok=True)

    report.save_json(
        reports / "schema-report.json"
    )

    report.save_markdown(
        reports / "schema-report.md"
    )

    print()
    print("Reports written to:")
    print(reports.resolve())

    print("\nDone.")


if __name__ == "__main__":
    main()