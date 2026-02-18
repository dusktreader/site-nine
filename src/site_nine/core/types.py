"""Shared types used across multiple domain packages."""

from typing import Self

from auto_name_enum import AutoNameEnum, auto


class Priority(AutoNameEnum):
    """
    Priority levels for tasks and epics.

    Attributes:
        CRITICAL: Must be done immediately
        HIGH: Important, should be done soon
        MEDIUM: Normal priority
        LOW: Can wait, do when convenient
    """

    CRITICAL = auto()
    HIGH = auto()
    MEDIUM = auto()
    LOW = auto()

    @classmethod
    def from_string(cls, value: str) -> Self:
        """Convert string to Priority enum (case-insensitive)."""
        value_upper = value.upper()
        for member in cls:
            if member.value.upper() == value_upper:
                return member
        raise ValueError(f"Invalid priority: {value}. Valid values: {', '.join(m.value for m in cls)}")
