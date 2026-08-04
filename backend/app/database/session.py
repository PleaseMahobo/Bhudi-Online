from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings


def _resolve_database_url() -> str:
    url = (settings.DATABASE_URL or "").strip()
    if not url:
        repo_root = Path(__file__).resolve().parents[3]
        db_path = repo_root / "bhudi.db"
        return f"sqlite:///{db_path.as_posix()}"
    return url


def _build_engine(database_url: str):
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        if database_url.endswith(":memory:") or ":memory:" in database_url:
            return create_engine(
                database_url,
                future=True,
                connect_args=connect_args,
                poolclass=StaticPool,
            )
        return create_engine(
            database_url,
            future=True,
            connect_args=connect_args,
        )

    engine = create_engine(
        database_url,
        future=True,
        pool_pre_ping=True,
    )

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return engine
    except OperationalError as exc:
        repo_root = Path(__file__).resolve().parents[3]
        fallback_url = f"sqlite:///{(repo_root / 'bhudi.db').as_posix()}"
        print(f"[db] PostgreSQL unavailable ({exc}); falling back to SQLite at {fallback_url}")
        return create_engine(
            fallback_url,
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )


_url = _resolve_database_url()
engine = _build_engine(_url)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
