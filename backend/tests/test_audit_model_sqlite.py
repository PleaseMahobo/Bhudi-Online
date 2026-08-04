from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core import bootstrap


def test_audit_trail_creates_on_sqlite() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    bootstrap.engine = engine
    bootstrap.SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    result = bootstrap.initialize_database()

    assert result["status"] == "initialized"
