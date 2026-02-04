"""Epic ID generation and validation"""

import re

from site_nine.core.database import Database

# Epic ID format: EPC-[P]-[NNNN]
# Examples: EPC-H-0001, EPC-C-0002, EPC-M-0003
EPIC_ID_PATTERN = re.compile(r"^EPC-([CHML])-(\d{4})$")

PRIORITY_TO_CODE = {
    "CRITICAL": "C",
    "HIGH": "H",
    "MEDIUM": "M",
    "LOW": "L",
}

CODE_TO_PRIORITY = {v: k for k, v in PRIORITY_TO_CODE.items()}


def format_epic_id(priority: str, number: int) -> str:
    """
    Format epic ID from priority and number.

    Args:
        priority: Priority level (CRITICAL, HIGH, MEDIUM, LOW)
        number: Sequential number

    Returns:
        Formatted epic ID (e.g., EPC-H-0001)
    """
    priority_code = PRIORITY_TO_CODE.get(priority)
    if not priority_code:
        raise ValueError(f"Invalid priority: {priority}")

    return f"EPC-{priority_code}-{number:04d}"


def parse_epic_id(epic_id: str) -> tuple[str, int] | None:
    """
    Parse epic ID into components.

    Args:
        epic_id: Epic ID to parse (e.g., EPC-H-0001)

    Returns:
        Tuple of (priority, number) or None if invalid
    """
    match = EPIC_ID_PATTERN.match(epic_id)
    if not match:
        return None

    priority_code, number_str = match.groups()
    priority = CODE_TO_PRIORITY.get(priority_code)
    if not priority:
        return None

    return priority, int(number_str)


def validate_epic_id(epic_id: str) -> tuple[bool, str | None]:
    """
    Validate epic ID format.

    Args:
        epic_id: Epic ID to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not epic_id:
        return False, "Epic ID cannot be empty"

    match = EPIC_ID_PATTERN.match(epic_id)
    if not match:
        return False, "Epic ID must match format EPC-[P]-[NNNN] (e.g., EPC-H-0001)"

    priority_code, _ = match.groups()
    if priority_code not in CODE_TO_PRIORITY:
        return False, f"Invalid priority code '{priority_code}' (must be C, H, M, or L)"

    return True, None


def get_next_epic_number(db: Database) -> int:
    """
    Get next sequential epic number across all priorities.

    Args:
        db: Database instance

    Returns:
        Next epic number
    """
    result = db.execute_query(
        """
        SELECT MAX(CAST(SUBSTR(id, 7, 4) AS INTEGER)) as max_number
        FROM epics
        WHERE id LIKE 'EPC-%'
        """
    )

    if result and result[0]["max_number"] is not None:
        return result[0]["max_number"] + 1

    return 1
