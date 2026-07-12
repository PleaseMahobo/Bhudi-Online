"""
inspector.py

Live PostgreSQL / Supabase schema inspector.

This module performs READ-ONLY inspection of the connected
database and converts the results into the canonical SchemaInfo
representation used throughout the synchronization subsystem.
"""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from .types import (
    SchemaInfo,
    TableInfo,
    ColumnInfo,
    PrimaryKeyInfo,
    ForeignKeyInfo,
    IndexInfo,
    UniqueConstraintInfo,
)


class DatabaseInspector:
    """
    Read-only PostgreSQL schema inspector.
    """

    def __init__(self, engine: Engine):

        self.engine = engine
        self.inspector = inspect(engine)

    # ==========================================================
    # Public
    # ==========================================================

    def collect(self) -> SchemaInfo:

        schema = SchemaInfo()

        for table_name in self.inspector.get_table_names(schema="public"):

            schema.tables[table_name] = self._inspect_table(
                table_name
            )

        self._load_extensions(schema)
        self._load_views(schema)
        self._load_sequences(schema)

        return schema

    # ==========================================================
    # Tables
    # ==========================================================

    def _inspect_table(self, table_name: str) -> TableInfo:

        table = TableInfo(
            schema="public",
            name=table_name,
        )

        # ---------------- Columns ----------------

        for position, column in enumerate(
            self.inspector.get_columns(table_name),
            start=1,
        ):

            table.columns[column["name"]] = ColumnInfo(

                name=column["name"],

                data_type=str(column["type"]),

                nullable=column.get("nullable", True),

                default=(
                    str(column.get("default"))
                    if column.get("default") is not None
                    else None
                ),

                identity=bool(
                    column.get("identity")
                ),

                autoincrement=bool(
                    column.get("autoincrement")
                ),

                ordinal_position=position,

            )

        # ---------------- Primary Key ----------------

        pk = self.inspector.get_pk_constraint(table_name)

        if pk and pk.get("constrained_columns"):

            table.primary_key = PrimaryKeyInfo(

                name=pk.get("name") or f"{table_name}_pkey",

                columns=pk["constrained_columns"],

            )

        # ---------------- Foreign Keys ----------------

        for fk in self.inspector.get_foreign_keys(
            table_name
        ):

            name = (
                fk.get("name")
                or "_unnamed_fk"
            )

            table.foreign_keys[name] = ForeignKeyInfo(

                name=name,

                constrained_columns=fk.get(
                    "constrained_columns",
                    [],
                ),

                referred_table=fk.get(
                    "referred_table"
                ),

                referred_columns=fk.get(
                    "referred_columns",
                    [],
                ),

            )

        # ---------------- Indexes ----------------

        for idx in self.inspector.get_indexes(
            table_name
        ):

            table.indexes[idx["name"]] = IndexInfo(

                name=idx["name"],

                columns=idx["column_names"],

                unique=idx.get("unique", False),

            )

        # ---------------- Unique Constraints ----------------

        for uc in self.inspector.get_unique_constraints(
            table_name
        ):

            name = (
                uc.get("name")
                or "_unnamed_unique"
            )

            table.unique_constraints[name] = (

                UniqueConstraintInfo(

                    name=name,

                    columns=uc.get(
                        "column_names",
                        [],
                    ),

                )

            )

        return table

    # ==========================================================
    # Extensions
    # ==========================================================

    def _load_extensions(
        self,
        schema: SchemaInfo,
    ):

        sql = text(
            """
            SELECT
                extname,
                extversion
            FROM pg_extension
            ORDER BY extname
            """
        )

        with self.engine.connect() as conn:

            for row in conn.execute(sql):

                schema.extensions[row.extname] = {

                    "name": row.extname,

                    "version": row.extversion,

                }

    # ==========================================================
    # Views
    # ==========================================================

    def _load_views(
        self,
        schema: SchemaInfo,
    ):

        sql = text(
            """
            SELECT
                table_name
            FROM information_schema.views
            WHERE table_schema='public'
            """
        )

        with self.engine.connect() as conn:

            for row in conn.execute(sql):

                schema.views[row.table_name] = {

                    "name": row.table_name
                }

    # ==========================================================
    # Sequences
    # ==========================================================

    def _load_sequences(
        self,
        schema: SchemaInfo,
    ):

        sql = text(
            """
            SELECT sequencename
            FROM pg_sequences
            WHERE schemaname='public'
            """
        )

        with self.engine.connect() as conn:

            for row in conn.execute(sql):

                schema.sequences[
                    row.sequencename
                ] = {

                    "name": row.sequencename
                }