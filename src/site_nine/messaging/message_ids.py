"""Message ID utilities and validation"""

import re

from buzz import enforce_defined, require_condition

# Priority codes (same as tasks)
PRIORITY_CODES = {
    "CRITICAL": "C",
    "HIGH": "H",
    "MEDIUM": "M",
    "LOW": "L",
}

# Reverse mapping
CODE_TO_PRIORITY = {v: k for k, v in PRIORITY_CODES.items()}

# Message ID format: MSG-PRIORITY-NUMBER (e.g., MSG-H-0001)
MESSAGE_ID_PATTERN = re.compile(r"^MSG-([CHML])-(\d{4})$")


def validate_message_id(message_id: str) -> None:
    """
    Validate message ID format.

    Args:
        message_id: Message ID to validate (e.g., "MSG-H-0001")

    Raises:
        ValueError: If message ID format is invalid
    """
    match = enforce_defined(
        MESSAGE_ID_PATTERN.match(message_id),
        "Invalid format. Expected: MSG-PRIORITY-NUMBER (e.g., MSG-H-0001)",
        raise_exc_class=ValueError,
    )

    priority_code, number = match.groups()

    require_condition(
        priority_code in CODE_TO_PRIORITY,
        f"Invalid priority code '{priority_code}'. Valid: C, H, M, L",
        raise_exc_class=ValueError,
    )

    num = int(number)
    require_condition(1 <= num <= 9999, "Number must be between 0001 and 9999", raise_exc_class=ValueError)


def parse_message_id(message_id: str) -> tuple[str, int] | None:
    """
    Parse message ID into components.

    Args:
        message_id: Message ID (e.g., "MSG-H-0001")

    Returns:
        Tuple of (priority, number) or None if invalid
    """
    match = MESSAGE_ID_PATTERN.match(message_id)
    if not match:
        return None

    priority_code, number = match.groups()
    priority = CODE_TO_PRIORITY.get(priority_code)

    if not priority:
        return None

    return priority, int(number)


def format_message_id(priority: str, number: int) -> str:
    """
    Format message ID from components.

    Args:
        priority: Priority level (e.g., "HIGH")
        number: Sequential number (1-9999)

    Returns:
        Formatted message ID (e.g., "MSG-H-0001")

    Raises:
        ValueError: If any component is invalid
    """
    priority_code = enforce_defined(
        PRIORITY_CODES.get(priority), f"Invalid priority: {priority}", raise_exc_class=ValueError
    )

    message_id = f"MSG-{priority_code}-{number:04d}"
    validate_message_id(message_id)
    return message_id


def get_next_message_number(db) -> int:
    """
    Get next available message number (global counter).

    Args:
        db: Database instance

    Returns:
        Next sequential number (1-9999)
    """
    result = db.execute_query(
        """
        SELECT MAX(CAST(SUBSTR(id, -4) AS INTEGER)) as max_num
        FROM messages
        """
    )

    max_num = result[0]["max_num"]
    if max_num is None:
        return 1

    return max_num + 1


def sort_message_ids(message_ids: list[str]) -> list[str]:
    """
    Sort message IDs by priority (descending), then number.

    Args:
        message_ids: List of message IDs

    Returns:
        Sorted list of message IDs

    Raises:
        ValueError: If any message ID is invalid
    """
    priority_order = {"C": 0, "H": 1, "M": 2, "L": 3}

    def sort_key(message_id: str) -> tuple:
        match = enforce_defined(
            MESSAGE_ID_PATTERN.match(message_id), f"Invalid message ID format: {message_id}", raise_exc_class=ValueError
        )
        priority_code, number = match.groups()
        return (priority_order.get(priority_code, 999), int(number))

    return sorted(message_ids, key=sort_key)
