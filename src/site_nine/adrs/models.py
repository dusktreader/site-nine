import re
from dataclasses import dataclass
from typing import Any, Self

import pendulum
from buzz import handle_errors

from site_nine.adrs.types import ADRStatus
from site_nine.core.utils import parse_timestamp


@dataclass
class ArchitectureDoc:
    """
    Architecture Decision Record (ADR) data model

    ADRs are documents that capture important architectural decisions made during development.
    They can be linked to epics and tasks to show which decisions informed which work items.
    """

    UPDATABLE_FIELDS = {"title", "status", "file_path"}

    id: str
    title: str
    status: ADRStatus
    file_path: str
    created_at: pendulum.DateTime | None = None
    updated_at: pendulum.DateTime | None = None

    def __post_init__(self):
        """Validate ADR fields after initialization"""
        self._validate_id()

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> Self:
        """
        Create ArchitectureDoc from database row dictionary.

        Args:
            row: Database row dictionary

        Returns:
            ArchitectureDoc instance with parsed timestamps
        """
        created_at_str = row.get("created_at")
        updated_at_str = row.get("updated_at")

        created_at: pendulum.DateTime | None = None
        if created_at_str:
            created_at = parse_timestamp(created_at_str)

        updated_at: pendulum.DateTime | None = None
        if updated_at_str:
            updated_at = parse_timestamp(updated_at_str)

        return cls(
            id=str(row["id"]),
            title=str(row["title"]),
            status=cls._parse_status(str(row["status"])),
            file_path=str(row["file_path"]),
            created_at=created_at,
            updated_at=updated_at,
        )

    @staticmethod
    def _parse_status(status: str | ADRStatus) -> ADRStatus:
        """
        Parse status string to ADRStatus enum.

        Args:
            status: Status value (string or enum)

        Returns:
            ADRStatus enum value
        """
        if isinstance(status, ADRStatus):
            return status

        with handle_errors(
            f"Invalid ADR status: {status}. Valid statuses: {ADRStatus.pretty_list()}",
            raise_exc_class=ValueError,
        ):
            return ADRStatus(status)

    def _validate_id(self) -> None:
        """Validate ADR ID format (ADR-NNN)"""
        if not re.match(r"^ADR-\d{3}$", self.id):
            raise ValueError(f"Invalid ADR ID format: {self.id}. Expected format: ADR-001")

    @property
    def is_active(self) -> bool:
        """Check if ADR is active (PROPOSED or ACCEPTED)"""
        return self.status in (ADRStatus.PROPOSED, ADRStatus.ACCEPTED)
