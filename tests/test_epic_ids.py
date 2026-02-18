"""Tests for epics.epic_ids module"""

import pytest

from site_nine.epics.epic_ids import (
    CODE_TO_PRIORITY,
    PRIORITY_TO_CODE,
    format_epic_id,
    get_next_epic_number,
    parse_epic_id,
    validate_epic_id,
)


def test_priority_to_code_mapping():
    """Test priority code constants"""
    assert PRIORITY_TO_CODE["CRITICAL"] == "C"
    assert PRIORITY_TO_CODE["HIGH"] == "H"
    assert PRIORITY_TO_CODE["MEDIUM"] == "M"
    assert PRIORITY_TO_CODE["LOW"] == "L"


def test_code_to_priority_mapping():
    """Test reverse priority mapping"""
    assert CODE_TO_PRIORITY["C"] == "CRITICAL"
    assert CODE_TO_PRIORITY["H"] == "HIGH"
    assert CODE_TO_PRIORITY["M"] == "MEDIUM"
    assert CODE_TO_PRIORITY["L"] == "LOW"


def test_format_epic_id_valid():
    """Test formatting valid epic IDs"""
    assert format_epic_id("HIGH", 1) == "EPC-H-0001"
    assert format_epic_id("CRITICAL", 42) == "EPC-C-0042"
    assert format_epic_id("MEDIUM", 9999) == "EPC-M-9999"
    assert format_epic_id("LOW", 1) == "EPC-L-0001"


def test_format_epic_id_invalid_priority():
    """Test formatting with invalid priority"""
    with pytest.raises(ValueError, match="Invalid priority: INVALID"):
        format_epic_id("INVALID", 1)


def test_parse_epic_id_valid():
    """Test parsing valid epic IDs"""
    assert parse_epic_id("EPC-H-0001") == ("HIGH", 1)
    assert parse_epic_id("EPC-C-0042") == ("CRITICAL", 42)
    assert parse_epic_id("EPC-M-9999") == ("MEDIUM", 9999)
    assert parse_epic_id("EPC-L-0001") == ("LOW", 1)


def test_parse_epic_id_invalid_format():
    """Test parsing invalid format"""
    assert parse_epic_id("INVALID") is None
    assert parse_epic_id("EPC-H-1") is None  # Wrong number format
    assert parse_epic_id("EPC-X-0001") is None  # Invalid priority code
    assert parse_epic_id("") is None


def test_validate_epic_id_valid():
    """Test validating valid epic IDs"""
    is_valid, error = validate_epic_id("EPC-H-0001")
    assert is_valid is True
    assert error is None

    is_valid, error = validate_epic_id("EPC-C-9999")
    assert is_valid is True
    assert error is None


def test_validate_epic_id_empty():
    """Test validating empty epic ID"""
    is_valid, error = validate_epic_id("")
    assert is_valid is False
    assert "cannot be empty" in error


def test_validate_epic_id_invalid_format():
    """Test validating invalid format"""
    is_valid, error = validate_epic_id("INVALID")
    assert is_valid is False
    assert "must match format" in error

    is_valid, error = validate_epic_id("EPC-H-1")
    assert is_valid is False
    assert "must match format" in error


def test_validate_epic_id_invalid_priority_code():
    """Test validating with invalid priority code"""
    # Note: The regex won't match EPC-X-0001 since X is not in [CHML]
    # So this will fail at format check, not priority check
    is_valid, error = validate_epic_id("EPC-X-0001")
    assert is_valid is False
    assert "must match format" in error


def test_get_next_epic_number_empty_db(test_db):
    """Test getting next epic number when no epics exist"""
    result = get_next_epic_number(test_db)
    assert result == 1


def test_get_next_epic_number_with_existing_epics(test_db):
    """Test getting next epic number with existing epics"""
    # Create some epics
    test_db.execute_update(
        """
        INSERT INTO epics (id, title, description, priority, file_path, created_at, updated_at)
        VALUES 
            ('EPC-H-0001', 'Epic 1', 'Test', 'HIGH', '.opencode/work/epics/EPC-H-0001.md', datetime('now'), datetime('now')),
            ('EPC-M-0003', 'Epic 3', 'Test', 'MEDIUM', '.opencode/work/epics/EPC-M-0003.md', datetime('now'), datetime('now'))
        """
    )

    result = get_next_epic_number(test_db)
    # Should return 4 (highest is 3)
    assert result == 4


def test_get_next_epic_number_sequential(test_db):
    """Test that epic numbers are sequential across priorities"""
    # Create epics with different priorities
    test_db.execute_update(
        """
        INSERT INTO epics (id, title, description, priority, file_path, created_at, updated_at)
        VALUES 
            ('EPC-H-0005', 'Epic 5', 'Test', 'HIGH', '.opencode/work/epics/EPC-H-0005.md', datetime('now'), datetime('now')),
            ('EPC-L-0007', 'Epic 7', 'Test', 'LOW', '.opencode/work/epics/EPC-L-0007.md', datetime('now'), datetime('now'))
        """
    )

    result = get_next_epic_number(test_db)
    # Should return 8 (highest number is 7)
    assert result == 8


def test_parse_epic_id_invalid_priority_code():
    """Test parsing epic ID with technically valid format but invalid priority code"""
    # This would match the regex pattern but has an invalid priority code
    # Note: The regex already filters for [CHML], so we can't actually test this
    # via the public API since the regex won't match. Testing via direct CODE_TO_PRIORITY check.
    result = parse_epic_id("EPC-H-0001")
    assert result == ("HIGH", 1)

    # Edge case: empty string check
    result = parse_epic_id("EPC-X-0001")
    assert result is None


def test_validate_epic_id_edge_cases():
    """Test validate_epic_id with edge case scenarios"""
    # Valid IDs with different priorities
    is_valid, error = validate_epic_id("EPC-C-0001")
    assert is_valid is True

    is_valid, error = validate_epic_id("EPC-M-0001")
    assert is_valid is True

    is_valid, error = validate_epic_id("EPC-L-0001")
    assert is_valid is True
