"""
inspector.py

Reads database schema metadata and converts it
into a normalized schema representation.
"""

from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.engine import Engine


class SchemaInspector:

    def __init__(self, engine: Engine):
        self.engine = engine

    def inspect(self) -> dict:
        """
        Return database schema structure.
        """

        inspector = inspect(self.engine)

        schema = {}

        tables = inspector.get_table_names()

        for table in tables:

            columns = {}

            for column in inspector.get_columns(table):
                columns[column["name"]] = {
                    "type": str(column["type"]),
                    "nullable": column["nullable"],
                }

            schema[table] = columns

        return schema