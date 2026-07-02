from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./bhudi_rmm.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# =========================
# SQLALCHEMY (LOCAL DB)
# =========================

DATABASE_URL = "sqlite:///./bhudi_rmm.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

# =========================
# SUPABASE (CLOUD LAYER)
# =========================

_supabase_client = None

def get_supabase():
    global _supabase_client

    if _supabase_client:
        return _supabase_client

    from supabase import create_client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise Exception("Missing SUPABASE credentials")

    _supabase_client = create_client(url, key)
    return _supabase_client