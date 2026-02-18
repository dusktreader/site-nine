"""Canonical role definitions for site-nine."""

from typing import Self

from auto_name_enum import AutoNameEnum, autodoc


class Role(AutoNameEnum):
    """Agent roles with descriptions."""

    ADMINISTRATOR = autodoc("Manages project configuration, infrastructure, and system administration")
    ARCHITECT = autodoc("Designs system architecture, technical decisions, and high-level structure")
    ENGINEER = autodoc("Implements features, writes code, and builds functionality")
    TESTER = autodoc("Writes and runs tests, ensures quality and correctness")
    DOCUMENTARIAN = autodoc("Creates documentation, guides, and written explanations")
    DESIGNER = autodoc("Designs user interfaces, user experience, and visual elements")
    INSPECTOR = autodoc("Reviews code, audits quality, and identifies improvements")
    OPERATOR = autodoc("Handles deployment, operations, and runtime management")
    HISTORIAN = autodoc("Documents project history and decisions")

    @property
    def title_case(self) -> str:
        """Return the role value in title case (e.g. 'Engineer' instead of 'ENGINEER')."""
        return self.value.title()

    @classmethod
    def from_string(cls, value: str) -> Self:
        """Convert string to Role enum (case-insensitive)."""
        for member in cls:
            if member.value.lower() == value.lower():
                return member
        valid_values = ", ".join(m.title_case for m in cls)
        raise ValueError(f"Invalid role: {value}. Valid values: {valid_values}")

    @classmethod
    def all_values(cls) -> list[str]:
        """Get list of all role values (title case)."""
        return [role.title_case for role in cls]

    @classmethod
    def all_lowercase(cls) -> list[str]:
        """Get list of all role values (lowercase)."""
        return [role.value.lower() for role in cls]
