"""
Compatibility layer.

New code should import from:

    app.database.base
    app.database.session

This module exists so older modules continue to work while the
project is migrated to the standardized database package.
"""

from app.database.base import Base
from app.database.session import (
    engine,
    SessionLocal,
    get_db,
)

__all__ = [
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
]