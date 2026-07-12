"""
synchronizer.py

Coordinates schema comparison, drift analysis,
and synchronization reporting.
"""

from __future__ import annotations

from dataclasses import dataclass

from .drift import DriftAnalyzer, DriftReport
from .types import ComparisonResult


@dataclass(slots=True)
class SyncResult:
    comparison: ComparisonResult
    drift: DriftReport
    synchronized: bool


class SchemaSynchronizer:
    """
    Main schema synchronization coordinator.
    """

    def __init__(self):
        self.drift_analyzer = DriftAnalyzer()

    def compare(
        self,
        source_schema: dict,
        target_schema: dict,
    ) -> ComparisonResult:
        """
        Compare source and target schemas.
        """

        differences = []

        source_tables = set(source_schema.keys())
        target_tables = set(target_schema.keys())

        for table in source_tables - target_tables:
            differences.append(
                {
                    "type": "missing_table",
                    "table": table,
                }
            )

        for table in target_tables - source_tables:
            differences.append(
                {
                    "type": "extra_table",
                    "table": table,
                }
            )

        return ComparisonResult(
            differences=differences
        )

    def analyze(
        self,
        source_schema: dict,
        target_schema: dict,
    ) -> SyncResult:
        """
        Full synchronization analysis.
        """

        comparison = self.compare(
            source_schema,
            target_schema,
        )

        drift = self.drift_analyzer.analyze(
            comparison
        )

        return SyncResult(
            comparison=comparison,
            drift=drift,
            synchronized=(
                drift.total_differences == 0
            ),
        )