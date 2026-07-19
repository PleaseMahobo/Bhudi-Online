from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


engine = create_engine(

    settings.DATABASE_URL,

    future=True,

    pool_pre_ping=True,

    pool_size=10,

    max_overflow=20,

)


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