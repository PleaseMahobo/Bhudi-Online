"""
serializer.py

Serialization utilities for the schema synchronization subsystem.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .types import ComparisonResult, SchemaInfo


class SchemaSerializer:
    """
    Serialize SchemaInfo and ComparisonResult objects.
    """

    @staticmethod
    def schema(schema: SchemaInfo) -> dict[str, Any]:
        return schema.to_dict()

    @staticmethod
    def comparison(result: ComparisonResult) -> dict[str, Any]:
        return result.to_dict()

    @staticmethod
    def to_json(data: Any, *, indent: int = 2) -> str:
        if hasattr(data, "to_dict"):
            data = data.to_dict()

        return json.dumps(data, indent=indent, sort_keys=True)

    @staticmethod
    def write_json(
        data: Any,
        filename: str | Path,
        *,
        indent: int = 2,
    ) -> None:

        path = Path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)

        path.write_text(
            SchemaSerializer.to_json(
                data,
                indent=indent,
            ),
            encoding="utf-8",
        )

    @staticmethod
    def load_json(
        filename: str | Path,
    ) -> dict:

        return json.loads(
            Path(filename).read_text(
                encoding="utf-8"
            )
        )