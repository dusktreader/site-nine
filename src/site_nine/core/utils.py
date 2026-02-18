"""Core utility functions"""

from typing import Any

import pendulum
from buzz import ensure_type


def parse_timestamp(value: Any) -> pendulum.DateTime:
    """
    Parse a timestamp value into a UTC pendulum DateTime.

    Converts the value to string, parses it with pendulum, and ensures
    the result is a timezone-aware pendulum.DateTime in UTC.

    If the parsed timestamp has no timezone info, it is assumed to be UTC.
    If it has a timezone, it is converted to UTC.

    Args:
        value: The timestamp value to parse (from database row)

    Returns:
        Parsed timestamp as pendulum.DateTime in UTC

    Raises:
        ParsingException: If the timestamp cannot be parsed
    """
    parsed = ensure_type(pendulum.parse(str(value)), pendulum.DateTime)
    if parsed.timezone is None or parsed.timezone_name is None:
        # Naive timestamp: assume UTC
        return parsed.in_tz("UTC")
    return parsed.in_tz("UTC")


def utc_now() -> str:
    """
    Get the current UTC time as an ISO-8601 string with timezone.

    Returns a string like '2026-02-14T23:05:00+00:00' suitable for
    storing in the database and passing as SQL parameters.

    All timestamps in the database should use this format.

    Returns:
        Current UTC time as ISO-8601 string with +00:00 suffix
    """
    return pendulum.now("UTC").to_iso8601_string()
