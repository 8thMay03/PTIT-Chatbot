from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.models import Base


def get_engine_options(database_url: str | None = None) -> dict[str, Any]:
    url = database_url or settings.database_url
    options: dict[str, Any] = {
        "future": True,
        "echo": settings.db_echo,
    }
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    else:
        options["pool_size"] = settings.db_pool_size
        options["max_overflow"] = settings.db_max_overflow
        options["pool_timeout"] = settings.db_pool_timeout
        options["pool_recycle"] = settings.db_pool_recycle
        options["pool_pre_ping"] = True
    return options


def create_app_engine(database_url: str | None = None) -> Engine:
    url = database_url or settings.database_url
    return create_engine(url, **get_engine_options(url))


engine = create_app_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


import sqlite3

@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()



def check_db_health() -> dict[str, Any]:
    """Execute a lightweight query to check database connectivity."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": "connected",
            "dialect": engine.dialect.name,
        }
    except Exception as exc:
        return {
            "status": "error",
            "database": "disconnected",
            "dialect": engine.dialect.name,
            "error": str(exc),
        }


def init_db() -> None:
    if settings.database_url.startswith("sqlite"):
        settings.database_path.parent.mkdir(parents=True, exist_ok=True)
        Base.metadata.create_all(bind=engine)
    else:
        try:
            Base.metadata.create_all(bind=engine)
        except Exception as exc:
            import logging
            logging.getLogger("app.db").warning("Could not auto-create tables during init_db: %s", exc)



def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session

