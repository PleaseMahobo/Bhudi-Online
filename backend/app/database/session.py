from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings


def normalize_database_url(url: str) -> str:
    """Railway often provides postgres://; SQLAlchemy needs postgresql://."""
    url = (url or "").strip()
    if not url:
        return url
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://") and "+psycopg" not in url and "+psycopg2" not in url:
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def _resolve_database_url() -> str:
    url = normalize_database_url(settings.DATABASE_URL or os.getenv("DATABASE_URL", ""))
    if not url:
        for key in (
            "DATABASE_PRIVATE_URL",
            "POSTGRES_URL",
            "POSTGRESQL_URL",
            "DATABASE_PUBLIC_URL",
        ):
            candidate = normalize_database_url(os.getenv(key, ""))
            if candidate:
                print(f"[db] using {key}")
                return candidate
    if not url:
        repo_root = Path(__file__).resolve().parents[3]
        db_path = repo_root / "bhudi.db"
        fallback = f"sqlite:///{db_path.as_posix()}"
        print(f"[db] DATABASE_URL empty; using local SQLite {fallback}")
        return fallback
    return url


def _allow_sqlite_fallback() -> bool:
    flag = os.getenv("BHUDI_ALLOW_SQLITE_FALLBACK", "").strip().lower()
    if flag in ("1", "true", "yes"):
        return True
    if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_ENVIRONMENT_NAME"):
        return False
    if os.getenv("BHUDI_ENV", "").lower() in ("production", "prod"):
        return False
    return True


def _build_engine(database_url: str):
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
        pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
    )

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print(f"[db] connected dialect={engine.dialect.name}")
        return engine
    except OperationalError as exc:
        print(f"[db] PostgreSQL connection failed: {exc}")
        if not _allow_sqlite_fallback():
            raise RuntimeError(
                "Database unreachable. Check DATABASE_URL on Railway, that the "
                "Postgres service is running, and that the API service is linked "
                f"to it. Underlying error: {exc}"
            ) from exc
        repo_root = Path(__file__).resolve().parents[3]
        fallback_url = f"sqlite:///{(repo_root / 'bhudi.db').as_posix()}"
        print(f"[db] falling back to SQLite at {fallback_url}")
        return create_engine(
            fallback_url,
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )


_url = _resolve_database_url()
_safe = _url
if "@" in _safe:
    try:
        scheme, rest = _safe.split("://", 1)
        creds, hostpart = rest.split("@", 1)
        if ":" in creds:
            user = creds.split(":", 1)[0]
            _safe = f"{scheme}://{user}:***@{hostpart}"
    except Exception:
        _safe = "***"
print(f"[db] resolving url={_safe}")

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


def db_health() -> dict:
    """Return connectivity info for diagnostics (no secrets)."""
    info: dict = {
        "dialect": getattr(engine.dialect, "name", "unknown"),
        "driver": getattr(engine.dialect, "driver", "unknown"),
        "url_scheme": (_url.split("://", 1)[0] if "://" in _url else "unknown"),
        "railway": bool(
            os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_ENVIRONMENT_NAME")
        ),
        "database_url_set": bool(
            (settings.DATABASE_URL or os.getenv("DATABASE_URL") or "").strip()
        ),
    }
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        info["ok"] = True
        info["error"] = None
    except Exception as exc:
        info["ok"] = False
        info["error"] = f"{type(exc).__name__}: {exc}"
    return info
