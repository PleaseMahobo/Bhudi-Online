"""
report.py

Generates Markdown, JSON and console reports from a ComparisonResult.
"""

from __future__ import annotations

import json
from pathlib import Path
from collections import defaultdict

from .types import ComparisonResult


class ReportGenerator:

    def __init__(self, result: ComparisonResult):

        self.result = result

    # ---------------------------------------------------------

    def grouped(self):

        groups = defaultdict(list)

        for diff in self.result.differences:
            groups[diff.category].append(diff)

        return dict(groups)

    # ---------------------------------------------------------

    def print_summary(self):

        print()
        print("=" * 70)
        print("Schema Drift Summary")
        print("=" * 70)

        print(
            f"Compared tables : {self.result.compared_tables}"
        )

        print(
            f"Compared columns: {self.result.compared_columns}"
        )

        print(
            f"Differences     : {self.result.total_differences}"
        )

        print()

        for category, items in sorted(
            self.grouped().items()
        ):

            print(
                f"{category:<20}{len(items):>5}"
            )

    # ---------------------------------------------------------

    def save_json(
        self,
        path: str | Path,
    ):

        Path(path).write_text(

            json.dumps(
                self.result.to_dict(),
                indent=2,
            )

        )

    # ---------------------------------------------------------

    def save_markdown(
        self,
        path: str | Path,
    ):

        lines = []

        lines.append("# Schema Drift Report")
        lines.append("")

        lines.append(
            f"Total differences: **{self.result.total_differences}**"
        )

        lines.append("")

        for category, items in sorted(
            self.grouped().items()
        ):

            lines.append(f"## {category}")
            lines.append("")

            for diff in items:

                lines.append(
                    f"- **{diff.object_name}** "
                    f"({diff.property_name})"
                )

                lines.append(
                    f"  - ORM: `{diff.source}`"
                )

                lines.append(
                    f"  - DB : `{diff.target}`"
                )

            lines.append("")

        Path(path).write_text(
            "\n".join(lines)
        )