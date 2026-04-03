#!/usr/bin/env python3
"""
possession_summary tool - Generate a summary of files, commits, and tasks for the current possession.

This tool:
1. Receives context.sessionID and optional possession_id override
2. Looks up the possession (by session or direct ID)
3. Calls PossessionManager.generate_summary to collect git file changes, commits, and tasks
4. Returns structured summary JSON
"""

import sys
import json
from tool_logging import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.possessions.manager import PossessionManager


def main():
    try:
        context = json.loads(sys.stdin.read())
        session_id = context.get("session_id")
        possession_id_override = context.get("possession_id")

        logger.debug("possession_summary called", session_id=session_id, possession_id_override=possession_id_override)

        db_path = get_db_path()
        db = Database(db_path)
        manager = PossessionManager(db)

        # Resolve possession_id
        if possession_id_override is not None:
            possession_id = int(possession_id_override)
            possession = manager.get_possession(possession_id)
            if not possession:
                return json.dumps(
                    {
                        "error": "possession_not_found",
                        "message": f"Possession {possession_id} not found",
                    }
                )
        else:
            if not session_id:
                return json.dumps(
                    {
                        "error": "no_session_id",
                        "message": "No session_id provided and no possession_id override",
                    }
                )

            rows = db.execute_query(
                """
                SELECT id FROM possessions
                WHERE opencode_session_id = :session_id
                ORDER BY created_at DESC
                LIMIT 1
                """,
                {"session_id": session_id},
            )

            if not rows:
                return json.dumps(
                    {
                        "error": "no_possession",
                        "message": f"No possession found for session {session_id}",
                    }
                )

            possession_id = rows[0]["id"]
            possession = manager.get_possession(possession_id)
            if not possession:
                return json.dumps(
                    {
                        "error": "possession_not_found",
                        "message": f"Possession {possession_id} not found",
                    }
                )

        # Generate summary
        summary = manager.generate_summary(possession_id)

        logger.info(
            "possession_summary_generated",
            possession_id=possession_id,
            files_changed=len(summary.files_changed),
            commits=len(summary.commits),
            tasks=len(summary.tasks),
        )

        return json.dumps(
            {
                "possession_id": possession.id,
                "daemon_name": possession.daemon_name,
                "role": possession.role,
                "status": possession.status.value if hasattr(possession.status, "value") else str(possession.status),
                "start_time": possession.start_time,
                "files_changed": [{"status": fc.status, "file": fc.file} for fc in summary.files_changed],
                "commits": summary.commits,
                "tasks": [{"id": t.id, "title": t.title, "status": t.status} for t in summary.tasks],
                "warnings": summary.warnings,
            }
        )

    except Exception as e:
        logger.exception("possession_summary_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
