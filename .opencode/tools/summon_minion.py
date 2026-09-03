#!/usr/bin/env python3
"""
summon_minion tool - Summon a minion-mode worker for a given role.

This tool:
1. Receives role, optional daemon, model, and poll_interval
2. Generates a UUID spawn token and passes it to minion_worker.py
3. Spawns minion_worker.py as a fully detached background process
4. Polls for a status file written by the worker after initialization
5. Returns the summoned possession ID for subsequent coordination

The spawn-token mechanism eliminates the race condition that occurred when two
same-role workers were spawned concurrently: the old code queried the DB for
the most recent ACTIVE possession of the given role and could cross-assign IDs.
Now each spawn uses a unique token, and the worker writes its exact possession
ID to ``~/.local/state/site-nine/workers/<token>.json`` after initializing.

This is the ONLY way for Admin agents to summon minions. Never use 's9 summon' CLI directly.
"""

import json
import os
import sys
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path
from tool_logging import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path, get_project_root
from site_nine.workers.journal import DeskWorkerJournal


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

        # --- Spawn-token setup (ADR-016, Fix 5) ---
        # Generate a unique token for this spawn so the worker can write a
        # status file we can poll instead of racing on the DB by role.
        spawn_token = uuid.uuid4().hex
        status_dir = Path.home() / ".local" / "state" / "site-nine" / "workers"
        status_dir.mkdir(parents=True, exist_ok=True)
        status_file = status_dir / f"{spawn_token}.json"

        # Build command
        cmd = ["uv", "run", "python", str(minion_worker_script), role]
        if daemon:
            cmd.extend(["--daemon", daemon])
        cmd.extend(["--model", model])
        cmd.extend(["--poll-interval", str(poll_interval)])
        cmd.extend(["--spawn-token", spawn_token])

        logger.info("summon_minion_starting", role=role, daemon=daemon, command=" ".join(cmd))

        # Redirect worker stdout/stderr to a log file. The worker also manages its own
        # loguru file sink (via _configure_worker_logging), but capturing the process-level
        # stdout/stderr here ensures that any crash before loguru is configured (e.g. an
        # import error) is not silently lost.
        log_dir = Path.home() / ".local" / "state" / "site-nine" / "workers" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        proc_log_path = log_dir / f"minion-{role.lower()}-{spawn_token[:8]}.proc.log"
        proc_log_file = open(proc_log_path, "w")

        # Spawn worker as a fully detached background process.
        # start_new_session=True detaches it from our process group so it is not
        # killed when the parent (summon_minion.py / Bun) exits.
        process = subprocess.Popen(
            cmd,
            cwd=str(repo_root),
            stdout=proc_log_file,
            stderr=proc_log_file,
            start_new_session=True,
        )

        # Poll for the spawn-token status file written by the worker after init.
        # This replaces the role-based DB query that was susceptible to race
        # conditions when two same-role workers were spawned concurrently.
        logger.debug("summon_minion_waiting_for_spawn_token", role=role, spawn_token=spawn_token)

        possession_id = None
        daemon_name = None
        possession_created_at = None
        max_attempts = 600  # 10-minute timeout — opencode run with possession-start can take several minutes
        for attempt in range(max_attempts):
            time.sleep(1)

            # Check if process died unexpectedly (only treat as error after 60s grace period)
            # opencode run can take 30-60s to boot, call the model, and complete init.
            if attempt > 60 and process.poll() is not None:
                _cleanup_status_file(status_file)
                return json.dumps(
                    {
                        "error": "worker_died",
                        "message": f"Worker process exited unexpectedly with code {process.returncode}",
                    }
                )

            # Check for spawn-token status file written by the worker
            if status_file.exists():
                try:
                    data = json.loads(status_file.read_text(encoding="utf-8"))
                    if data.get("status") == "ready":
                        possession_id = data["possession_id"]
                        daemon_name = data["daemon"]
                        logger.info(
                            "summon_minion_token_file_found",
                            possession_id=possession_id,
                            role=role,
                            daemon=daemon_name,
                        )
                        _cleanup_status_file(status_file)
                        break
                except (json.JSONDecodeError, KeyError):
                    # File may be partially written; try again next cycle
                    pass

        if possession_id is None:
            # Timeout - kill the process and clean up
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            _cleanup_status_file(status_file)
            return json.dumps(
                {
                    "error": "init_timeout",
                    "message": f"Worker initialization timed out after {max_attempts} seconds. Possession not created.",
                }
            )

        # Retrieve possession metadata (created_at) from the DB for journal path derivation.
        db = Database(get_db_path())
        rows = db.execute_query(
            "SELECT created_at, daemon_name FROM possessions WHERE id = :id",
            {"id": possession_id},
        )
        if rows:
            possession_created_at = rows[0]["created_at"]
            # Prefer the DB daemon name (daemon_name may be None from token file if auto-assigned)
            if rows[0]["daemon_name"]:
                daemon_name = rows[0]["daemon_name"]

        logger.info("summon_minion_success", possession_id=possession_id, role=role, daemon=daemon_name)

        # Derive the expected journal path from possession metadata
        try:
            project_root = get_project_root()
            possessions_dir = project_root / ".opencode" / "work" / "possessions"
            raw_ts = possession_created_at
            if isinstance(raw_ts, str):
                try:
                    created_at = datetime.fromisoformat(raw_ts)
                except ValueError:
                    created_at = datetime.now()
            else:
                created_at = raw_ts if raw_ts is not None else datetime.now()
            journal_path = DeskWorkerJournal.make_final_path(
                possessions_dir=possessions_dir,
                created_at=created_at,
                role=role,
                daemon=daemon_name,
                possession_id=possession_id,
            )
        except Exception:
            journal_path = None

        return json.dumps(
            {
                "possession_id": possession_id,
                "role": role,
                "daemon": daemon_name,
                "model": model,
                "poll_interval": poll_interval,
                "status": "summoned",
                "message": f"Minion summoned successfully. Possession #{possession_id} ({daemon_name}, {role}) is now polling for messages.",
                "journal_path": str(journal_path) if journal_path else None,
            }
        )

    except Exception as e:
        logger.exception("summon_minion_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


def _cleanup_status_file(status_file: Path) -> None:
    """Remove the spawn-token status file if it exists, silently ignoring errors."""
    try:
        status_file.unlink(missing_ok=True)
    except Exception:
        pass


if __name__ == "__main__":
    print(main())
