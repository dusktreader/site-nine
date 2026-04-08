#!/usr/bin/env python3
"""
summon_minion tool - Summon a minion-mode worker for a given role.

This tool:
1. Receives role, optional daemon, model, and poll_interval
2. Spawns minion_worker.py as a fully detached background process
3. Waits for the minion to initialize and create its possession
4. Returns the summoned possession ID for subsequent coordination

This is the ONLY way for Admin agents to summon minions. Never use 's9 summon' CLI directly.
"""

import sys
import json
import subprocess
import time
from pathlib import Path
from tool_logging import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path


def main():
    try:
        args = json.loads(sys.stdin.read())

        role = args.get("role")
        daemon = args.get("daemon")
        model = args.get("model") or "github-copilot/claude-sonnet-4.6"
        poll_interval = args.get("poll_interval") or 30

        if not role:
            return json.dumps({"error": "missing_role", "message": "role is required."})

        # Validate role
        valid_roles = [
            "Administrator",
            "Architect",
            "Engineer",
            "Tester",
            "Documentarian",
            "Designer",
            "Inspector",
            "Operator",
            "Historian",
        ]

        # Auto-capitalize first letter if needed
        role = role.capitalize()

        if role not in valid_roles:
            return json.dumps(
                {
                    "error": "invalid_role",
                    "message": f"Invalid role '{role}'. Valid roles: {', '.join(valid_roles)}",
                }
            )

        logger.debug("summon_minion_called", role=role, daemon=daemon, model=model, poll_interval=poll_interval)

        # Find minion_worker.py module
        tool_dir = Path(__file__).resolve().parent
        repo_root = tool_dir.parent.parent
        minion_worker_script = repo_root / "src" / "site_nine" / "workers" / "minion_worker.py"

        if not minion_worker_script.exists():
            return json.dumps(
                {
                    "error": "script_not_found",
                    "message": f"minion_worker.py not found at {minion_worker_script}",
                }
            )

        # Build command
        cmd = ["uv", "run", "python", str(minion_worker_script), role]
        if daemon:
            cmd.extend(["--daemon", daemon])
        cmd.extend(["--model", model])
        cmd.extend(["--poll-interval", str(poll_interval)])

        logger.info("summon_minion_starting", role=role, daemon=daemon, command=" ".join(cmd))

        # Redirect worker stdout/stderr to a per-role log file so the process can
        # run fully detached. Using PIPE would cause the worker to block once the
        # pipe buffer fills (minion_worker.py produces substantial output during the
        # opencode-run initialization phase), and the buffer would be orphaned
        # when summon_minion exits — killing the worker process.
        log_dir = Path.home() / ".local" / "state" / "site-nine" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"minion-worker-{role.lower()}.log"

        log_file = open(log_path, "a")

        # Spawn worker as a fully detached background process.
        # start_new_session=True detaches it from our process group so it is not
        # killed when the parent (summon_minion.py / Bun) exits.
        process = subprocess.Popen(
            cmd,
            cwd=str(repo_root),
            stdout=log_file,
            stderr=log_file,
            start_new_session=True,
        )

        # Wait for worker to initialize and create possession (up to 120 seconds)
        logger.debug("summon_minion_waiting_for_init", role=role)

        possession_id = None
        daemon_name = None
        max_attempts = 120
        for attempt in range(max_attempts):
            time.sleep(1)

            # Check if process died unexpectedly (only treat as error after 10s grace period)
            if attempt > 10 and process.poll() is not None:
                log_file.flush()
                log_tail = log_path.read_text()[-2000:] if log_path.exists() else "(no log)"
                return json.dumps(
                    {
                        "error": "worker_died",
                        "message": f"Worker process exited unexpectedly with code {process.returncode}",
                        "log_tail": log_tail,
                        "log_path": str(log_path),
                    }
                )

            # Check database for newly created ACTIVE possession for this role
            db = Database(get_db_path())
            rows = db.execute_query(
                """
                SELECT id, daemon_name FROM possessions
                WHERE role = :role
                  AND status = 'ACTIVE'
                  AND end_time IS NULL
                ORDER BY created_at DESC
                LIMIT 1
                """,
                {"role": role},
            )

            if rows:
                possession_id = rows[0]["id"]
                daemon_name = rows[0]["daemon_name"]
                logger.info("summon_minion_success", possession_id=possession_id, role=role, daemon=daemon_name)
                break

        if possession_id is None:
            # Timeout - kill the process
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            return json.dumps(
                {
                    "error": "init_timeout",
                    "message": f"Worker initialization timed out after {max_attempts} seconds. Possession not created.",
                    "log_path": str(log_path),
                }
            )

        return json.dumps(
            {
                "possession_id": possession_id,
                "role": role,
                "daemon": daemon_name,
                "model": model,
                "poll_interval": poll_interval,
                "status": "summoned",
                "message": f"Minion summoned successfully. Possession #{possession_id} ({daemon_name}, {role}) is now polling for messages.",
                "log_path": str(log_path),
            }
        )

    except Exception as e:
        logger.exception("summon_minion_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
