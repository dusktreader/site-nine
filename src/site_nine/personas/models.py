from dataclasses import dataclass
from typing import Any, Self

import pendulum

from site_nine.core.utils import parse_timestamp


@dataclass
class Persona:
    """
    Persona data model.

    Attributes:
        name: Persona name (lowercase, e.g., 'atlas', 'terminus')
        role: Primary role this persona suits (title case)
        mythology: Mythology/religion origin (e.g., 'Greek', 'Roman', 'Norse')
        description: Brief description of the deity/daemon
        whimsical_bio: Whimsical first-person bio (3-5 sentences, generated lazily)
        mission_count: How many times this persona has been used
        last_mission_at: Timestamp of last usage
        created_at: Timestamp when the persona was created
    """

    name: str
    role: str
    mythology: str
    description: str
    whimsical_bio: str | None
    mission_count: int
    last_mission_at: pendulum.DateTime | None
    created_at: pendulum.DateTime

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> Self:
        """
        Create Persona from database row dictionary.

        Args:
            row: Database row dictionary

        Returns:
            Persona instance with parsed timestamps
        """
        created_at = parse_timestamp(row["created_at"])

        last_mission_at: pendulum.DateTime | None = None
        if row.get("last_mission_at"):
            last_mission_at = parse_timestamp(row["last_mission_at"])

        return cls(
            name=str(row["name"]),
            role=str(row["role"]),
            mythology=str(row["mythology"]),
            description=str(row["description"]),
            whimsical_bio=row.get("whimsical_bio"),
            mission_count=int(row["mission_count"]),
            last_mission_at=last_mission_at,
            created_at=created_at,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "role": self.role,
            "mythology": self.mythology,
            "description": self.description,
            "whimsical_bio": self.whimsical_bio,
            "mission_count": self.mission_count,
            "last_mission_at": self.last_mission_at.isoformat() if self.last_mission_at else None,
            "created_at": self.created_at.isoformat(),
        }
