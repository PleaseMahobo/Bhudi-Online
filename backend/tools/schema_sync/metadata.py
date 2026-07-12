"""
metadata.py

Collects SQLAlchemy ORM metadata and converts it into the
canonical SchemaInfo model used by the synchronization utility.

No database access occurs here.

This module inspects SQLAlchemy metadata only.
"""

from __future__ import annotations

import app.models

from sqlalchemy import MetaData
from sqlalchemy.sql.schema import Table

from app.database.base import Base

from .types import (
    SchemaInfo,
    TableInfo,
    ColumnInfo,
    PrimaryKeyInfo,
    ForeignKeyInfo,
    IndexInfo,
    UniqueConstraintInfo,
    CheckConstraintInfo,
)


class MetadataCollector:
    """
    Converts SQLAlchemy metadata into SchemaInfo.
    """

    def __init__(self, metadata: MetaData | None = None):

        self.metadata = metadata or Base.metadata

    ##################################################################

    def collect(self) -> SchemaInfo:

        schema = SchemaInfo()

        for table in self.metadata.sorted_tables:

            schema.tables[table.name] = self._table(table)

        return schema

    ##################################################################

    def _table(
        self,
        table: Table,
    ) -> TableInfo:

        info = TableInfo(

            schema=table.schema or "public",

            name=table.name,

        )

        ##################################################################
        # Columns
        ##################################################################

        for position, column in enumerate(table.columns, start=1):

            info.columns[column.name] = ColumnInfo(

                name=column.name,

                data_type=str(column.type),

                nullable=column.nullable,

                default=(
                    str(column.default.arg)
                    if column.default is not None
                    else None
                ),

                identity=getattr(
                    column,
                    "identity",
                    None,
                )
                is not None,

                autoincrement=bool(
                    column.autoincrement
                ),

                primary_key=column.primary_key,

                unique=bool(column.unique),

                ordinal_position=position,

            )

        ##################################################################
        # Primary Key
        ##################################################################

        if table.primary_key:

            info.primary_key = PrimaryKeyInfo(

                name=f"{table.name}_pkey",

                columns=[

                    c.name

                    for c in table.primary_key.columns

                ],

            )

        ##################################################################
        # Foreign Keys
        ##################################################################

        for fk in table.foreign_key_constraints:

            info.foreign_keys[fk.name] = ForeignKeyInfo(

                name=fk.name,

                constrained_columns=[
                    c.parent.name
                    for c in fk.elements
                ],

                referred_table=fk.referred_table.name,

                referred_columns=[
                    c.column.name
                    for c in fk.elements
                ],

                on_delete=fk.ondelete,

                on_update=fk.onupdate,

            )

        ##################################################################
        # Indexes
        ##################################################################

        for idx in table.indexes:

            info.indexes[idx.name] = IndexInfo(

                name=idx.name,

                columns=[
                    c.name
                    for c in idx.columns
                ],

                unique=idx.unique,

            )

        ##################################################################
        # Unique Constraints
        ##################################################################

        for constraint in table.constraints:

            if constraint.__class__.__name__ != "UniqueConstraint":
                continue

            name = constraint.name or "_unnamed_unique"

            info.unique_constraints[name] = (

                UniqueConstraintInfo(

                    name=name,

                    columns=[
                        c.name
                        for c in constraint.columns
                    ],

                )

            )

        ##################################################################
        # Check Constraints
        ##################################################################

        for constraint in table.constraints:

            if constraint.__class__.__name__ != "CheckConstraint":
                continue

            name = constraint.name or "_unnamed_check"

            info.check_constraints[name] = (

                CheckConstraintInfo(

                    name=name,

                    sqltext=str(
                        constraint.sqltext
                    ),

                )

            )

        return info

    ##################################################################

    @staticmethod
    def metadata() -> MetaData:

        return Base.metadata

    ##################################################################

    @staticmethod
    def table_names():

        return sorted(

            Base.metadata.tables.keys()

        )

    ##################################################################

    @staticmethod
    def table_count():

        return len(

            Base.metadata.tables

        )