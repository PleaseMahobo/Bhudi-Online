"""
Loads the SQLAlchemy ORM metadata into an in-memory SchemaDefinition.

This module never connects to the live database.

It only reflects the application's SQLAlchemy models.
"""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    PrimaryKeyConstraint,
    UniqueConstraint,
)
from sqlalchemy.sql.schema import Table

import app.models  # noqa: F401

from app.database.base import Base

from .types import (
    CheckConstraintDefinition,
    ColumnDefinition,
    ForeignKeyDefinition,
    IndexDefinition,
    SchemaDefinition,
    TableDefinition,
    UniqueConstraintDefinition,
)


class MetadataLoader:
    """
    Converts SQLAlchemy metadata into SchemaDefinition.
    """

    def __init__(self):
        self.metadata = Base.metadata

    def load(self) -> SchemaDefinition:
        schema = SchemaDefinition()

        for table in self.metadata.sorted_tables:
            schema.tables[table.name] = self._load_table(table)

        return schema

    def _load_table(self, table: Table) -> TableDefinition:
        definition = TableDefinition(
            name=table.name,
            schema=table.schema or "public",
        )

        for column in table.columns:

            definition.columns[column.name] = ColumnDefinition(
                table=table.name,
                name=column.name,
                data_type=str(column.type),
                nullable=column.nullable,
                default=self._column_default(column),
                primary_key=column.primary_key,
                unique=bool(column.unique),
                identity=getattr(column, "identity", None) is not None,
                comment=column.comment,
            )

        for constraint in table.constraints:

            if isinstance(constraint, PrimaryKeyConstraint):
                definition.primary_key = [
                    c.name for c in constraint.columns
                ]

            elif isinstance(
                constraint,
                ForeignKeyConstraint,
            ):
                definition.foreign_keys.append(
                    ForeignKeyDefinition(
                        table=table.name,
                        name=constraint.name or "",
                        constrained_columns=[
                            c.parent.name
                            for c in constraint.elements
                        ],
                        referred_table=list(
                            constraint.elements
                        )[0].column.table.name,
                        referred_columns=[
                            c.column.name
                            for c in constraint.elements
                        ],
                        on_delete=constraint.ondelete,
                        on_update=constraint.onupdate,
                    )
                )

            elif isinstance(
                constraint,
                UniqueConstraint,
            ):
                definition.unique_constraints.append(
                    UniqueConstraintDefinition(
                        table=table.name,
                        name=constraint.name or "",
                        columns=[
                            c.name
                            for c in constraint.columns
                        ],
                    )
                )

            elif isinstance(
                constraint,
                CheckConstraint,
            ):
                definition.check_constraints.append(
                    CheckConstraintDefinition(
                        table=table.name,
                        name=constraint.name or "",
                        sqltext=str(constraint.sqltext),
                    )
                )

        for idx in table.indexes:

            definition.indexes.append(
                self._load_index(
                    table.name,
                    idx,
                )
            )

        return definition

    def _load_index(
        self,
        table_name: str,
        index: Index,
    ) -> IndexDefinition:

        return IndexDefinition(
            table=table_name,
            name=index.name,
            columns=[
                c.name
                for c in index.columns
            ],
            unique=index.unique,
            expression=str(index.expressions)
            if index.expressions
            else None,
        )

    @staticmethod
    def _column_default(column):

        if column.default is None:
            return None

        try:
            if column.default.arg is None:
                return None

            return str(column.default.arg)

        except Exception:
            return str(column.default)