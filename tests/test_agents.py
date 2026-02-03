"""Tests for agent session management"""

from s9.agents.sessions import AgentSessionManager
from s9.core.database import Database


def test_start_session(test_db: Database):
    """Test starting an agent session"""
    # Add daemon name first with valid role
    test_db.execute_update(
        """
        INSERT INTO daemon_names (name, role, mythology, description, usage_count)
        VALUES ('azazel', 'Inspector', 'judaism', 'Fallen angel', 0)
        """
    )

    manager = AgentSessionManager(test_db)
    session_id = manager.start_session(
        name="azazel",
        role="Inspector",
        task_summary="Test investigation",
    )

    assert session_id is not None
    assert session_id > 0

    # Verify session was created
    session = manager.get_session(session_id)
    assert session is not None
    assert session.name == "azazel"
    assert session.base_name == "azazel"
    assert session.suffix is None
    assert session.role == "Inspector"
    assert session.status == "in-progress"


def test_start_session_with_suffix(test_db: Database):
    """Test starting a session with a suffixed name"""
    # Add daemon name with valid role
    test_db.execute_update(
        """
        INSERT INTO daemon_names (name, role, mythology, description, usage_count)
        VALUES ('belial', 'Administrator', 'judaism', 'Demon', 0)
        """
    )

    manager = AgentSessionManager(test_db)
    session_id = manager.start_session(
        name="belial-ii",
        role="Administrator",
        task_summary="Second session",
    )

    session = manager.get_session(session_id)
    assert session.name == "belial-ii"
    assert session.base_name == "belial"
    assert session.suffix == "ii"


def test_end_session(test_db: Database):
    """Test ending an agent session"""
    # Add daemon name and start session with valid role
    test_db.execute_update(
        """
        INSERT INTO daemon_names (name, role, mythology, description, usage_count)
        VALUES ('mephisto', 'Builder', 'german', 'Devil', 0)
        """
    )

    manager = AgentSessionManager(test_db)
    session_id = manager.start_session(
        name="mephisto",
        role="Builder",
        task_summary="Build feature",
    )

    # End the session
    manager.end_session(session_id, status="completed")

    # Verify session was ended
    session = manager.get_session(session_id)
    assert session.status == "completed"
    assert session.end_time is not None


def test_list_sessions(test_db: Database):
    """Test listing sessions with filters"""
    # Add daemon names and create sessions with valid roles
    test_db.execute_update(
        """
        INSERT INTO daemon_names (name, role, mythology, description, usage_count)
        VALUES 
            ('daemon1', 'Builder', 'test', 'Test 1', 0),
            ('daemon2', 'Administrator', 'test', 'Test 2', 0)
        """
    )

    manager = AgentSessionManager(test_db)
    id1 = manager.start_session("daemon1", "Builder", "Task 1")
    _id2 = manager.start_session("daemon2", "Administrator", "Task 2")

    # End first session
    manager.end_session(id1, "completed")

    # List all sessions
    all_sessions = manager.list_sessions()
    assert len(all_sessions) == 2

    # List active only
    active_sessions = manager.list_sessions(active_only=True)
    assert len(active_sessions) == 1
    assert active_sessions[0].name == "daemon2"

    # Filter by role
    builder_sessions = manager.list_sessions(role="Builder")
    assert len(builder_sessions) == 1
    assert builder_sessions[0].name == "daemon1"


def test_daemon_name_usage_tracking(test_db: Database):
    """Test that daemon name usage count is updated"""
    # Add daemon name with valid role
    test_db.execute_update(
        """
        INSERT INTO daemon_names (name, role, mythology, description, usage_count)
        VALUES ('tracked', 'Builder', 'test', 'Tracked daemon', 0)
        """
    )

    manager = AgentSessionManager(test_db)

    # Start multiple sessions with same daemon
    manager.start_session("tracked", "Builder", "Task 1")
    manager.start_session("tracked-ii", "Builder", "Task 2")

    # Check usage count
    result = test_db.execute_query("SELECT usage_count FROM daemon_names WHERE name = 'tracked'")
    assert result[0]["usage_count"] == 2
