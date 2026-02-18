"""Tests for database module"""

from pathlib import Path

from site_nine.core.database import Database


def test_database_init(temp_dir: Path):
    """Test database initialization"""
    db_path = temp_dir / "test.db"
    with Database(db_path) as db:
        assert db.db_path == db_path
        assert db.engine is not None


def test_initialize_schema(test_db: Database):
    """Test schema initialization"""
    # Check that tables exist
    result = test_db.execute_query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    table_names = [row["name"] for row in result]

    assert "personas" in table_names
    assert "missions" in table_names
    assert "tasks" in table_names
    assert "task_dependencies" in table_names


def test_execute_query(test_db: Database):
    """Test query execution"""
    # Insert a persona with valid role
    test_db.execute_update(
        """
        INSERT INTO personas (name, role, mythology, description)
        VALUES (:name, :role, :mythology, :description)
        """,
        {
            "name": "test-query-persona",
            "role": "Administrator",
            "mythology": "test",
            "description": "Test persona",
        },
    )

    # Query it back
    result = test_db.execute_query(
        "SELECT * FROM personas WHERE name = :name",
        {"name": "test-query-persona"},
    )

    assert len(result) == 1
    assert result[0]["name"] == "test-query-persona"
    assert result[0]["role"] == "Administrator"


def test_execute_update(test_db: Database):
    """Test update execution"""
    # Insert a persona with valid role
    test_db.execute_update(
        """
        INSERT INTO personas (name, role, mythology, description)
        VALUES ('update-test', 'Architect', 'test', 'Test')
        """
    )

    # Update it
    test_db.execute_update("UPDATE personas SET description = 'Updated' WHERE name = 'update-test'")

    # Verify update
    result = test_db.execute_query("SELECT description FROM personas WHERE name = 'update-test'")
    assert result[0]["description"] == "Updated"


def test_get_session(temp_dir):
    """Test getting a database session"""

    from site_nine.core.database import Database

    db_path = temp_dir / "test.db"
    with Database(db_path) as db:
        db.initialize_schema()

        session = db.get_session()

        # Should return a session object
        assert session is not None
        # Should be able to close it
        session.close()


def test_execute_insert(test_db: Database):
    """Test insert execution with lastrowid return"""
    # Insert a persona and get the row ID
    row_id = test_db.execute_insert(
        """
        INSERT INTO personas (name, role, mythology, description)
        VALUES (:name, :role, :mythology, :description)
        """,
        {
            "name": "insert-test-persona",
            "role": "Engineer",
            "mythology": "test",
            "description": "Test insert",
        },
    )

    # Row ID should be returned
    assert row_id is not None
    assert row_id > 0

    # Verify the row was inserted
    result = test_db.execute_query(
        "SELECT * FROM personas WHERE name = :name",
        {"name": "insert-test-persona"},
    )
    assert len(result) == 1
    assert result[0]["name"] == "insert-test-persona"
