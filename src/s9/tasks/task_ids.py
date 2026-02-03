"""Task ID utilities and validation"""

import re
from typing import Literal

# Role prefix mapping
ROLE_PREFIXES = {
    "Administrator": "ADM",
    "Architect": "ARC",
    "Builder": "BLD",
    "Tester": "TST",
    "Documentarian": "DOC",
    "Designer": "DES",
    "Inspector": "INS",
    "Operator": "OPR",
    "Historian": "HIS",
}

# Reverse mapping
PREFIX_TO_ROLE = {v: k for k, v in ROLE_PREFIXES.items()}

# Priority codes
PRIORITY_CODES = {
    "CRITICAL": "C",
    "HIGH": "H",
    "MEDIUM": "M",
    "LOW": "L",
}

# Reverse mapping
CODE_TO_PRIORITY = {v: k for k, v in PRIORITY_CODES.items()}

# Task ID format: PREFIX-PRIORITY-NUMBER (e.g., OPR-H-0001)
TASK_ID_PATTERN = re.compile(r"^([A-Z]{3})-([CHML])-(\d{4})$")


def validate_task_id(task_id: str) -> tuple[bool, str | None]:
    """
    Validate task ID format.

    Args:
        task_id: Task ID to validate (e.g., "OPR-H-0001")

    Returns:
        Tuple of (is_valid, error_message)
    """
    match = TASK_ID_PATTERN.match(task_id)
    if not match:
        return False, f"Invalid format. Expected: PREFIX-PRIORITY-NUMBER (e.g., OPR-H-0001)"

    prefix, priority_code, number = match.groups()

    # Validate prefix
    if prefix not in PREFIX_TO_ROLE:
        valid_prefixes = ", ".join(sorted(ROLE_PREFIXES.values()))
        return False, f"Invalid role prefix '{prefix}'. Valid: {valid_prefixes}"

    # Validate priority code
    if priority_code not in CODE_TO_PRIORITY:
        return False, f"Invalid priority code '{priority_code}'. Valid: C, H, M, L"

    # Validate number range
    num = int(number)
    if num < 1 or num > 9999:
        return False, f"Number must be between 0001 and 9999"

    return True, None


def parse_task_id(task_id: str) -> tuple[str, str, int] | None:
    """
    Parse task ID into components.

    Args:
        task_id: Task ID (e.g., "OPR-H-0001")

    Returns:
        Tuple of (role, priority, number) or None if invalid
    """
    match = TASK_ID_PATTERN.match(task_id)
    if not match:
        return None

    prefix, priority_code, number = match.groups()
    role = PREFIX_TO_ROLE.get(prefix)
    priority = CODE_TO_PRIORITY.get(priority_code)

    if not role or not priority:
        return None

    return role, priority, int(number)


def format_task_id(role: str, priority: str, number: int) -> str:
    """
    Format task ID from components.

    Args:
        role: Role name (e.g., "Operator")
        priority: Priority level (e.g., "HIGH")
        number: Sequential number (1-9999)

    Returns:
        Formatted task ID (e.g., "OPR-H-0001")
    """
    prefix = ROLE_PREFIXES.get(role)
    if not prefix:
        raise ValueError(f"Invalid role: {role}")

    priority_code = PRIORITY_CODES.get(priority)
    if not priority_code:
        raise ValueError(f"Invalid priority: {priority}")

    if number < 1 or number > 9999:
        raise ValueError(f"Number must be between 1 and 9999")

    return f"{prefix}-{priority_code}-{number:04d}"


def get_next_task_number(db) -> int:
    """
    Get next available task number (global counter).

    Args:
        db: Database instance

    Returns:
        Next sequential number (1-9999)
    """
    # Extract number from all task IDs
    result = db.execute_query("SELECT id FROM tasks ORDER BY id DESC")

    if not result:
        return 1

    # Find highest number across all task IDs
    max_num = 0
    for row in result:
        task_id = row["id"]
        match = TASK_ID_PATTERN.match(task_id)
        if match:
            num = int(match.group(3))
            max_num = max(max_num, num)

    return max_num + 1


def sort_task_ids(task_ids: list[str]) -> list[str]:
    """
    Sort task IDs by priority (descending), role prefix, then number.

    Args:
        task_ids: List of task IDs

    Returns:
        Sorted list of task IDs
    """
    priority_order = {"C": 0, "H": 1, "M": 2, "L": 3}

    def sort_key(task_id: str) -> tuple:
        match = TASK_ID_PATTERN.match(task_id)
        if not match:
            # Put invalid IDs at the end
            return (999, "ZZZ", 9999)

        prefix, priority_code, number = match.groups()
        return (priority_order.get(priority_code, 999), prefix, int(number))

    return sorted(task_ids, key=sort_key)
