"""Mission management"""

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from site_nine.core.database import Database
from site_nine.core.paths import validate_path_within_project

# Prime-length word lists for deterministic codename generation
ADJECTIVES = [
    "swift",
    "silent",
    "bold",
    "clever",
    "quantum",
    "stellar",
    "epic",
    "crimson",
    "azure",
    "phantom",
    "iron",
    "silver",
    "rogue",
    "cosmic",
    "electric",
    "shadow",
    "titanium",
    "mystic",
    "storm",
    "ghost",
    "crystal",
    "rapid",
    "omega",
    "void",
    "neon",
    "plasma",
    "razor",
    "cyber",
    "dark",
    "chrome",
    "gamma",
]  # 31 entries (prime)

NOUNS = [
    "thunder",
    "phoenix",
    "shadow",
    "dragon",
    "nexus",
    "vortex",
    "cipher",
    "falcon",
    "sentinel",
    "tempest",
    "wraith",
    "cascade",
    "apex",
    "forge",
    "blade",
    "comet",
    "prism",
    "quasar",
    "raven",
    "typhoon",
    "vector",
    "aurora",
    "blaze",
    "echo",
    "griffin",
    "helix",
    "kraken",
    "nebula",
    "zenith",
    "matrix",
    "pulse",
    "specter",
    "vertex",
    "enigma",
    "hydra",
    "photon",
    "titan",
]  # 37 entries (prime)


def generate_mission_codename(mission_id: int) -> str:
    """
    Generate deterministic codename from mission ID using prime modulo.

    Using coprime prime numbers (31 and 37) ensures maximum distribution
    before collisions occur. First collision happens at mission #1,147.

    31 × 37 = 1,147 unique combinations
    """
    adjective = ADJECTIVES[mission_id % len(ADJECTIVES)]
    noun = NOUNS[mission_id % len(NOUNS)]
    return f"{adjective}-{noun}"


@dataclass
class Mission:
    """Mission data"""

    id: int | None
    persona_name: str
    role: str
    codename: str
    mission_file: str
    start_date: str
    start_time: str
    end_time: str | None
    objective: str
    created_at: str
    updated_at: str


class MissionManager:
    """Manages missions"""

    def __init__(self, db: Database) -> None:
        self.db = db

    def start_mission(self, persona_name: str, role: str, objective: str, mission_file: str | None = None) -> int:
        """Start a new mission"""
        from site_nine.core.paths import get_opencode_dir

        # Generate mission file name if not provided
        if not mission_file:
            now = datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")
            mission_file = f".opencode/work/missions/{date_str}.{time_str}.{role.lower()}.{persona_name}.md"

        # Insert into database (codename will be generated via trigger or after insert)
        result = self.db.execute_query(
            """
            INSERT INTO missions (
                persona_name, role, codename, mission_file,
                start_date, start_time, objective,
                created_at, updated_at
            )
            VALUES (
                :persona_name, :role, '', :mission_file,
                date('now'), time('now'), :objective,
                datetime('now'), datetime('now')
            )
            RETURNING id
            """,
            {
                "persona_name": persona_name,
                "role": role,
                "mission_file": mission_file,
                "objective": objective,
            },
        )

        mission_id = result[0]["id"]

        # Generate and update codename
        codename = generate_mission_codename(mission_id)
        self.db.execute_update(
            "UPDATE missions SET codename = :codename WHERE id = :id", {"codename": codename, "id": mission_id}
        )

        # Update persona usage
        self.db.execute_update(
            """
            UPDATE personas
            SET mission_count = mission_count + 1,
                last_mission_at = datetime('now')
            WHERE name = :persona_name
            """,
            {"persona_name": persona_name},
        )

        # Create the mission file
        self._create_mission_file(
            mission_file=mission_file,
            persona_name=persona_name,
            role=role,
            codename=codename,
            objective=objective,
        )

        return mission_id

    def _create_mission_file(
        self,
        mission_file: str,
        persona_name: str,
        role: str,
        codename: str,
        objective: str,
    ) -> None:
        """Create initial mission file with frontmatter and structure"""
        from site_nine.core.paths import get_opencode_dir

        # Get absolute path
        opencode_dir = get_opencode_dir()
        project_root = opencode_dir.parent
        mission_path = project_root / mission_file

        # Ensure parent directory exists
        mission_path.parent.mkdir(parents=True, exist_ok=True)

        # Get current datetime for timestamps
        now = datetime.now()
        start_date = now.strftime("%Y-%m-%d")
        start_time = now.strftime("%H:%M:%S")

        # Get persona info from database for mythology/description
        persona_info = self.db.execute_query(
            "SELECT mythology, description FROM personas WHERE name = :name", {"name": persona_name}
        )
        mythology = persona_info[0]["mythology"] if persona_info else "Unknown"
        description = persona_info[0]["description"] if persona_info else ""

        # Create mission file content
        content = f"""# Mission: {codename}

**Persona:** {persona_name} ({mythology} - {description})  
**Role:** {role}  
**Start:** {start_date} {start_time}  
**End:** TBD  
**Duration:** TBD  
**Objective:** {objective}

## Summary

[To be filled in during mission]

## Files Changed

[To be filled in during mission]

## Work Log

### {start_time[:5]} - Mission Start
- Summoned as {persona_name}, {role} persona
- Mission codename: {codename}
- Objective: {objective}

## Outcomes

[To be filled in during mission]

## Next Steps

[To be filled in during mission]

## Technical Notes

[To be filled in during mission]
"""

        # Write the file
        mission_path.write_text(content)

    def end_mission(self, mission_id: int) -> None:
        """End a mission and update both database and mission file"""
        # Get mission info first
        mission = self.get_mission(mission_id)
        if not mission:
            raise ValueError(f"Mission {mission_id} not found")

        # Get current time for end_time
        end_time = datetime.now().strftime("%H:%M:%S")

        # Update database
        self.db.execute_update(
            """
            UPDATE missions
            SET end_time = :end_time,
                updated_at = datetime('now')
            WHERE id = :mission_id
            """,
            {"mission_id": mission_id, "end_time": end_time},
        )

        # Update mission file if it exists
        if mission.mission_file:
            # Validate path to prevent directory traversal
            mission_path = validate_path_within_project(mission.mission_file)
            if mission_path.exists():
                self._update_mission_file_frontmatter(mission_path, end_time)

    def _update_mission_file_frontmatter(self, mission_path: Path, end_time: str) -> None:
        """Update YAML frontmatter in mission file"""
        content = mission_path.read_text()

        # Match YAML frontmatter block
        frontmatter_pattern = r"^---\n(.*?)\n---\n"
        match = re.match(frontmatter_pattern, content, re.DOTALL)

        if not match:
            # No frontmatter found, skip update
            return

        frontmatter_text = match.group(1)

        # Update the frontmatter text directly with regex to avoid YAML parsing issues
        # (YAML interprets HH:MM:SS as sexagesimal numbers)
        frontmatter_text = re.sub(r"(end_time:\s*).*", f"end_time: {end_time}", frontmatter_text)

        # Reconstruct file with updated frontmatter
        new_content = f"---\n{frontmatter_text}\n---\n" + content[match.end() :]

        # Write back to file
        mission_path.write_text(new_content)

    def list_missions(self, active_only: bool = False, role: str | None = None) -> list[Mission]:
        """List missions"""
        query = "SELECT * FROM missions WHERE 1=1"
        params = {}

        if active_only:
            query += " AND end_time IS NULL"

        if role:
            query += " AND role = :role"
            params["role"] = role

        query += " ORDER BY created_at DESC"

        rows = self.db.execute_query(query, params)
        return [Mission(**row) for row in rows]

    def get_mission(self, mission_id: int) -> Mission | None:
        """Get mission by ID"""
        rows = self.db.execute_query("SELECT * FROM missions WHERE id = :id", {"id": mission_id})
        return Mission(**rows[0]) if rows else None

    def update_mission(self, mission_id: int, objective: str | None = None, role: str | None = None) -> None:
        """Update mission metadata"""
        update_fields = ["updated_at = datetime('now')"]
        params: dict[str, int | str] = {"mission_id": mission_id}

        if objective is not None:
            update_fields.append("objective = :objective")
            params["objective"] = objective

        if role is not None:
            update_fields.append("role = :role")
            params["role"] = role

        query = f"UPDATE missions SET {', '.join(update_fields)} WHERE id = :mission_id"
        self.db.execute_update(query, params)
