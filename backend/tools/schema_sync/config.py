from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(slots=True)
class SyncConfig:
    database_url: str
    schema: str = "public"
    output_directory: str = "reports/schema"
    snapshot_directory: str = "snapshots/schema"


def load_config() -> SyncConfig:
    load_dotenv()

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set.")

    return SyncConfig(
        database_url=database_url,
        schema=os.getenv("DB_SCHEMA", "public"),
        output_directory=os.getenv(
            "SCHEMA_REPORT_DIRECTORY",
            "reports/schema",
        ),
        snapshot_directory=os.getenv(
            "SCHEMA_SNAPSHOT_DIRECTORY",
            "snapshots/schema",
        ),
    )