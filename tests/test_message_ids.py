"""Tests for messaging.message_ids module"""

import pytest

from site_nine.messaging.message_ids import (
    CODE_TO_PRIORITY,
    PRIORITY_CODES,
    format_message_id,
    get_next_message_number,
    parse_message_id,
    sort_message_ids,
    validate_message_id,
)


def test_priority_codes_mapping():
    """Test priority code constants"""
    assert PRIORITY_CODES["CRITICAL"] == "C"
    assert PRIORITY_CODES["HIGH"] == "H"
    assert PRIORITY_CODES["MEDIUM"] == "M"
    assert PRIORITY_CODES["LOW"] == "L"


def test_code_to_priority_mapping():
    """Test reverse priority code mapping"""
    assert CODE_TO_PRIORITY["C"] == "CRITICAL"
    assert CODE_TO_PRIORITY["H"] == "HIGH"
    assert CODE_TO_PRIORITY["M"] == "MEDIUM"
    assert CODE_TO_PRIORITY["L"] == "LOW"


def test_validate_message_id_valid():
    """Test validating valid message IDs"""
    validate_message_id("MSG-M-0001")
    validate_message_id("MSG-H-0042")
    validate_message_id("MSG-C-9999")


def test_validate_message_id_invalid_format():
    """Test validating message IDs with invalid format"""
    with pytest.raises(ValueError, match="Invalid format"):
        validate_message_id("INVALID")

    with pytest.raises(ValueError, match="Invalid format"):
        validate_message_id("MSG-M-1")

    with pytest.raises(ValueError, match="Invalid format"):
        validate_message_id("MS-M-0001")


def test_validate_message_id_invalid_priority():
    """Test validating message IDs with invalid priority code"""
    with pytest.raises(ValueError, match="Invalid format"):
        validate_message_id("MSG-X-0001")


def test_validate_message_id_invalid_number_range():
    """Test validating message IDs with invalid number range"""
    with pytest.raises(ValueError, match="Number must be between 0001 and 9999"):
        validate_message_id("MSG-M-0000")

    with pytest.raises(ValueError, match="Invalid format"):
        validate_message_id("MSG-M-10000")


def test_parse_message_id_valid():
    """Test parsing valid message IDs"""
    result = parse_message_id("MSG-M-0001")
    assert result == ("MEDIUM", 1)

    result = parse_message_id("MSG-H-0042")
    assert result == ("HIGH", 42)

    result = parse_message_id("MSG-C-9999")
    assert result == ("CRITICAL", 9999)


def test_parse_message_id_invalid_format():
    """Test parsing message IDs with invalid format"""
    result = parse_message_id("INVALID")
    assert result is None

    result = parse_message_id("MSG-M-1")
    assert result is None


def test_parse_message_id_invalid_priority():
    """Test parsing message IDs with invalid priority code"""
    result = parse_message_id("MSG-X-0001")
    assert result is None


def test_format_message_id_valid():
    """Test formatting valid message IDs"""
    result = format_message_id("MEDIUM", 1)
    assert result == "MSG-M-0001"

    result = format_message_id("HIGH", 42)
    assert result == "MSG-H-0042"

    result = format_message_id("CRITICAL", 9999)
    assert result == "MSG-C-9999"


def test_format_message_id_invalid_priority():
    """Test formatting message ID with invalid priority"""
    with pytest.raises(ValueError, match="Invalid priority"):
        format_message_id("INVALID", 1)


def test_format_message_id_invalid_number_too_low():
    """Test formatting message ID with number too low"""
    with pytest.raises(ValueError, match="Number must be between 0001 and 9999"):
        format_message_id("MEDIUM", 0)


def test_format_message_id_invalid_number_too_high():
    """Test formatting message ID with number too high"""
    with pytest.raises(ValueError):
        format_message_id("MEDIUM", 10000)


def test_get_next_message_number_empty_db(test_db):
    """Test getting next message number when no messages exist"""
    # Check if messages table exists and if so, skip tests that need insertion
    try:
        result = test_db.execute_query("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
        if result:
            # Messages table exists from migration - just test with empty table
            result = get_next_message_number(test_db)
            assert result == 1
            return
    except Exception:
        pass

    # If messages table doesn't exist, create a simple version for testing
    try:
        test_db.execute_update(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                from_mission_id INTEGER,
                subject TEXT,
                body TEXT,
                priority TEXT DEFAULT 'MEDIUM',
                created_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
    except Exception:
        pass

    result = get_next_message_number(test_db)
    assert result == 1


def test_get_next_message_number_with_existing_messages(test_db_with_data):
    """Test getting next message number with existing messages"""
    db = test_db_with_data
    # Insert a conversation and messages using the real schema
    db.execute_update(
        """
        INSERT INTO conversations (id, subject, type, status, participant_1_id, participant_2_id)
        VALUES ('CONV-MID-01', 'Test', 'conversation', 'open', 1, 2)
        """
    )
    db.execute_update(
        """
        INSERT INTO messages (id, conversation_id, from_possession_id, subject, body, priority)
        VALUES ('MSG-M-0001', 'CONV-MID-01', 1, 'Test', 'Body', 'MEDIUM')
        """
    )
    db.execute_update(
        """
        INSERT INTO messages (id, conversation_id, from_possession_id, subject, body, priority)
        VALUES ('MSG-M-0003', 'CONV-MID-01', 1, 'Test', 'Body', 'MEDIUM')
        """
    )

    result = get_next_message_number(db)
    # Should return 4 (highest is 3)
    assert result == 4


def test_get_next_message_number_across_different_priorities(test_db_with_data):
    """Test that next message number is global across all priorities"""
    db = test_db_with_data
    db.execute_update(
        """
        INSERT INTO conversations (id, subject, type, status, participant_1_id, participant_2_id)
        VALUES ('CONV-MID-02', 'Test', 'conversation', 'open', 1, 2)
        """
    )
    db.execute_update(
        """
        INSERT INTO messages (id, conversation_id, from_possession_id, subject, body, priority)
        VALUES ('MSG-M-0005', 'CONV-MID-02', 1, 'Test', 'Body', 'MEDIUM')
        """
    )
    db.execute_update(
        """
        INSERT INTO messages (id, conversation_id, from_possession_id, subject, body, priority)
        VALUES ('MSG-H-0007', 'CONV-MID-02', 1, 'Test', 'Body', 'HIGH')
        """
    )

    result = get_next_message_number(db)
    # Should return 8 (highest number globally is 7)
    assert result == 8


def test_sort_message_ids_empty():
    """Test sorting empty list"""
    result = sort_message_ids([])
    assert result == []


def test_sort_message_ids_by_priority():
    """Test sorting message IDs by priority (descending)"""
    message_ids = [
        "MSG-L-0001",
        "MSG-C-0001",
        "MSG-M-0001",
        "MSG-H-0001",
    ]

    result = sort_message_ids(message_ids)
    assert result == [
        "MSG-C-0001",  # Critical first
        "MSG-H-0001",  # High
        "MSG-M-0001",  # Medium
        "MSG-L-0001",  # Low last
    ]


def test_sort_message_ids_by_number():
    """Test sorting message IDs by number when priority is same"""
    message_ids = [
        "MSG-M-0005",
        "MSG-M-0001",
        "MSG-M-0003",
        "MSG-M-0002",
    ]

    result = sort_message_ids(message_ids)
    assert result == [
        "MSG-M-0001",
        "MSG-M-0002",
        "MSG-M-0003",
        "MSG-M-0005",
    ]


def test_sort_message_ids_mixed():
    """Test sorting message IDs with mixed priorities and numbers"""
    message_ids = [
        "MSG-L-0010",
        "MSG-H-0001",
        "MSG-M-0005",
        "MSG-C-0002",
        "MSG-H-0003",
    ]

    result = sort_message_ids(message_ids)
    # Should sort by: priority (desc), then number (asc)
    assert result == [
        "MSG-C-0002",  # Critical
        "MSG-H-0001",  # High, lower number
        "MSG-H-0003",  # High, higher number
        "MSG-M-0005",  # Medium
        "MSG-L-0010",  # Low
    ]


def test_sort_message_ids_with_invalid():
    """Test sorting message IDs with invalid IDs raises ValueError"""
    message_ids = [
        "MSG-M-0001",
        "INVALID",
        "MSG-H-0002",
    ]

    with pytest.raises(ValueError, match="Invalid message ID format"):
        sort_message_ids(message_ids)


def test_format_message_id_with_single_digit():
    """Test formatting message ID with single digit number"""
    result = format_message_id("HIGH", 5)
    assert result == "MSG-H-0005"


def test_format_message_id_with_max_number():
    """Test formatting message ID with maximum number"""
    result = format_message_id("LOW", 9999)
    assert result == "MSG-L-9999"


def test_validate_message_id_case_sensitive():
    """Test that validation is case-sensitive"""
    with pytest.raises(ValueError, match="Invalid format"):
        validate_message_id("msg-m-0001")

    with pytest.raises(ValueError, match="Invalid format"):
        validate_message_id("Msg-M-0001")


def test_parse_message_id_extracts_correct_values():
    """Test that parse extracts all components correctly"""
    priority, number = parse_message_id("MSG-C-0123")
    assert priority == "CRITICAL"
    assert number == 123


def test_sort_message_ids_single_item():
    """Test sorting with single item"""
    result = sort_message_ids(["MSG-M-0001"])
    assert result == ["MSG-M-0001"]


def test_sort_message_ids_already_sorted():
    """Test sorting already sorted list"""
    message_ids = ["MSG-C-0001", "MSG-H-0001", "MSG-M-0001"]
    result = sort_message_ids(message_ids)
    assert result == message_ids
