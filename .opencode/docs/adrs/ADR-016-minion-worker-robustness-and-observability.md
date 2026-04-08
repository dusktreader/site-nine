# ADR-016: Minion Worker Robustness and Observability

**Status:** PROPOSED
**Date:** 2026-04-07
**Deciders:** Tucker (Director), Asmodeus (Architect, Possession #15)
**Related ADRs:** ADR-013 (OpenCode Integration Platform), ADR-014 (Message-Driven Coordination), ADR-015 (Git Worktree Isolation)
**Task:** ARC-H-0257


## Context

The minion worker system (`src/site_nine/workers/minion_worker.py`, `.opencode/tools/summon_minion.py`,
`.opencode/tools/watch_inbox.py`) is the backbone of multi-agent orchestration. An Admin spawns one
or more background workers via `summon_minion`, assigns tasks via `worker_message`, and waits for
completion via `watch_inbox`. The system works for the happy path but has five gaps that limit its
reliability and observability in real workflows.

### Gap 1: Log file is role-scoped, not possession-scoped

`summon_minion.py` redirects all `minion_worker.py` stdout/stderr to:

```
~/.local/state/site-nine/logs/minion-worker-{role}.log
```

Two problems:

1. **Collision:** Two concurrent Engineer workers write to the same file. Log lines interleave and
   are unattributable.
2. **Disconnected from artifact system:** The log is outside the repo. It is not visible in the TUI,
   not linked to the possession record, and not retained alongside other work artifacts.

The possession file system already provides a natural home for per-possession output at
`.opencode/work/possessions/<timestamp>.<role>.<daemon>.md`.

### Gap 2: Admin `watch_inbox` blocks indefinitely on worker crash

`watch_inbox` has a `timeout` parameter (default 300s). When timeout fires it returns
`{"status": "timeout"}`. However:

- There is no documented protocol for what the Admin should do on timeout.
- There is no way to distinguish "worker is slow" from "worker is dead" at the point of timeout.
- `worker_status` returns `last_active_at` (from `possessions.last_heartbeat_at`) but the heartbeat
  is updated by the OpenCode plugin on each tool invocation — it stops updating as soon as the worker's
  `opencode run` subprocess exits (crashed or hung).

An Admin today must manually reason: "timeout fired, let me check `worker_status`, compare
`last_active_at` to now, decide if the worker is dead, then decide what to do." None of this is
codified.

### Gap 3: No liveness signal during long tasks

Workers are instructed (via the init message) to send `worker_message` updates when they start,
complete, or hit a blocker. But for a task that takes 15 minutes of continuous work, there is no
intermediate signal. An Admin using `watch_inbox` will wait silently. The Admin cannot distinguish
a healthy worker grinding through a task from a worker that hung 2 minutes in.

### Gap 4: No crash detection or recovery

If `minion_worker.py` itself crashes (uncaught exception in the polling loop, OOM, system fault), the
possession remains ACTIVE in the database. The inquisitor only exorcises possessions whose
`last_heartbeat_at` is stale by more than 3 hours. The admin finds out either:

- After `watch_inbox` times out (up to 5 minutes by default), or
- Never, if the admin doesn't call `watch_inbox` again.

There is no mechanism to restart the worker process or re-deliver the in-flight task.

### Gap 5: `summon_minion` possession ID race condition

`summon_minion.py` identifies the spawned worker's possession by querying:

```sql
SELECT id, daemon_name FROM possessions
WHERE role = :role
  AND status = 'ACTIVE'
  AND end_time IS NULL
ORDER BY created_at DESC
LIMIT 1
```

If two workers of the same role are spawned concurrently (by the same Admin or different sessions),
the second spawn may match the first spawn's possession record. The returned `possession_id` would be
wrong, and all subsequent `worker_message` calls would go to the wrong worker.

The fix is straightforward: `minion_worker.py` already extracts the OpenCode session ID from
`opencode run --format json` output. `possession_init` stores that session ID in
`possessions.opencode_session_id` (with a `UNIQUE` index). The lookup should use that column.


## Decision

We adopt five targeted fixes, described below. Each is minimal and self-contained. They do not
require changes to the database schema beyond adding one column (Gap 5 fix).

---

### Fix 1: Per-Possession Markdown Journal

**Replace** the role-scoped flat log file with a per-possession markdown journal written by
`minion_worker.py` to `.opencode/work/possessions/`.

#### Journal filename

Final filename convention:
```
.opencode/work/possessions/YYYY-MM-DD.HH-MM-SS.<role>.<Daemon>.<possession-id>.journal.md
```

Example:
```
.opencode/work/possessions/2026-04-07.14-23-11.engineer.Halphas.42.journal.md
```

The possession ID and daemon name are not known until after `initialize()` completes. Therefore
the journal is opened in two phases:

1. **Before init** — open a temporary file with a UUID placeholder (not possession-scoped):
   ```
   .opencode/work/possessions/minion-worker-<role>-<uuid8>.pending.md
   ```
2. **After init** — rename to the final convention using the daemon name, possession creation
   timestamp, and possession ID retrieved from the DB.

#### Journal format

```markdown
---
possession_id: 42
daemon: Halphas
role: Engineer
start_time: "2026-04-07 14:23:11"
status: ACTIVE
---

# Minion Worker Journal: Halphas — Engineer

## Initialization

- **14:23:11** Worker process started (PID: 98142)
- **14:23:44** OpenCode session initialized (session: abc123)
- **14:23:49** Possession ACTIVE (id: 42)
- **14:23:49** Minion mode enabled. Polling every 30s.

## Message Log

### [14:24:00] MSG-H-0017 from Possession #15 (HIGH)
Task assignment received: ENG-H-0150

### [14:24:01] Processing started

### [14:43:22] Processing complete (exit code 0)

### [14:43:22] Poll cycle — no new messages

...

## Shutdown

- **15:01:05** SIGTERM received. Disabling minion mode.
- **15:01:05** Ending possession via opencode run.
- **15:01:47** Shutdown complete.
```

#### Log routing

`summon_minion.py` currently opens the log file and passes it as `stdout=log_file, stderr=log_file`
to `subprocess.Popen`. Under this fix:

- `minion_worker.py` opens and manages its own journal file.
- `summon_minion.py` redirects to `/dev/null` (or a minimal bootstrap log that is superseded once
  `minion_worker.py` opens its own file). The role-scoped log file is eliminated.
- All structured output in `minion_worker.py` (`print(...)` statements) is replaced with a
  `MinionWorkerJournal` helper that writes timestamped markdown entries and flushes immediately.

---

### Fix 2: Codified Admin Timeout Protocol

The timeout protocol is documented in two places: this ADR establishes the design; the
`minion-mode-orchestration.md` guide is updated with the concrete steps.

#### Recommended `watch_inbox` timeout values

| Scenario | Recommended timeout |
|---|---|
| Simple task (test run, small edit) | 300s (5 min, current default) |
| Medium task (feature implementation) | 1200s (20 min) |
| Long task (epic, large refactor) | 3600s (1 hr) |
| Unknown / general | 600s (10 min) |

Admins should pass an explicit `timeout` rather than relying on the 300s default for non-trivial work.

#### On timeout: the Admin decision tree

```
watch_inbox returns { status: "timeout" }
    │
    ▼
worker_status({ role: <role> })
    │
    ├─ possession not found (status != ACTIVE) ──► Worker crashed. Re-spawn + re-send task.
    │
    └─ possession found, last_active_at present
           │
           ├─ last_active_at < (now - 10 min) ──► Worker likely stalled. Send ping.
           │     │
           │     ├─ ping acknowledged (new message arrives within 60s) ──► Extend timeout, continue.
           │     └─ no response ──► Exorcise + re-spawn + re-send task.
           │
           └─ last_active_at >= (now - 10 min) ──► Worker is alive. Extend timeout.
```

"Stalled" threshold is 10 minutes: if the heartbeat has not updated in 10 minutes, the worker's
`opencode run` subprocess is not making tool calls, which is a strong signal it is hung or dead.

#### Ping message convention

When an Admin needs to check liveness, send:

```
worker_message({
  to_possession_id: <id>,
  body: "STATUS_PING: Please respond with your current status immediately."
})
```

A healthy worker will process this on its next poll cycle (≤ 30s) and reply with a short status.

---

### Fix 3: Worker Heartbeat via `push_status`

Workers are already instructed to call `push_status` on status changes. We codify this as a
**liveness signal** with a required interval.

#### Design

`minion_worker.py` records the time of the last `opencode run` subprocess completion. After each
polling cycle in which no messages were processed, if more than **5 minutes** have elapsed since
the last subprocess completion, `minion_worker.py` itself (not the agent inside OpenCode) writes a
heartbeat entry to the journal and calls `push_status` directly via the Python tool implementation.

This is handled **outside** the agent — by `minion_worker.py` calling the push_status Python backend
directly — so it cannot be forgotten by the agent and does not require an extra `opencode run`
invocation.

```python
# In minion_worker.py polling loop
HEARTBEAT_INTERVAL = 300  # seconds

last_heartbeat = time.time()

while self.running:
    time.sleep(self.poll_interval)
    # ... check messages, process ...

    # Emit heartbeat if idle too long
    if time.time() - last_heartbeat > HEARTBEAT_INTERVAL:
        self._emit_heartbeat()
        last_heartbeat = time.time()

def _emit_heartbeat(self) -> None:
    """Write a heartbeat entry to the journal and push a toast status."""
    self.journal.write_entry("Heartbeat — still alive, polling for messages")
    try:
        from site_nine.possessions.manager import PossessionManager
        from site_nine.core.database import Database
        from site_nine.core.paths import get_db_path
        db = Database(get_db_path())
        mgr = PossessionManager(db)
        mgr.update_heartbeat(self.possession_id)
    except Exception:
        pass  # non-fatal
```

This keeps `last_heartbeat_at` fresh in the DB (which the Admin can read via `worker_status`) and
gives the Inquisitor accurate data to distinguish live workers from crashed ones.

#### Inquisitor threshold adjustment

With active heartbeats from `minion_worker.py`, the inquisitor's 3-hour stale threshold is too
conservative. A crashed worker that never heartbeats will be zombied for 3 hours. With Fix 3 in
place, **the inquisitor threshold can be reduced to 15 minutes** for minion-mode possessions
specifically (possessions where `minion_mode_active = 1`).

This is a separate schema/config change tracked in the implementation tasks.

---

### Fix 4: Worker PID Registration and Crash Detection

#### PID column

Add a `worker_pid` column to the `possessions` table:

```sql
ALTER TABLE possessions ADD COLUMN worker_pid INTEGER;
-- NULL for interactive possessions
-- Set to os.getpid() by minion_worker.py after possession is created
-- Cleared to NULL on clean shutdown
```

`minion_worker.py` writes its PID immediately after `set_minion_mode()`:

```python
db.execute_update(
    "UPDATE possessions SET worker_pid = :pid WHERE id = :id",
    {"pid": os.getpid(), "id": self.possession_id}
)
```

On clean shutdown, `handle_shutdown()` clears it:

```python
db.execute_update(
    "UPDATE possessions SET worker_pid = NULL WHERE id = :id",
    {"id": self.possession_id}
)
```

#### Inquisitor crash detection

The Inquisitor gains a new check: for every ACTIVE minion-mode possession with a non-NULL
`worker_pid`, check whether that PID is still running on the local machine:

```python
import os

def is_pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)  # signal 0 = existence check, no actual signal sent
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # process exists, we just can't signal it
```

If the PID is dead, the Inquisitor immediately exorcises the possession (without waiting for
heartbeat staleness). This reduces crash-to-detection latency from up to 3 hours to the next
Inquisitor cycle (which runs every few minutes).

**Limitation:** PID-based detection only works on the local machine. If workers run on different
hosts in the future, this approach needs revisiting. For the current single-machine deployment, it
is the right tradeoff.

#### Recovery path

When the Admin's `watch_inbox` times out and `worker_status` shows the possession is no longer
ACTIVE (because the Inquisitor exorcised it), the Admin follows the re-spawn protocol:

1. Call `summon_minion` to spawn a new worker of the same role.
2. Re-send the original task assignment message, with a note that this is a retry after crash.
3. The new worker proceeds as normal; it has no memory of the previous attempt.

**No automatic re-spawn.** Automatic re-spawn risks duplicate task execution if the original worker
completed the task just before crashing. The Admin (or the Director via the Admin) makes the
re-spawn decision, which is the correct locus of control.

---

### Fix 5: Session-ID-Based Possession Lookup in `summon_minion`

`minion_worker.py` already extracts the `sessionID` from `opencode run --format json` output. That
session ID is stored in `possessions.opencode_session_id` with a `UNIQUE` index.

Replace the role-based fallback lookup in `summon_minion.py` with a session-ID lookup:

```python
# After initialize() completes and self.session_id is set:
rows = db.execute_query(
    """
    SELECT id, daemon_name FROM possessions
    WHERE opencode_session_id = :session_id
      AND status = 'ACTIVE'
    LIMIT 1
    """,
    {"session_id": self.session_id},
)
```

`minion_worker.py` already performs this exact lookup in its `initialize()` method (Phase 1 of its
two-phase lookup). `summon_minion.py` should use the same approach.

The current role-based lookup in `summon_minion.py` is replaced entirely. The role+timestamp query
was only needed because `summon_minion.py` did not have access to the session ID — but it can now
obtain it by reading it back from `minion_worker.py`'s in-memory state, or equivalently by having
`minion_worker.py` write the session ID to a small temp file or pipe it back through a mechanism.

#### Implementation approach

The cleanest approach: `minion_worker.py` writes a small JSON status file after init completes:

```
~/.local/state/site-nine/workers/<spawn-token>.json
```

Where `spawn-token` is a UUID passed to `minion_worker.py` via a new `--spawn-token` CLI argument.
`summon_minion.py` generates the token, passes it to `minion_worker.py`, and then polls for the
status file rather than polling the DB by role.

```json
{
  "session_id": "ses_abc123",
  "possession_id": 42,
  "daemon": "Halphas",
  "status": "ready"
}
```

`summon_minion.py` reads this file, gets the exact possession ID, then cleans up the temp file.
This eliminates the race condition entirely.


## Alternatives Considered

### Alt 1: Process supervisor (systemd / launchd / supervisord)

A process supervisor would restart `minion_worker.py` automatically on crash and provide log
management out of the box. Rejected because:

- Requires system-level setup (admin privileges, platform-specific config)
- Incompatible with the "lightweight single-machine tool" philosophy
- Workers are ephemeral by design — restart semantics would need careful thought to avoid duplicate
  task execution

### Alt 2: Automatic re-spawn on crash

Detect crash and automatically re-spawn the worker, re-sending the last in-flight task.

Rejected because:

- Risk of double-execution: the task may have completed just before the crash
- Admin should decide when to retry (the Admin has context the automation does not)
- Adds complexity to the crash detection path without clear benefit over the manual recovery flow

### Alt 3: Persistent task queue with at-least-once delivery

Store task assignments in the DB (not just messages) with delivery status. Worker marks task as
"in-flight" when processing starts; if the worker crashes without marking "complete", the task
re-enters the queue for any available worker.

Rejected for this ADR because:

- Significant schema and workflow complexity
- Requires defining "idempotent task processing" semantics across all possible task types
- Deferred to a future ADR if at-least-once delivery becomes a hard requirement


## Consequences

### Positive

- **Per-possession journals:** Each worker's activity is captured in a named, addressable artifact
  linked to the possession record. TUI and directory browsing reveal what each worker did.
- **Crash detection latency:** Reduced from 3 hours to the next Inquisitor cycle (~minutes) via
  PID liveness check.
- **Admin recovery clarity:** The Admin timeout decision tree provides a codified, deterministic
  response to timeout events. No more ad-hoc reasoning.
- **Heartbeats from `minion_worker.py`:** `last_active_at` is kept fresh even during idle periods,
  giving `worker_status` accurate data.
- **Race condition eliminated:** `summon_minion` now identifies the spawned possession by session
  ID, not role+recency. Concurrent same-role spawns are safe.

### Negative / Trade-offs

- **Journal file management:** `.opencode/work/possessions/` will accumulate journal files from
  minion workers alongside interactive possession files. The naming convention distinguishes them
  (`minion-worker-<role>-pending.md` during init, then renamed to the standard format). The
  directory may grow large in heavy-use scenarios; no automated retention policy exists yet.
- **PID detection is local only:** Works for the current single-machine deployment. Not portable
  to distributed execution.
- **Spawn token temp files:** Introduces a small temp file mechanism (`~/.local/state/site-nine/workers/`)
  that must be cleaned up. Cleanup is handled by `summon_minion.py` after reading the file.
- **`minion_worker.py` complexity increases:** Adding journal, heartbeat, PID registration, and
  spawn-token output makes `minion_worker.py` larger. Acceptable given the reliability improvements.


## Implementation Plan

Five implementation tasks are created from this ADR:

| Task | Role | Priority | Description |
|---|---|---|---|
| ENG-H-0258 | Engineer | HIGH | Per-possession journal: `MinionWorkerJournal` class, rename logic, journal routing in `minion_worker.py` and `summon_minion.py` |
| ENG-H-0259 | Engineer | HIGH | Worker PID column: DB migration, PID registration in `minion_worker.py`, Inquisitor crash-detection check |
| ENG-H-0260 | Engineer | HIGH | Heartbeat emission from `minion_worker.py` polling loop; reduce Inquisitor minion-mode threshold to 15 min |
| ENG-M-0261 | Engineer | MEDIUM | Session-ID-based possession lookup: spawn-token mechanism in `summon_minion.py` and `minion_worker.py` |
| DOC-M-0262 | Documentarian | MEDIUM | Update `minion-mode-orchestration.md` with timeout protocol, decision tree, and ping convention |

Implementation should proceed in order: ENG-H-0258 (journal, no schema change) → ENG-H-0259 (PID,
schema change) → ENG-H-0260 (heartbeat, depends on journal) → ENG-M-0261 (spawn token) →
DOC-M-0262 (documentation, depends on all of the above).


## References

- `src/site_nine/workers/minion_worker.py` — minion worker implementation
- `.opencode/tools/summon_minion.py` — spawn tool
- `.opencode/tools/watch_inbox.py` — inbox blocking tool
- `.opencode/tools/worker_status.py` — status check tool
- `src/site_nine/data/schema.sql` — database schema
- ADR-014: Message-Driven Coordination Architecture
- ADR-015: Git Worktree Isolation for Minion Workers (PROPOSED)
- Task: ARC-H-0257 (this task)
