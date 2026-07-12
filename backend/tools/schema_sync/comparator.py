"""
comparator.py

Compares two SchemaInfo objects and produces a ComparisonResult.

The comparator never modifies either schema. It only records
differences.
"""

from __future__ import annotations

from .types import (
    ComparisonResult,
    Difference,
    SchemaInfo,
    TableInfo,
)


class SchemaComparator:
    """
    Compare ORM metadata with a live PostgreSQL schema.
    """

    def __init__(
        self,
        source: SchemaInfo,
        target: SchemaInfo,
    ):

        self.source = source
        self.target = target

        self.result = ComparisonResult()

    # ==========================================================
    # Public
    # ==========================================================

    def compare(self) -> ComparisonResult:

        self._compare_tables()

        return self.result

    # ==========================================================
    # Table Comparison
    # ==========================================================

    def _compare_tables(self):

        source_tables = set(
            self.source.tables.keys()
        )

        target_tables = set(
            self.target.tables.keys()
        )

        self.result.compared_tables = len(
            source_tables | target_tables
        )

        #
        # Missing tables
        #

        for table_name in sorted(
            source_tables - target_tables
        ):

            self._difference(

                category="table",

                object_name=table_name,

                property_name="exists",

                source=True,

                target=False,

                severity="error",

            )

        #
        # Extra tables
        #

        for table_name in sorted(
            target_tables - source_tables
        ):

            self._difference(

                category="table",

                object_name=table_name,

                property_name="exists",

                source=False,

                target=True,

                severity="warning",

            )

        #
        # Compare common tables
        #

        for table_name in sorted(
            source_tables & target_tables
        ):

            self._compare_single_table(

                self.source.tables[table_name],

                self.target.tables[table_name],

            )

    # ==========================================================

        # ==========================================================

    def _compare_single_table(
        self,
        source: TableInfo,
        target: TableInfo,
    ):

        self._compare_columns(source, target)

        self._compare_primary_key(source, target)

    # ==========================================================
    # Columns
    # ==========================================================

    def _compare_columns(
        self,
        source: TableInfo,
        target: TableInfo,
    ):

        source_columns = set(source.columns.keys())

        target_columns = set(target.columns.keys())

        self.result.compared_columns += len(
            source_columns | target_columns
        )

        #
        # Missing columns
        #

        for column_name in sorted(
            source_columns - target_columns
        ):

            self._difference(

                category="column",

                object_name=f"{source.name}.{column_name}",

                property_name="exists",

                source=True,

                target=False,

                severity="error",

            )

        #
        # Extra columns
        #

        for column_name in sorted(
            target_columns - source_columns
        ):

            self._difference(

                category="column",

                object_name=f"{source.name}.{column_name}",

                property_name="exists",

                source=False,

                target=True,

                severity="warning",

            )

        #
        # Compare common columns
        #

        for column_name in sorted(
            source_columns & target_columns
        ):

            s = source.columns[column_name]

            t = target.columns[column_name]

            #
            # Data type
            #

            if str(s.data_type).lower() != str(t.data_type).lower():

                self._difference(

                    category="column",

                    object_name=f"{source.name}.{column_name}",

                    property_name="data_type",

                    source=s.data_type,

                    target=t.data_type,

                )

            #
            # Nullable
            #

            if s.nullable != t.nullable:

                self._difference(

                    category="column",

                    object_name=f"{source.name}.{column_name}",

                    property_name="nullable",

                    source=s.nullable,

                    target=t.nullable,

                )

            #
            # Default
            #

            if (s.default or "") != (t.default or ""):

                self._difference(

                    category="column",

                    object_name=f"{source.name}.{column_name}",

                    property_name="default",

                    source=s.default,

                    target=t.default,

                )

            #
            # Identity
            #

            if s.identity != t.identity:

                self._difference(

                    category="column",

                    object_name=f"{source.name}.{column_name}",

                    property_name="identity",

                    source=s.identity,

                    target=t.identity,

                )

            #
            # Autoincrement
            #

            if s.autoincrement != t.autoincrement:

                self._difference(

                    category="column",

                    object_name=f"{source.name}.{column_name}",

                    property_name="autoincrement",

                    source=s.autoincrement,

                    target=t.autoincrement,

                )

    # ==========================================================
    # Primary Keys
    # ==========================================================

    def _compare_primary_key(
        self,
        source: TableInfo,
        target: TableInfo,
    ):

        if source.primary_key is None and target.primary_key is None:
            return

        if source.primary_key is None:

            self._difference(

                category="primary_key",

                object_name=source.name,

                property_name="exists",

                source=False,

                target=True,

            )

            return

        if target.primary_key is None:

            self._difference(

                category="primary_key",

                object_name=source.name,

                property_name="exists",

                source=True,

                target=False,

            )

            return

        if (
            source.primary_key.columns
            != target.primary_key.columns
        ):

            self._difference(

                category="primary_key",

                object_name=source.name,

                property_name="columns",

                source=source.primary_key.columns,

                target=target.primary_key.columns,

            )

    # ==========================================================
    # Helpers
    # ==========================================================

    def _difference(

        self,

        category: str,

        object_name: str,

        property_name: str,

        source,

        target,

        severity="warning",

    ):

        self.result.add(

            Difference(

                category=category,

                object_name=object_name,

                property_name=property_name,

                source=source,

                target=target,

                severity=severity,

            )

        )


# ==============================================================
# Convenience Function
# ==============================================================


def compare(
    source: SchemaInfo,
    target: SchemaInfo,
) -> ComparisonResult:

    return SchemaComparator(
        source,
        target,
    ).compare()