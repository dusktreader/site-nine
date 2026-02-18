from dataclasses import dataclass
from typing import Any

from site_nine.core.database import Database
from site_nine.core.roles import Role
from site_nine.personas.exceptions import PersonaError
from site_nine.personas.models import Persona


@dataclass
class PersonaMission:
    """Lightweight mission record for persona usage history."""

    id: int
    persona_name: str
    role: str | None
    codename: str
    start_date: str | None
    start_time: str
    end_time: str | None

    @property
    def is_active(self) -> bool:
        return self.end_time is None

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> "PersonaMission":
        return cls(
            id=int(row["id"]),
            persona_name=str(row["persona_name"]),
            role=row.get("role"),
            codename=str(row["codename"]),
            start_date=row.get("start_date"),
            start_time=str(row["start_time"]),
            end_time=row.get("end_time"),
        )


class PersonaManager:
    """Manages persona CRUD operations and queries."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def validate_role(self, role: str) -> str:
        """
        Validate role name (case-insensitive) and return title case.

        Args:
            role: Role name to validate

        Returns:
            Title-cased role name

        Raises:
            PersonaError: If the role is invalid
        """
        try:
            Role.from_string(role)
        except ValueError:
            valid_roles_str = ", ".join(Role.all_values())
            raise PersonaError(f"Invalid role: {role}. Valid values: {valid_roles_str}")
        return role.title()

    def add_persona(
        self,
        name: str,
        role: str,
        mythology: str,
        description: str,
    ) -> Persona:
        """
        Add a new persona.

        Args:
            name: Persona name (will be lowercased)
            role: Primary role (will be validated and title-cased)
            mythology: Mythology origin
            description: Brief description

        Returns:
            The created Persona

        Raises:
            PersonaError: If the persona already exists or the role is invalid
        """
        name = name.lower()
        role = self.validate_role(role)

        try:
            rows = self.db.execute_query(
                """
                INSERT INTO personas (name, role, mythology, description)
                VALUES (:name, :role, :mythology, :description)
                RETURNING *
                """,
                {"name": name, "role": role, "mythology": mythology, "description": description},
            )
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                raise PersonaError(f"Persona '{name}' already exists")
            raise

        PersonaError.require_condition(len(rows) > 0, f"Failed to create persona '{name}'")
        return Persona.from_db_row(rows[0])

    def get_persona(self, name: str) -> Persona | None:
        """
        Get a persona by name.

        Args:
            name: Persona name (case-insensitive)

        Returns:
            Persona if found, None otherwise
        """
        rows = self.db.execute_query(
            "SELECT * FROM personas WHERE name = :name",
            {"name": name.lower()},
        )
        return Persona.from_db_row(rows[0]) if rows else None

    def list_personas(
        self,
        role: str | None = None,
        unused_only: bool = False,
        by_usage: bool = False,
    ) -> list[Persona]:
        """
        List personas with optional filtering and sorting.

        Args:
            role: Filter by role (validated, case-insensitive)
            unused_only: Show only personas with zero missions
            by_usage: Sort by mission count descending

        Returns:
            List of matching Personas
        """
        conditions = []
        params: dict[str, Any] = {}

        if role:
            role = self.validate_role(role)
            conditions.append("role = :role")
            params["role"] = role

        if unused_only:
            conditions.append("mission_count = 0")

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        order_by = "mission_count DESC, name ASC" if by_usage else "role ASC, name ASC"

        query = f"""
            SELECT *
            FROM personas
            WHERE {where_clause}
            ORDER BY {order_by}
        """

        rows = self.db.execute_query(query, params)
        return [Persona.from_db_row(row) for row in rows]

    def suggest_for_role(self, role: str, count: int = 3) -> list[Persona]:
        """
        Suggest unused or least-used personas for a role.

        Args:
            role: Role to suggest personas for (validated, case-insensitive)
            count: Maximum number of suggestions

        Returns:
            List of personas ordered by mission count ascending (least used first)
        """
        role = self.validate_role(role)

        rows = self.db.execute_query(
            """
            SELECT *
            FROM personas
            WHERE role = :role
            ORDER BY mission_count ASC, name ASC
            LIMIT :count
            """,
            {"role": role, "count": count},
        )
        return [Persona.from_db_row(row) for row in rows]

    def get_persona_missions(self, name: str) -> list[PersonaMission]:
        """
        Get mission history for a persona.

        Args:
            name: Persona name

        Returns:
            List of missions ordered by date descending
        """
        rows = self.db.execute_query(
            """
            SELECT id, persona_name, role, codename, start_date, start_time, end_time
            FROM missions
            WHERE persona_name = :name
            ORDER BY start_date DESC, start_time DESC
            """,
            {"name": name.lower()},
        )
        return [PersonaMission.from_db_row(row) for row in rows]

    def set_bio(self, name: str, bio: str) -> Persona:
        """
        Set whimsical bio for a persona.

        Args:
            name: Persona name
            bio: Whimsical bio text

        Returns:
            Updated Persona

        Raises:
            PersonaError: If persona not found
        """
        name = name.lower()

        rows = self.db.execute_query(
            """
            UPDATE personas SET whimsical_bio = :bio
            WHERE name = :name
            RETURNING *
            """,
            {"name": name, "bio": bio},
        )
        PersonaError.require_condition(len(rows) > 0, f"Persona '{name}' not found")
        return Persona.from_db_row(rows[0])
