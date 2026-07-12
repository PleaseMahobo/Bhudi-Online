"""
snapshot.py

Coordinates collection of ORM metadata and the live PostgreSQL schema.

This module is intentionally lightweight. It delegates collection to
MetadataCollector and DatabaseInspector and returns canonical SchemaInfo
objects that can be passed directly into the comparator.

The snapshot layer performs NO comparison and NO database modifications.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.engine import Engine

from .inspector import DatabaseInspector
from .metadata import MetadataCollector
from .types import SchemaInfo


# ============================================================
# Snapshot
# ============================================================


@dataclass(slots=True)
class Snapshot:
    """
    Represents one complete schema snapshot.
    """

    source: str

    captured_at: datetime

    schema: SchemaInfo

    @property
    def table_count(self) -> int:
        return len(self.schema.tables)

    @property
    def column_count(self) -> int:
        return sum(
            len(table.columns)
            for table in self.schema.tables.values()
        )


# ============================================================
# Snapshot Builder
# ============================================================


class SnapshotBuilder:
    """
    Builds ORM and Database snapshots.
    """

    def __init__(self, engine: Engine):

        self.engine = engine

    # --------------------------------------------------------

    def orm_snapshot(self) -> Snapshot:

        collector = MetadataCollector()

        schema = collector.collect()

        schema.generated_at = datetime.now(
            timezone.utc
        ).isoformat()

        return Snapshot(

            source="orm",

            captured_at=datetime.now(timezone.utc),

            schema=schema,

        )

    # --------------------------------------------------------

    def database_snapshot(self) -> Snapshot:

        inspector = DatabaseInspector(self.engine)

        schema = inspector.collect()

        schema.generated_at = datetime.now(
            timezone.utc
        ).isoformat()

        return Snapshot(

            source="database",

            captured_at=datetime.now(timezone.utc),

            schema=schema,

        )

    # --------------------------------------------------------

    def collect(self) -> tuple[Snapshot, Snapshot]:

        """
        Returns

            (
                orm_snapshot,
                database_snapshot,
            )
        """

        return (

            self.orm_snapshot(),

            self.database_snapshot(),

        )


# ============================================================
# Convenience Functions
# ============================================================


def build_orm_snapshot() -> Snapshot:

    """
    Collect ORM metadata only.
    """

    collector = MetadataCollector()

    schema = collector.collect()

    schema.generated_at = datetime.now(
        timezone.utc
    ).isoformat()

    return Snapshot(

        source="orm",

        captured_at=datetime.now(
            timezone.utc
        ),

        schema=schema,

    )


def build_database_snapshot(
    engine: Engine,
) -> Snapshot:

    """
    Collect live PostgreSQL metadata only.
    """

    inspector = DatabaseInspector(engine)

    schema = inspector.collect()

    schema.generated_at = datetime.now(
        timezone.utc
    ).isoformat()

    return Snapshot(

        source="database",

        captured_at=datetime.now(
            timezone.utc
        ),

        schema=schema,

    )


def build_snapshots(
    engine: Engine,
) -> tuple[Snapshot, Snapshot]:

    """
    Convenience wrapper.

    Returns:

        (
            orm_snapshot,
            database_snapshot,
        )
    """

    builder = SnapshotBuilder(engine)

    return builder.collect()