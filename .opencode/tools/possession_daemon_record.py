#!/usr/bin/env python3
"""
possession_daemon_record tool - Record daemon selection for a pending possession.

This tool:
1. Receives possession_id and optional daemon name
2. If daemon is not provided, atomically claims the least-used daemon for the possession's role
3. Validates possession exists and is in DAEMON_PENDING status
4. Validates daemon exists in the daemons table (if provided)
5. Updates possession: daemon_name, possession_log, start_time
6. Transitions status from DAEMON_PENDING to ACTIVE
7. Returns updated possession info
"""

import sys
import json
import pendulum
from tool_logging import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.core.utils import utc_now
from site_nine.possessions.manager import PossessionManager
from site_nine.possessions.types import PossessionStatus
from site_nine.daemons.manager import DaemonManager


def main():
    try:
        # Read context from stdin
        context = json.loads(sys.stdin.read())
        possession_id = context["possession_id"]
        daemon_input = context.get("daemon")  # Optional

        # Normalize daemon name if provided
        daemon = daemon_input.lower().strip() if daemon_input else None

        logger.debug(
            "possession_daemon_record called",
            possession_id=possession_id,
            daemon=daemon,
            auto_claim=daemon is None,
        )

        # Connect to database
        db_path = get_db_path()
        db = Database(db_path)

        # Fetch possession
        rows = db.execute_query(
            "SELECT id, role, status FROM possessions WHERE id = :possession_id",
            {"possession_id": possession_id},
        )

        if not rows:
            return json.dumps(
                {
                    "error": "possession_not_found",
                    "message": f"Possession {possession_id} not found",
                }
            )

        possession = rows[0]

        if possession["status"] != PossessionStatus.DAEMON_PENDING.value:
            return json.dumps(
                {
                    "error": "invalid_status",
                    "message": f"Possession {possession_id} is in status '{possession['status']}', expected '{PossessionStatus.DAEMON_PENDING.value}'",
                    "current_status": possession["status"],
                }
            )

        if not possession["role"]:
            return json.dumps(
                {
                    "error": "role_not_set",
                    "message": f"Possession {possession_id} has no role set — run possession_role_record first",
                }
            )

        role = possession["role"]
        daemon_manager = DaemonManager(db)

        # Handle daemon selection: auto-claim or validate manual selection
        if daemon is None:
            # Auto-claim: atomically select and claim least-used daemon.
            # Returns None when no daemons exist for the role OR all were
            # summoned within the last 3 days → invention required.
            claimed_daemon = daemon_manager.summon_daemon(role)
            if claimed_daemon is None:
                return json.dumps(
                    {
                        "action": "invent_required",
                        "role": role,
                        "possession_id": possession_id,
                        "prompt": (
                            "New daemon names should feel consistent with the naming conventions of "
                            "the Ars Goetia and Pseudomonarchia Daemonum — rooted in Latin, Hebrew, "
                            "or Aramaic phonetics, with the gravity and specificity of a named entity "
                            "in a grimoire. Avoid fantasy-generic constructions."
                        ),
                        "instructions": (
                            "Generate: (1) a new daemon name following the prompt above, "
                            "(2) a personality — a terse trait string (e.g. 'methodical, blunt, relentless'), "
                            "(3) a daemonology — a grimoire-style first-person bio, 3–5 sentences. "
                            "Then call `add_daemon` (or `s9 daemon add`) to INSERT the new daemon with "
                            "the generated name, role, personality, and daemonology. "
                            "Finally, call `possession_daemon_record` again with the invented daemon name."
                        ),
                    }
                )
            daemon = claimed_daemon.name
            logger.info(
                "daemon_auto_claimed",
                possession_id=possession_id,
                role=role,
                daemon=daemon,
            )
        else:
            # Manual selection: validate daemon exists
            daemon_rows = db.execute_query(
                "SELECT name FROM daemons WHERE lower(name) = :name",
                {"name": daemon},
            )

            if not daemon_rows:
                return json.dumps(
                    {
                        "error": "daemon_not_found",
                        "message": f"Daemon '{daemon}' not found in daemons table",
                    }
                )

            # Update daemon usage stats (manual selection only - auto-claim via summon_daemon already did this)
            now_str = utc_now()
            db.execute_update(
                """
                UPDATE daemons
                SET incarnations = incarnations + 1,
                    last_possession = :now
                WHERE lower(name) = :daemon
                """,
                {"now": now_str, "daemon": daemon},
            )

        # Compute possession log path and timestamps
        now = pendulum.now("UTC")
        date_str = now.format("YYYY-MM-DD")
        time_str = now.format("HH:mm:ss")
        possession_log = f".opencode/work/possessions/{date_str}.{time_str}.{role.lower()}.{daemon}.md"

        now_str = utc_now()

        # Update possession record
        db.execute_update(
            """
            UPDATE possessions
            SET daemon_name = :daemon,
                possession_log = :possession_log,
                start_time = :start_time,
                status = :new_status,
                last_heartbeat_at = :now,
                updated_at = :now
            WHERE id = :possession_id
            """,
            {
                "daemon": daemon,
                "possession_log": possession_log,
                "start_time": time_str,
                "new_status": PossessionStatus.ACTIVE.value,
                "now": now_str,
                "possession_id": possession_id,
            },
        )

        logger.info(
            "possession_daemon_recorded",
            possession_id=possession_id,
            daemon=daemon,
            role=role,
            possession_log=possession_log,
        )

        return json.dumps(
            {
                "possession_id": possession_id,
                "daemon": daemon,
                "role": role,
                "status": PossessionStatus.ACTIVE.value,
                "possession_log": possession_log,
            }
        )

    except Exception as e:
        logger.exception("possession_daemon_record_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
