import sqlite3
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from site_nine.core.paths import get_package_data_dir


class Database:
    """Database manager for site-nine project data"""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            poolclass=NullPool,
        )

        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        self.SessionLocal = sessionmaker(bind=self.engine)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def close(self) -> None:
        self.engine.dispose()

    def initialize_schema(self) -> None:
        """Initialize database schema from SQL file"""
        schema_path = get_package_data_dir() / "schema.sql"

        with open(schema_path) as f:
            schema_sql = f.read()

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.executescript(schema_sql)
            conn.commit()
        finally:
            conn.close()

    def seed_data(self) -> None:
        """Populate database with seed data"""
        seed_path = get_package_data_dir() / "seed.sql"

        with open(seed_path) as f:
            seed_sql = f.read()

        conn = sqlite3.connect(self.db_path)
        try:
            conn.executescript(seed_sql)
            conn.commit()
        finally:
            conn.close()

    def get_session(self) -> Session:
        return self.SessionLocal()

    def execute_query(self, query: str, params: dict[str, Any] | None = None) -> list[dict]:
        """Execute raw SQL query and return results"""
        with self.engine.begin() as conn:
            result = conn.execute(text(query), params or {})
            return [dict(row._mapping) for row in result]

    def execute_update(self, query: str, params: dict[str, Any] | None = None) -> None:
        """Execute update/insert/delete query"""
        with self.engine.begin() as conn:
            conn.execute(text(query), params or {})

    def execute_insert(self, query: str, params: dict[str, Any] | None = None) -> int:
        """Execute insert query and return last inserted row ID"""
        with self.engine.begin() as conn:
            result = conn.execute(text(query), params or {})
            return result.lastrowid
