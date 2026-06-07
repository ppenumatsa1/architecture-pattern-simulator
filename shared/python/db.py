from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from typing import Generator
from urllib.parse import quote_plus
import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


@dataclass(frozen=True)
class DatabaseSettings:
    dsn: str


@lru_cache(maxsize=1)
def get_database_settings() -> DatabaseSettings:
    dsn = os.getenv("POSTGRES_DSN")
    if dsn:
        return DatabaseSettings(dsn=dsn)

    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = quote_plus(os.getenv("POSTGRES_USER", "postgres"))
    password = quote_plus(os.getenv("POSTGRES_PASSWORD", "postgres"))
    database = os.getenv("POSTGRES_DB", "architecture_simulator")
    return DatabaseSettings(dsn=f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}")


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(
        get_database_settings().dsn,
        future=True,
        pool_pre_ping=True,
        pool_recycle=1800,
    )


SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, class_=Session)


def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a transactional SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
