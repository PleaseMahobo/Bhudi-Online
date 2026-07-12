"""
drift.py

Calculates schema drift metrics and an overall synchronization score.
"""

from __future__ import annotations

from dataclasses import dataclass

from .types import ComparisonResult


@dataclass(slots=True)
class DriftReport:

    compared_tables: int

    compared_columns: int

    total_differences: int

    health_score: float

    drift_score: float

    identical: bool

    def to_dict(self):

        return DriftReport(
            compared_tables=0,
            compared_columns=0,
            total_differences=total,
            health_score=health,
            drift_score=100 - health,
            identical=(total == 0),
)

class DriftAnalyzer:

    def analyze(
        self,
        comparison: ComparisonResult,
    ) -> DriftReport:

        differences = comparison.differences

        total = len(differences)

        health = 100.0

        if total:
            health = max(
                0,
                100 - (total * 10)
            )

        return DriftReport(
            compared_tables=0,
            compared_columns=0,
            total_differences=total,
            health_score=health,
            drift_score=100 - health,
            identical=(total == 0)
        )

def calculate_drift(
    result: ComparisonResult,
) -> DriftReport:

    return DriftAnalyzer().analyze(result)