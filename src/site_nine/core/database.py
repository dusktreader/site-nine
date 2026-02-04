"""Database management for site-nine"""

from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker


class Database:
    """Database manager for site-nine project data"""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        # Enable foreign key constraints for SQLite
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            poolclass=None,  # Disable connection pooling to ensure PRAGMA is set
        )
        # Set foreign keys pragma on every connection
        from sqlalchemy import event

        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        self.SessionLocal = sessionmaker(bind=self.engine)

    def initialize_schema(self) -> None:
        """Initialize database schema from SQL file"""
        schema_path = Path(__file__).parent.parent / "templates" / "schema.sql"

        with open(schema_path) as f:
            schema_sql = f.read()

        # Use raw connection for executescript (handles triggers properly)
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        try:
            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys = ON")
            conn.executescript(schema_sql)
            conn.commit()
        finally:
            conn.close()

    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()

    def execute_query(self, query: str, params: dict[str, Any] | None = None) -> list[dict]:
        """Execute raw SQL query and return results"""
        with self.engine.begin() as conn:  # Use begin() for automatic commit
            result = conn.execute(text(query), params or {})
            return [dict(row._mapping) for row in result]

    def execute_update(self, query: str, params: dict[str, Any] | None = None) -> None:
        """Execute update/insert/delete query"""
        with self.engine.begin() as conn:  # Use begin() for automatic commit
            conn.execute(text(query), params or {})

    def execute_insert(self, query: str, params: dict[str, Any] | None = None) -> int:
        """Execute insert query and return last inserted row ID"""
        with self.engine.begin() as conn:  # Use begin() for automatic commit
            result = conn.execute(text(query), params or {})
            return result.lastrowid
