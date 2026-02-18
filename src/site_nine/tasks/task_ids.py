"""Task ID utilities and validation"""

import re

from buzz import enforce_defined, require_condition

from site_nine.core.roles import Role

# Role prefix mapping
ROLE_PREFIXES = {
    Role.ADMINISTRATOR.title_case: "ADM",
    Role.ARCHITECT.title_case: "ARC",
    Role.ENGINEER.title_case: "ENG",
    Role.TESTER.title_case: "TST",
    Role.DOCUMENTARIAN.title_case: "DOC",
    Role.DESIGNER.title_case: "DES",
    Role.INSPECTOR.title_case: "INS",
    Role.OPERATOR.title_case: "OPR",
    Role.HISTORIAN.title_case: "HIS",
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


def validate_task_id(task_id: str) -> None:
    """
    Validate task ID format.

    Args:
        task_id: Task ID to validate (e.g., "OPR-H-0001")

    Raises:
        ValueError: If task ID format is invalid
    """
    match = enforce_defined(
        TASK_ID_PATTERN.match(task_id),
        "Invalid format. Expected: PREFIX-PRIORITY-NUMBER (e.g., OPR-H-0001)",
        raise_exc_class=ValueError,
    )

    prefix, priority_code, number = match.groups()

    valid_prefixes = ", ".join(sorted(ROLE_PREFIXES.values()))
    require_condition(
        prefix in PREFIX_TO_ROLE, f"Invalid role prefix '{prefix}'. Valid: {valid_prefixes}", raise_exc_class=ValueError
    )

    require_condition(
        priority_code in CODE_TO_PRIORITY,
        f"Invalid priority code '{priority_code}'. Valid: C, H, M, L",
        raise_exc_class=ValueError,
    )

    num = int(number)
    require_condition(1 <= num <= 9999, "Number must be between 0001 and 9999", raise_exc_class=ValueError)


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

    Raises:
        ValueError: If any component is invalid
    """
    prefix = enforce_defined(ROLE_PREFIXES.get(role), f"Invalid role: {role}", raise_exc_class=ValueError)
    priority_code = enforce_defined(
        PRIORITY_CODES.get(priority), f"Invalid priority: {priority}", raise_exc_class=ValueError
    )

    task_id = f"{prefix}-{priority_code}-{number:04d}"
    validate_task_id(task_id)
    return task_id


def get_next_task_number(db) -> int:
    """
    Get next available task number (global counter).

    Args:
        db: Database instance

    Returns:
        Next sequential number (1-9999)
    """
    result = db.execute_query(
        """
        SELECT MAX(CAST(SUBSTR(id, -4) AS INTEGER)) as max_num
        FROM tasks
        """
    )

    max_num = result[0]["max_num"]
    if max_num is None:
        return 1

    return max_num + 1


def sort_task_ids(task_ids: list[str]) -> list[str]:
    """
    Sort task IDs by priority (descending), role prefix, then number.

    Args:
        task_ids: List of task IDs

    Returns:
        Sorted list of task IDs

    Raises:
        ValueError: If any task ID is invalid
    """
    priority_order = {"C": 0, "H": 1, "M": 2, "L": 3}

    def sort_key(task_id: str) -> tuple:
        match = enforce_defined(
            TASK_ID_PATTERN.match(task_id), f"Invalid task ID format: {task_id}", raise_exc_class=ValueError
        )
        prefix, priority_code, number = match.groups()
        return (priority_order.get(priority_code, 999), prefix, int(number))

    return sorted(task_ids, key=sort_key)
