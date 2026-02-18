"""Tests for tasks.task_ids module"""

import pytest

from site_nine.tasks.task_ids import (
    CODE_TO_PRIORITY,
    PREFIX_TO_ROLE,
    PRIORITY_CODES,
    ROLE_PREFIXES,
    format_task_id,
    get_next_task_number,
    parse_task_id,
    sort_task_ids,
    validate_task_id,
)


def test_role_prefixes_mapping():
    """Test role prefix constants"""
    assert ROLE_PREFIXES["Administrator"] == "ADM"
    assert ROLE_PREFIXES["Engineer"] == "ENG"
    assert ROLE_PREFIXES["Tester"] == "TST"
    assert ROLE_PREFIXES["Operator"] == "OPR"


def test_prefix_to_role_mapping():
    """Test reverse role prefix mapping"""
    assert PREFIX_TO_ROLE["ADM"] == "Administrator"
    assert PREFIX_TO_ROLE["ENG"] == "Engineer"
    assert PREFIX_TO_ROLE["TST"] == "Tester"
    assert PREFIX_TO_ROLE["OPR"] == "Operator"


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


def test_validate_task_id_valid():
    """Test validating valid task IDs"""
    validate_task_id("ENG-M-0001")
    validate_task_id("OPR-H-0042")
    validate_task_id("TST-C-9999")


def test_validate_task_id_invalid_format():
    """Test validating task IDs with invalid format"""
    with pytest.raises(ValueError, match="Invalid format"):
        validate_task_id("INVALID")

    with pytest.raises(ValueError, match="Invalid format"):
        validate_task_id("ENG-M-1")

    with pytest.raises(ValueError, match="Invalid format"):
        validate_task_id("EN-M-0001")


def test_validate_task_id_invalid_prefix():
    """Test validating task IDs with invalid role prefix"""
    with pytest.raises(ValueError, match="Invalid role prefix.*XXX"):
        validate_task_id("XXX-M-0001")


def test_validate_task_id_invalid_priority():
    """Test validating task IDs with invalid priority code"""
    with pytest.raises(ValueError, match="Invalid format"):
        validate_task_id("ENG-X-0001")


def test_validate_task_id_invalid_number_range():
    """Test validating task IDs with invalid number range"""
    with pytest.raises(ValueError, match="Number must be between 0001 and 9999"):
        validate_task_id("ENG-M-0000")

    with pytest.raises(ValueError, match="Invalid format"):
        validate_task_id("ENG-M-10000")


def test_parse_task_id_valid():
    """Test parsing valid task IDs"""
    result = parse_task_id("ENG-M-0001")
    assert result == ("Engineer", "MEDIUM", 1)

    result = parse_task_id("OPR-H-0042")
    assert result == ("Operator", "HIGH", 42)

    result = parse_task_id("TST-C-9999")
    assert result == ("Tester", "CRITICAL", 9999)


def test_parse_task_id_invalid_format():
    """Test parsing task IDs with invalid format"""
    result = parse_task_id("INVALID")
    assert result is None

    result = parse_task_id("ENG-M-1")
    assert result is None


def test_parse_task_id_invalid_prefix():
    """Test parsing task IDs with invalid prefix"""
    result = parse_task_id("XXX-M-0001")
    assert result is None


def test_parse_task_id_invalid_priority():
    """Test parsing task IDs with invalid priority code"""
    result = parse_task_id("ENG-X-0001")
    assert result is None


def test_format_task_id_valid():
    """Test formatting valid task IDs"""
    result = format_task_id("Engineer", "MEDIUM", 1)
    assert result == "ENG-M-0001"

    result = format_task_id("Operator", "HIGH", 42)
    assert result == "OPR-H-0042"

    result = format_task_id("Tester", "CRITICAL", 9999)
    assert result == "TST-C-9999"


def test_format_task_id_invalid_role():
    """Test formatting task ID with invalid role"""
    with pytest.raises(ValueError, match="Invalid role"):
        format_task_id("InvalidRole", "MEDIUM", 1)


def test_format_task_id_invalid_priority():
    """Test formatting task ID with invalid priority"""
    with pytest.raises(ValueError, match="Invalid priority"):
        format_task_id("Engineer", "INVALID", 1)


def test_format_task_id_invalid_number_too_low():
    """Test formatting task ID with number too low"""
    with pytest.raises(ValueError, match="Number must be between 0001 and 9999"):
        format_task_id("Engineer", "MEDIUM", 0)


def test_format_task_id_invalid_number_too_high():
    """Test formatting task ID with number too high"""
    with pytest.raises(ValueError):
        format_task_id("Engineer", "MEDIUM", 10000)


def test_get_next_task_number_empty_db(test_db):
    """Test getting next task number when no tasks exist"""
    result = get_next_task_number(test_db)
    assert result == 1


def test_get_next_task_number_with_existing_tasks(test_db):
    """Test getting next task number with existing tasks"""
    # Create some tasks
    test_db.execute_update(
        """
        INSERT INTO tasks (id, title, description, status, priority, role, file_path, created_at)
        VALUES ('ENG-M-0001', 'Task 1', 'Test', 'TODO', 'MEDIUM', 'Engineer', '.opencode/work/tasks/ENG-M-0001.md', datetime('now'))
        """,
    )

    test_db.execute_update(
        """
        INSERT INTO tasks (id, title, description, status, priority, role, file_path, created_at)
        VALUES ('ENG-M-0003', 'Task 3', 'Test', 'TODO', 'MEDIUM', 'Engineer', '.opencode/work/tasks/ENG-M-0003.md', datetime('now'))
        """,
    )

    result = get_next_task_number(test_db)
    # Should return 4 (highest is 3)
    assert result == 4


def test_get_next_task_number_across_different_roles(test_db):
    """Test that next task number is global across all roles"""
    # Create tasks with different roles
    test_db.execute_update(
        """
        INSERT INTO tasks (id, title, description, status, priority, role, file_path, created_at)
        VALUES ('ENG-M-0005', 'Engineer Task', 'Test', 'TODO', 'MEDIUM', 'Engineer', '.opencode/work/tasks/ENG-M-0005.md', datetime('now'))
        """,
    )

    test_db.execute_update(
        """
        INSERT INTO tasks (id, title, description, status, priority, role, file_path, created_at)
        VALUES ('TST-H-0007', 'Tester Task', 'Test', 'TODO', 'HIGH', 'Tester', '.opencode/work/tasks/TST-H-0007.md', datetime('now'))
        """,
    )

    result = get_next_task_number(test_db)
    # Should return 8 (highest number globally is 7)
    assert result == 8


def test_sort_task_ids_empty():
    """Test sorting empty list"""
    result = sort_task_ids([])
    assert result == []


def test_sort_task_ids_by_priority():
    """Test sorting task IDs by priority (descending)"""
    task_ids = [
        "ENG-L-0001",
        "ENG-C-0001",
        "ENG-M-0001",
        "ENG-H-0001",
    ]

    result = sort_task_ids(task_ids)
    assert result == [
        "ENG-C-0001",  # Critical first
        "ENG-H-0001",  # High
        "ENG-M-0001",  # Medium
        "ENG-L-0001",  # Low last
    ]


def test_sort_task_ids_by_role_prefix():
    """Test sorting task IDs by role prefix when priority is same"""
    task_ids = [
        "OPR-M-0001",
        "ENG-M-0001",
        "TST-M-0001",
        "ARC-M-0001",
    ]

    result = sort_task_ids(task_ids)
    # Should sort alphabetically by prefix
    assert result == [
        "ARC-M-0001",
        "ENG-M-0001",
        "OPR-M-0001",
        "TST-M-0001",
    ]


def test_sort_task_ids_by_number():
    """Test sorting task IDs by number when priority and role are same"""
    task_ids = [
        "ENG-M-0005",
        "ENG-M-0001",
        "ENG-M-0003",
        "ENG-M-0002",
    ]

    result = sort_task_ids(task_ids)
    assert result == [
        "ENG-M-0001",
        "ENG-M-0002",
        "ENG-M-0003",
        "ENG-M-0005",
    ]


def test_sort_task_ids_mixed():
    """Test sorting task IDs with mixed priorities, roles, and numbers"""
    task_ids = [
        "TST-L-0010",
        "ENG-H-0001",
        "OPR-M-0005",
        "ENG-C-0002",
        "TST-H-0001",
        "ENG-H-0003",
    ]

    result = sort_task_ids(task_ids)
    # Should sort by: priority (desc), then role (asc), then number (asc)
    assert result == [
        "ENG-C-0002",  # Critical
        "ENG-H-0001",  # High, ENG comes before TST
        "ENG-H-0003",  # High, ENG, higher number
        "TST-H-0001",  # High, TST
        "OPR-M-0005",  # Medium
        "TST-L-0010",  # Low
    ]


def test_sort_task_ids_with_invalid():
    """Test sorting task IDs with invalid IDs raises ValueError"""
    task_ids = [
        "ENG-M-0001",
        "INVALID",
        "ENG-H-0002",
        "ALSO_INVALID",
    ]

    with pytest.raises(ValueError, match="Invalid task ID format"):
        sort_task_ids(task_ids)


def test_format_task_id_with_single_digit():
    """Test formatting task ID with single digit number"""
    result = format_task_id("Engineer", "HIGH", 5)
    assert result == "ENG-H-0005"


def test_format_task_id_with_max_number():
    """Test formatting task ID with maximum number"""
    result = format_task_id("Engineer", "LOW", 9999)
    assert result == "ENG-L-9999"


def test_validate_task_id_case_sensitive():
    """Test that validation is case-sensitive"""
    with pytest.raises(ValueError, match="Invalid format"):
        validate_task_id("eng-m-0001")

    with pytest.raises(ValueError, match="Invalid format"):
        validate_task_id("Eng-M-0001")


def test_parse_task_id_extracts_correct_values():
    """Test that parse extracts all components correctly"""
    role, priority, number = parse_task_id("ADM-C-0123")
    assert role == "Administrator"
    assert priority == "CRITICAL"
    assert number == 123


def test_sort_task_ids_single_item():
    """Test sorting with single item"""
    result = sort_task_ids(["ENG-M-0001"])
    assert result == ["ENG-M-0001"]


def test_sort_task_ids_already_sorted():
    """Test sorting already sorted list"""
    task_ids = ["ENG-C-0001", "ENG-H-0001", "ENG-M-0001"]
    result = sort_task_ids(task_ids)
    assert result == task_ids
