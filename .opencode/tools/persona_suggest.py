#!/usr/bin/env python3
"""
persona_suggest tool - Suggest unused or least-used persona names for a given role.

This tool:
1. Receives role and optional count from OpenCode
2. Queries the personas table ordered by mission_count ASC (least-used first)
3. Returns the top N suggestions with name, mythology, description, and usage info
"""

import sys
import json
from loguru import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.personas.manager import PersonaManager


def persona_to_dict(persona) -> dict:
    """Serialize a Persona to a JSON-safe dict."""
    return {
        "name": persona.name,
        "role": persona.role,
        "mythology": persona.mythology,
        "description": persona.description,
        "mission_count": persona.mission_count,
        "last_mission_at": persona.last_mission_at.isoformat() if persona.last_mission_at else None,
        "is_unused": persona.mission_count == 0,
    }


def main():
    try:
        args = json.loads(sys.stdin.read())

        role = args.get("role")
        count = args.get("count", 3)

        if not role:
            return json.dumps({"error": "missing_role", "message": "role is required."})

        logger.debug("persona_suggest called", role=role, count=count)

        db_path = get_db_path()
        db = Database(db_path)
        manager = PersonaManager(db)

        suggestions = manager.suggest_for_role(role, count=count)

        logger.info("persona_suggestions_returned", role=role, count=len(suggestions))

        return json.dumps(
            {
                "data": [persona_to_dict(p) for p in suggestions],
                "count": len(suggestions),
                "role": role,
            }
        )

    except Exception as e:
        logger.exception("persona_suggest_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
