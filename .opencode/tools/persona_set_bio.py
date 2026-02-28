#!/usr/bin/env python3
"""
persona_set_bio tool - Set or update the whimsical bio for a persona.

This tool:
1. Receives persona name and bio text from OpenCode
2. Updates the whimsical_bio field in the database
3. Returns the updated persona details
"""

import sys
import json
from loguru import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.personas.manager import PersonaManager
from site_nine.personas.exceptions import PersonaError


def main():
    try:
        args = json.loads(sys.stdin.read())
        name = args.get("name")
        bio = args.get("bio")

        if not name:
            return json.dumps({"error": "missing_name", "message": "name is required."})
        if not bio:
            return json.dumps({"error": "missing_bio", "message": "bio is required."})

        logger.debug("persona_set_bio_called", name=name, bio_length=len(bio))

        db_path = get_db_path()
        db = Database(db_path)
        manager = PersonaManager(db)

        try:
            updated = manager.set_bio(name.lower(), bio)
        except PersonaError as e:
            logger.warning("persona_set_bio_failed", name=name, error=str(e))
            return json.dumps({"error": "update_failed", "message": str(e)})

        logger.info("persona_bio_set", name=updated.name)

        return json.dumps(
            {
                "name": updated.name,
                "role": updated.role,
                "mythology": updated.mythology,
                "whimsical_bio": updated.whimsical_bio,
            }
        )

    except Exception as e:
        logger.exception("persona_set_bio_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
