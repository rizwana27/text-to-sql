# INTERN NOTE: Factory pattern for database engine creation
# This lets us swap between SQLite (dev) and PostgreSQL (prod)
# by only changing the DATABASE_URL env var. The application
# code never needs to know which database it's talking to.
# SQLite needs special args (check_same_thread, StaticPool) because
# FastAPI is async and SQLite isn't thread-safe by default.
# PostgreSQL uses the default connection pool which handles concurrency natively.

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import os


def get_engine() -> Engine:
    """Create and return a SQLAlchemy engine based on DATABASE_URL env var."""
    url = os.getenv("DATABASE_URL", "sqlite:///./data/olist.db")
    if url.startswith("sqlite"):
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(url)


def get_session() -> Session:
    """Create and return a new SQLAlchemy session."""
    engine = get_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()
