from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ColumnInfo:
    name: str
    data_type: str
    nullable: bool
    default: Any = None
    primary_key: bool = False
    unique: bool = False


@dataclass(slots=True)
class ForeignKeyInfo:
    constrained_columns: list[str]
    referred_table: str
    referred_columns: list[str]


@dataclass(slots=True)
class IndexInfo:
    name: str
    columns: list[str]
    unique: bool


@dataclass(slots=True)
class TableInfo:
    name: str
    columns: list[ColumnInfo] = field(default_factory=list)
    foreign_keys: list[ForeignKeyInfo] = field(default_factory=list)
    indexes: list[IndexInfo] = field(default_factory=list)


@dataclass(slots=True)
class SchemaInfo:
    schema: str
    tables: dict[str, TableInfo] = field(default_factory=dict)