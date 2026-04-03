from dataclasses import dataclass
from typing import Any, Self

import pendulum

from site_nine.core.utils import parse_timestamp

# Roman numeral conversion table (descending order)
_ROMAN_NUMERALS = [
    (1000, "M"),
    (900, "CM"),
    (500, "D"),
    (400, "CD"),
    (100, "C"),
    (90, "XC"),
    (50, "L"),
    (40, "XL"),
    (10, "X"),
    (9, "IX"),
    (5, "V"),
    (4, "IV"),
    (1, "I"),
]


def to_roman(n: int) -> str:
    """
    Convert a positive integer to a Roman numeral string.

    Args:
        n: Positive integer to convert

    Returns:
        Roman numeral string (e.g., 3 → 'III', 14 → 'XIV')

    Raises:
        ValueError: If n is not a positive integer
    """
    if not isinstance(n, int) or n <= 0:
        raise ValueError(f"Cannot convert {n!r} to roman numeral: must be a positive integer")
    result = []
    for value, numeral in _ROMAN_NUMERALS:
        while n >= value:
            result.append(numeral)
            n -= value
    return "".join(result)


@dataclass
class Daemon:
    """
    Daemon data model.

    Attributes:
        name: Daemon name (lowercase, e.g., 'lucifer', 'asmodeus')
        role: Primary role this daemon suits (title case)
        daemonology: Whimsical first-person bio (3-5 sentences, generated lazily)
        personality: Terse trait string (e.g., 'methodical, blunt')
        incarnations: How many times this daemon has been summoned
        last_possession: Timestamp of last summoning
        created_at: Timestamp when the daemon was created
    """

    name: str
    role: str
    daemonology: str | None
    personality: str | None
    incarnations: int
    last_possession: pendulum.DateTime | None
    created_at: pendulum.DateTime

    @property
    def incarnation(self) -> int:
        """
        Current incarnation number (same as total incarnations count).

        Returns 0 if this daemon has never been summoned.
        """
        return self.incarnations

    @property
    def incarnation_label(self) -> str | None:
        """
        Roman numeral label for the current incarnation.

        Returns None if the daemon has never been summoned (incarnations == 0).
        Returns 'I', 'II', 'III', etc. for summoned daemons.
        """
        if self.incarnations == 0:
            return None
        return to_roman(self.incarnations)

    @property
    def display_name(self) -> str:
        """
        Display name with roman numeral incarnation suffix if summoned.

        Returns 'Azazel' for a never-summoned daemon, or 'Azazel III' for
        the third incarnation.
        """
        label = self.incarnation_label
        if label is None:
            return self.name.capitalize()
        return f"{self.name.capitalize()} {label}"

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> Self:
        """
        Create Daemon from database row dictionary.

        Args:
            row: Database row dictionary

        Returns:
            Daemon instance with parsed timestamps
        """
        created_at = parse_timestamp(row["created_at"])

        last_possession: pendulum.DateTime | None = None
        if row.get("last_possession"):
            last_possession = parse_timestamp(row["last_possession"])

        return cls(
            name=str(row["name"]),
            role=str(row["role"]),
            daemonology=row.get("daemonology"),
            personality=row.get("personality"),
            incarnations=int(row["incarnations"]),
            last_possession=last_possession,
            created_at=created_at,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "role": self.role,
            "daemonology": self.daemonology,
            "personality": self.personality,
            "incarnations": self.incarnations,
            "incarnation": self.incarnation,
            "incarnation_label": self.incarnation_label,
            "display_name": self.display_name,
            "last_possession": self.last_possession.isoformat() if self.last_possession else None,
            "created_at": self.created_at.isoformat(),
        }
