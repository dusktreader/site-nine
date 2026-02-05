"""Tests for database module"""

from pathlib import Path

from site_nine.core.database import Database


def test_database_init(temp_dir: Path):
    """Test database initialization"""
    db_path = temp_dir / "test.db"
    db = Database(db_path)
    assert db.db_path == db_path
    assert db.engine is not None


def test_initialize_schema(test_db: Database):
    """Test schema initialization"""
    # Check that tables exist
    result = test_db.execute_query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    table_names = [row["name"] for row in result]

    assert "daemon_names" in table_names
    assert "agents" in table_names
    assert "tasks" in table_names
    assert "task_dependencies" in table_names


def test_execute_query(test_db: Database):
    """Test query execution"""
    # Insert a daemon name with valid role
    test_db.execute_update(
        """
        INSERT INTO daemon_names (name, role, mythology, description, usage_count)
        VALUES (:name, :role, :mythology, :description, :usage_count)
        """,
        {
            "name": "test-daemon",
            "role": "Administrator",
            "mythology": "test",
            "description": "Test daemon",
            "usage_count": 0,
        },
    )

    # Query it back
    result = test_db.execute_query(
        "SELECT * FROM daemon_names WHERE name = :name",
        {"name": "test-daemon"},
    )

    assert len(result) == 1
    assert result[0]["name"] == "test-daemon"
    assert result[0]["role"] == "Administrator"


def test_execute_update(test_db: Database):
    """Test update execution"""
    # Insert a daemon name with valid role
    test_db.execute_update(
        """
        INSERT INTO daemon_names (name, role, mythology, description, usage_count)
        VALUES ('update-test', 'Engineer', 'test', 'Test', 0)
        """
    )

    # Update it
    test_db.execute_update("UPDATE daemon_names SET usage_count = 5 WHERE name = 'update-test'")

    # Verify update
    result = test_db.execute_query("SELECT usage_count FROM daemon_names WHERE name = 'update-test'")
    assert result[0]["usage_count"] == 5


def test_get_session(temp_dir):
    """Test getting a database session"""

    from site_nine.core.database import Database

    db_path = temp_dir / "test.db"
    db = Database(db_path)
    db.initialize_schema()

    session = db.get_session()

    # Should return a session object
    assert session is not None
    # Should be able to close it
    session.close()
