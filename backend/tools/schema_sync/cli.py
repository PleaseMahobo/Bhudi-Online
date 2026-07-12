"""
Production CLI for the Schema Synchronization utility.
"""

from __future__ import annotations

import argparse
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine

from .sync import SchemaSynchronizer


VERSION = "1.0.0"


def build_parser():

    parser = argparse.ArgumentParser(
        prog="schema-sync",
        description="Bhudi Schema Synchronization Utility",
    )

    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version",
    )

    parser.add_argument(
        "--output",
        default="reports/schema",
        help="Report directory",
    )

    return parser


def main():

    parser = build_parser()

    args = parser.parse_args()

    if args.version:
        print(VERSION)
        return

    load_dotenv()

    engine = create_engine(
        os.environ["DATABASE_URL"]
    )

    synchronizer = SchemaSynchronizer(engine)

    result = synchronizer.run(
        output_directory=args.output
    )

    print()
    print("=" * 70)
    print("Bhudi Schema Synchronization")
    print("=" * 70)

    print(
        f"Tables      : {result.comparison.compared_tables}"
    )

    print(
        f"Columns     : {result.comparison.compared_columns}"
    )

    print(
        f"Differences : {result.comparison.total_differences}"
    )

    print(
        f"Health      : {result.drift.health_score:.2f}%"
    )

    print(
        f"Drift       : {result.drift.drift_score:.2f}%"
    )

    print()

    print("Reports written to:")

    print(args.output)


if __name__ == "__main__":
    main()