#!/usr/bin/env python3
"""
persona_show tool - Show persona details including mythology, description, and whimsical bio.

This tool:
1. Receives persona name from OpenCode
2. Fetches persona record from database
3. Returns all persona fields including bio (null if not yet generated)
"""

import sys
import json
from loguru import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.personas.manager import PersonaManager


def persona_to_dict(persona) -> dict:
    return {
        "name": persona.name,
        "role": persona.role,
        "mythology": persona.mythology,
        "description": persona.description,
        "whimsical_bio": persona.whimsical_bio,
        "mission_count": persona.mission_count,
        "last_mission_at": persona.last_mission_at.isoformat() if persona.last_mission_at else None,
        "created_at": persona.created_at.isoformat() if persona.created_at else None,
    }


def main():
    try:
        args = json.loads(sys.stdin.read())
        name = args.get("name")

        if not name:
            return json.dumps({"error": "missing_name", "message": "name is required."})

        logger.debug("persona_show_called", name=name)

        db_path = get_db_path()
        db = Database(db_path)
        manager = PersonaManager(db)

        persona = manager.get_persona(name.lower())

        if not persona:
            logger.warning("persona_not_found", name=name)
            return json.dumps(
                {
                    "error": "persona_not_found",
                    "message": f"Persona '{name}' not found.",
                }
            )

        logger.info("persona_shown", name=persona.name, has_bio=bool(persona.whimsical_bio))

        return json.dumps({"persona": persona_to_dict(persona)})

    except Exception as e:
        logger.exception("persona_show_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
