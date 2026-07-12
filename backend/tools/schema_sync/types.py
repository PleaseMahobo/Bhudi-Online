"""
types.py

Canonical data structures used by the Bhudi Schema Synchronization
subsystem.

These dataclasses provide a normalized representation of both:

    • SQLAlchemy ORM metadata
    • Live PostgreSQL / Supabase schema

Every other module in this package exchanges information using
these types.

This module contains NO database logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


# ============================================================
# Column
# ============================================================

@dataclass(slots=True)
class ColumnInfo:
    """Represents a database column."""

    name: str
    data_type: str

    nullable: bool = True

    default: str | None = None

    identity: bool = False

    autoincrement: bool = False

    primary_key: bool = False

    unique: bool = False

    comment: str | None = None

    ordinal_position: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================
# Primary Key
# ============================================================

@dataclass(slots=True)
class PrimaryKeyInfo:

    name: str

    columns: list[str] = field(default_factory=list)

    def to_dict(self):

        return asdict(self)


# ============================================================
# Foreign Key
# ============================================================

@dataclass(slots=True)
class ForeignKeyInfo:

    name: str

    constrained_columns: list[str]

    referred_table: str

    referred_columns: list[str]

    on_update: str | None = None

    on_delete: str | None = None

    def to_dict(self):

        return asdict(self)


# ============================================================
# Index
# ============================================================

@dataclass(slots=True)
class IndexInfo:

    name: str

    columns: list[str]

    unique: bool = False

    method: str | None = None

    def to_dict(self):

        return asdict(self)


# ============================================================
# Unique Constraint
# ============================================================

@dataclass(slots=True)
class UniqueConstraintInfo:

    name: str

    columns: list[str]

    def to_dict(self):

        return asdict(self)


# ============================================================
# Check Constraint
# ============================================================

@dataclass(slots=True)
class CheckConstraintInfo:

    name: str

    sqltext: str

    def to_dict(self):

        return asdict(self)

# ============================================================
# PostgreSQL ENUM
# ============================================================

@dataclass(slots=True)
class EnumInfo:
    """Represents a PostgreSQL enum."""

    name: str
    schema: str = "public"
    labels: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================
# Sequence
# ============================================================

@dataclass(slots=True)
class SequenceInfo:
    """Represents a PostgreSQL sequence."""

    name: str
    schema: str = "public"

    data_type: str | None = None

    start_value: int | None = None

    minimum_value: int | None = None

    maximum_value: int | None = None

    increment: int | None = None

    cycle: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================
# Trigger
# ============================================================

@dataclass(slots=True)
class TriggerInfo:
    """Represents a database trigger."""

    name: str

    table: str

    schema: str = "public"

    timing: str | None = None

    events: list[str] = field(default_factory=list)

    function: str | None = None

    enabled: bool = True

    definition: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================
# Function
# ============================================================

@dataclass(slots=True)
class FunctionInfo:
    """Represents a PostgreSQL function."""

    schema: str

    name: str

    language: str | None = None

    return_type: str | None = None

    arguments: str | None = None

    definition: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================
# Extension
# ============================================================

@dataclass(slots=True)
class ExtensionInfo:
    """Represents a PostgreSQL extension."""

    name: str

    version: str | None = None

    schema: str | None = None

    relocatable: bool | None = None

    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================
# Row Level Security Policy
# ============================================================

@dataclass(slots=True)
class PolicyInfo:
    """Represents a PostgreSQL RLS policy."""

    table: str

    name: str

    schema: str = "public"

    permissive: bool = True

    command: str | None = None

    roles: list[str] = field(default_factory=list)

    using_expression: str | None = None

    check_expression: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================
# View
# ============================================================

@dataclass(slots=True)
class ViewInfo:
    """Represents a database view."""

    schema: str

    name: str

    definition: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================
# Materialized View
# ============================================================

@dataclass(slots=True)
class MaterializedViewInfo:
    """Represents a PostgreSQL materialized view."""

    schema: str

    name: str

    definition: str | None = None

    populated: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

        # ============================================================
# Table
# ============================================================

@dataclass(slots=True)
class TableInfo:
    """
    Complete representation of a database table.
    """

    schema: str
    name: str

    columns: dict[str, ColumnInfo] = field(default_factory=dict)

    primary_key: PrimaryKeyInfo | None = None

    foreign_keys: dict[str, ForeignKeyInfo] = field(default_factory=dict)

    indexes: dict[str, IndexInfo] = field(default_factory=dict)

    unique_constraints: dict[str, UniqueConstraintInfo] = field(default_factory=dict)

    check_constraints: dict[str, CheckConstraintInfo] = field(default_factory=dict)

    comment: str | None = None

    owner: str | None = None

    row_count: int | None = None

    def to_dict(self) -> dict:

        return {

            "schema": self.schema,

            "name": self.name,

            "columns": {
                k: v.to_dict()
                for k, v in self.columns.items()
            },

            "primary_key": (
                self.primary_key.to_dict()
                if self.primary_key
                else None
            ),

            "foreign_keys": {
                k: v.to_dict()
                for k, v in self.foreign_keys.items()
            },

            "indexes": {
                k: v.to_dict()
                for k, v in self.indexes.items()
            },

            "unique_constraints": {
                k: v.to_dict()
                for k, v in self.unique_constraints.items()
            },

            "check_constraints": {
                k: v.to_dict()
                for k, v in self.check_constraints.items()
            },

            "comment": self.comment,

            "owner": self.owner,

            "row_count": self.row_count,
        }


# ============================================================
# Schema
# ============================================================

@dataclass(slots=True)
class SchemaInfo:
    """
    Complete PostgreSQL schema snapshot.
    """

    tables: dict[str, TableInfo] = field(default_factory=dict)

    enums: dict[str, EnumInfo] = field(default_factory=dict)

    sequences: dict[str, SequenceInfo] = field(default_factory=dict)

    views: dict[str, ViewInfo] = field(default_factory=dict)

    materialized_views: dict[str, MaterializedViewInfo] = field(default_factory=dict)

    triggers: dict[str, TriggerInfo] = field(default_factory=dict)

    functions: dict[str, FunctionInfo] = field(default_factory=dict)

    extensions: dict[str, ExtensionInfo] = field(default_factory=dict)

    policies: dict[str, PolicyInfo] = field(default_factory=dict)

    generated_at: str | None = None

    def to_dict(self) -> dict:

        return {

            "generated_at": self.generated_at,

            "tables": {
                k: v.to_dict()
                for k, v in self.tables.items()
            },

            "enums": {
                k: v.to_dict()
                for k, v in self.enums.items()
            },

            "sequences": {
                k: v.to_dict()
                for k, v in self.sequences.items()
            },

            "views": {
                k: v.to_dict()
                for k, v in self.views.items()
            },

            "materialized_views": {
                k: v.to_dict()
                for k, v in self.materialized_views.items()
            },

            "triggers": {
                k: v.to_dict()
                for k, v in self.triggers.items()
            },

            "functions": {
                k: v.to_dict()
                for k, v in self.functions.items()
            },

            "extensions": {
                k: v.to_dict()
                for k, v in self.extensions.items()
            },

            "policies": {
                k: v.to_dict()
                for k, v in self.policies.items()
            },
        }


# ============================================================
# Difference
# ============================================================

@dataclass(slots=True)
class Difference:
    """
    Single schema difference.
    """

    category: str

    object_name: str

    property_name: str

    source: Any

    target: Any

    severity: str = "warning"

    def to_dict(self) -> dict:

        return asdict(self)


# ============================================================
# Comparison Result
# ============================================================

@dataclass(slots=True)
class ComparisonResult:
    """
    Result of comparing ORM metadata with the database.
    """

    differences: list[Difference] = field(default_factory=list)

    compared_tables: int = 0

    compared_columns: int = 0

    identical: bool = True

    def add(self, difference: Difference) -> None:

        self.differences.append(difference)

        self.identical = False

    @property
    def total_differences(self) -> int:

        return len(self.differences)

    def to_dict(self) -> dict:

        return {

            "identical": self.identical,

            "compared_tables": self.compared_tables,

            "compared_columns": self.compared_columns,

            "total_differences": self.total_differences,

            "differences": [
                d.to_dict()
                for d in self.differences
            ],
        }


# ============================================================
# Helpers
# ============================================================

def as_dictionary(value: Any) -> Any:
    """
    Convert any synchronization object into a JSON-safe structure.
    """

    if hasattr(value, "to_dict"):
        return value.to_dict()

    if isinstance(value, dict):
        return {
            k: as_dictionary(v)
            for k, v in value.items()
        }

    if isinstance(value, list):
        return [
            as_dictionary(v)
            for v in value
        ]

    return value
