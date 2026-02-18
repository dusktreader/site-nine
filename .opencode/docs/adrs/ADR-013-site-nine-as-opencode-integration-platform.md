# ADR-013: Site-nine as OpenCode Integration Platform

**Status:** ACCEPTED
**Date:** 2026-02-18
**Deciders:** Tucker (Director), Atum (Architect)
**Supersedes:** ADR-011 (Site-nine as OpenCode Integration Platform - prior draft)
**Related Tasks:** OPR-M-0129, ARC-H-0131


## Context

### Current State

Site-nine currently operates as a loosely coupled CLI tool. Agents use it manually within OpenCode sessions by
following markdown skill documents. The current session initialization workflow works as follows:

1. Director opens OpenCode manually (via `opencode` command or the TUI)
2. Director invokes the `/summon` command, which runs the `session-start` skill
3. The `session-start` skill is a monolithic markdown document that instructs the agent to run a series of `s9` CLI
   commands to register a mission, select a persona, send heartbeats, etc.
4. The agent periodically sends heartbeats by calling `s9 mission heartbeat <id>`
5. When dismissed, the Director invokes `/dismiss`, which runs the `mission-end` skill

### Problems with the Current State

**Problem 1: Manual coupling is fragile**

The entire mission lifecycle depends on agents correctly following skill instructions. Any deviation leaves the system
in a corrupt state:

- Agents forget to call `s9 mission heartbeat`, causing `s9 doctor` to flag missions as stale
- Agents forget to end missions when sessions close unexpectedly (crashes, terminal closures), creating zombie missions
  that remain `ACTIVE` forever
- The `session-start` skill is a long monolithic document that is easy to partially follow or misinterpret,
  particularly when the agent's context is limited or polluted

**Problem 2: Skill architecture is monolithic and fragile**

The `session-start` skill mixes deterministic operations (creating a database record, generating a codename) with
interactive agent decisions (selecting a role, choosing a persona). This makes it:

- Hard to test: The entire flow must be simulated end-to-end
- Easy to break: A single misstep partway through the skill leaves the mission in an inconsistent state
- Inefficient: The agent carries all intermediate CLI output in context, including operational noise that is never
  useful for actual work

**Problem 3: No connection to the OpenCode session lifecycle**

OpenCode sessions have a well-defined lifecycle (created, updated, deleted). Site-nine is completely unaware of this
lifecycle. There is no mechanism to:

- Automatically suspend a mission when a session closes unexpectedly
- Automatically track session activity (heartbeats must be sent manually)
- Resume a suspended mission in a new OpenCode session
- Detect that a new session is a resumption of a prior mission

**Problem 4: No multi-agent orchestration**

The current model requires the Director to interact with each agent individually. There is no way for one agent (an
Admin) to orchestrate other agents (workers) without Director involvement. The messaging system exists but lacks the
session-lifecycle integration needed to make background workers practical.


## Decision

We will transform site-nine from a loosely coupled CLI tool into a tightly integrated OpenCode platform.

The core of this transformation is:

1. **`s9 summon` becomes the session launcher** — The Director launches site-nine sessions externally. The summon
   command injects an initial instruction message that triggers the mission initialization workflow automatically.

2. **The `session-start` skill is replaced by decomposed tools and skills** — Deterministic operations become
   OpenCode custom tools (TypeScript wrappers around Python scripts). Interactive decisions remain as lightweight
   skills. This produces a clean separation of concerns.

3. **A site-nine OpenCode plugin manages the session lifecycle** — A TypeScript plugin observes OpenCode session
   events to automatically track activity and suspend missions when sessions close unexpectedly.

4. **Missions can be suspended and resumed** — Session closure no longer means mission loss. The plugin auto-suspends
   the mission, and the Director can resume it with `s9 mission resume`.

5. **Desk mode enables background agent workers** — Admin agents can summon background (headless) workers via
   `s9 summon --desk`. Workers process tasks via the `opencode run` command and are coordinated via the messaging
   system.

6. **`s9` CLI is the Director's interface; tools are the agent's interface** — All `site_nine` business logic is
   accessed through two surfaces: the `s9` CLI (used by the Director in a terminal) and OpenCode tools (used by
   agents inside a session). Both surfaces call the same underlying `site_nine` Python functions directly. Agents
   never shell out to `s9` commands; the CLI is not part of the agent's interface.


## Proposed Design

### 1. `s9 summon` as the Session Launcher

The existing `s9 summon` command is extended to become the primary way to start a site-nine session. Rather than
opening OpenCode and then running `/summon` inside it, the Director runs `s9 summon` from the terminal directly.

```
# Launch a session with role and persona pre-specified
s9 summon architect atum

# Launch a session with only role specified (persona auto-selected)
s9 summon architect

# Resume a suspended mission (transitions state to ACTIVE and launches OpenCode)
s9 mission resume void-vortex

# Launch a background desk-mode worker
s9 summon engineer --desk
```

The summon command:

1. Accepts an optional role and optional persona as arguments
2. Constructs an initial instruction message appropriate to the provided arguments
3. Execs into OpenCode with that message as the first input (via `opencode --message "..."`), replacing the `s9`
   process — no parent process remains
4. The agent receives the instruction, runs the `mission-start` skill, and becomes active

For desk mode (`--desk`), the process is spawned instead of exec'd — the `s9` process must remain alive to run
the polling loop and hold the worker's PID.

Resuming a suspended mission is handled entirely by `s9 mission resume` — it performs the state transition and
launches OpenCode in a single step. `s9 summon` is only for starting new missions.

The `/summon` command inside OpenCode continues to work as an alternative entry point, supporting the same arguments.
This is useful for workflows where the Director has already opened OpenCode and wants to initialize a mission without
restarting.

**Instruction message examples:**

```
# Role + persona specified:
"Your role is architect, your persona is atum. Initialize your mission with the mission-start skill."

# Role only:
"Your role is architect. Initialize your mission with the mission-start skill."

# Neither (agent selects both):
"Initialize your mission with the mission-start skill."

# Resume:
"Resume mission 'void-vortex' using the mission-start skill with --resume void-vortex."
```


### 2. Decomposed Tools and Skills Architecture

The current monolithic `session-start` skill is replaced with a set of focused tools and skills.

**Terminology:**
- A **skill** is a markdown document that provides instructions to an agent. Skills handle interactive,
  context-dependent decisions.
- A **tool** is a TypeScript file in `.opencode/tools/` that the agent can invoke as a function call. Tools handle
  deterministic, repeatable operations. Each tool is a thin TypeScript wrapper that passes arguments and session
  context to a Python script, which imports from the `site_nine` package to do the actual work.

**Dual-surface principle:** Every operation available to agents via a tool has a corresponding `s9` CLI command
for the Director. Both surfaces call the same `site_nine` Python functions directly. Agents never invoke `s9`
commands; the CLI is strictly the Director's interface.

**Tool definitions live at:** `.opencode/tools/<tool-name>.ts`
**Python implementations live at:** `.opencode/tools/<tool-name>.py`

#### Tool: `mission_init`

Responsibilities:
- Receives `context.sessionID` from OpenCode automatically
- Checks whether the session is already bound to an active or suspended mission (prevents double-binding)
- Creates a new mission record in the database with status `ROLE_PENDING`
- Generates and assigns a codename
- Returns the mission ID and codename

Arguments: none (session ID comes from tool context)

#### Tool: `mission_role_record`

Responsibilities:
- Updates the mission's role field in the database
- Transitions mission status from `ROLE_PENDING` to `PERSONA_PENDING`

Arguments: `mission_id`, `role`

#### Tool: `mission_persona_record`

Responsibilities:
- Updates the mission's persona field in the database
- Transitions mission status from `PERSONA_PENDING` to `ACTIVE`

Arguments: `mission_id`, `persona`

#### Skill: `mission-start`

This is the replacement for `session-start`. It is a markdown skill that orchestrates the mission initialization
workflow by invoking the tools above in sequence.

Workflow:

```
1. Call mission_init tool
   → Creates mission record bound to current session
   → Returns mission_id, codename

2. If role was provided in the summon instruction:
   → Call mission_role_record tool directly

   If role was NOT provided:
   → Show the role-selection dashboard (s9 dashboard)
   → Ask the Director to choose a role (using question tool)
   → Call mission_role_record tool with the chosen role

3. Check whether persona was provided in the summon instruction:
   → If provided: use it
   → If not provided: auto-select using s9 persona suggest <role>

4. Check whether persona has a bio:
   → If bio exists: display it
   → If bio missing: generate bio and save with s9 persona set-bio

5. Call mission_persona_record tool
   → Mission transitions to ACTIVE

6. Call mission_rename_session tool
   → Looks up the OpenCode session file by session ID (from context.sessionID)
   → Renames the session title to "Operation <codename>: <Persona> - <Role>"

7. Call handoff_list tool
   → Returns pending handoffs for the current mission's role

8. Call mission_dashboard tool
   → Returns the role-filtered task dashboard for the current mission's role
```

#### Additional Tools for Task Lifecycle

The following tools replace CLI-heavy portions of the current task management skills:

- **`task_claim`** — Claims a task for the current mission (invokes a Python script that calls `site_nine` task
  functions directly)
- **`task_update`** — Updates task progress notes (invokes a Python script that calls `site_nine` task functions
  directly)
- **`task_close`** — Closes a task with a given status and notes (invokes a Python script that calls `site_nine` task
  functions directly)

These tools receive `context.sessionID` so they can look up the current mission without requiring the agent to track
the mission ID manually.

#### Tool and Python Script Pattern

All tools follow this pattern: the TypeScript file receives arguments and `context.sessionID` from OpenCode,
serializes them to JSON, and pipes them to a Python script via stdin. The Python script imports and calls functions
from the `site_nine` package directly — it never shells out to the `s9` CLI. This ensures all business logic and
database access goes through the same tested code paths used by the rest of the system.

`.opencode/tools/mission_init.ts`:
```typescript
import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description: "Initialize a new site-nine mission for the current session",
  args: {},
  async execute(args, context) {
    const script = path.join(context.worktree, ".opencode/tools/mission_init.py")
    const input = JSON.stringify({ session_id: context.sessionID })
    const result = await Bun.$`echo ${input} | python3 ${script}`.text()
    return result.trim()
  },
})
```

`.opencode/tools/mission_init.py`:
```python
#!/usr/bin/env python3
import sys
import json
from site_nine.models.mission import Mission
from site_nine.database import get_db

def main():
    context = json.loads(sys.stdin.read())
    session_id = context["session_id"]
    db = get_db()
    # ... implementation using site_nine modules
    return json.dumps({"mission_id": mission.id, "codename": mission.codename})

if __name__ == "__main__":
    print(main())
```

The Python script imports directly from `site_nine` package modules, ensuring all business logic and database access
goes through the same tested code paths used by the CLI.


### 3. OpenCode Plugin for Lifecycle Automation

A TypeScript plugin at `.opencode/plugins/site-nine.ts` handles automatic session lifecycle management.

**Plugin responsibilities (minimal by design):**

1. **Activity tracking:** On `session.updated` events, update the mission's `last_activity_at` timestamp. Throttled
   to a maximum of one database write per minute to prevent excessive load.

2. **Auto-suspend on session close:** On `session.deleted` events, look up whether an active mission is bound to
   the session and, if so, transition it to `SUSPENDED` status. This is the only reliable mechanism for detecting
   unexpected session closure without false positives from idle time. If the database is unavailable, the suspend
   operation is retried with exponential backoff before giving up and logging the error.

3. **Comprehensive logging:** All plugin operations are logged via the Python scripts they invoke. Each script uses
   `loguru`'s `logger` (i.e. `from loguru import logger`), consistent with the rest of the `site_nine` package.

**What the plugin does NOT do:**

- Does not create missions (that is the responsibility of the `mission_init` tool)
- Does not end missions (that is the responsibility of the `mission-end` skill via `/dismiss`)
- Does not manage task state
- Does not introspect session content

The plugin invokes Python scripts for all database operations, following the same pattern as the tools above. It
never accesses the database directly from TypeScript.

**Session activity tracking rationale:**

The `last_activity_at` field is for analytics and UI display (showing the Director when an agent last did
something). It is also used as a fallback for stale detection. Under normal operation, a crashed session triggers
the plugin's `session.deleted` handler, which auto-suspends the mission — stale detection then operates on the
`SUSPENDED` status and `suspension_time`. However, if OpenCode crashes hard enough that the plugin never fires, the
mission remains `ACTIVE` indefinitely. In that case, `last_activity_at` is the only signal available. An
`ACTIVE` mission with no activity for longer than the stale threshold is treated as a crash survivor and surfaced
by `s9 doctor` for cleanup.


### 4. Mission Lifecycle: Suspend, Resume, and Stale Detection

#### Mission Status States

```
ROLE_PENDING → PERSONA_PENDING → ACTIVE ──→ SUSPENDED ──→ (resume) → ACTIVE
                                    └────────────────────→ ENDED
                                    (via /dismiss)
```

- **`ROLE_PENDING`**: Mission record created, session bound, awaiting role selection
- **`PERSONA_PENDING`**: Role recorded, awaiting persona selection
- **`ACTIVE`**: Fully initialized, agent is working
- **`SUSPENDED`**: Session closed unexpectedly; mission is paused and resumable
- **`ENDED`**: Mission explicitly ended via `/dismiss` or manual cleanup (terminal state)

#### Transition Rules

| Transition           | Trigger                              | Mechanism                        |
|----------------------|--------------------------------------|----------------------------------|
| `→ ROLE_PENDING`     | `mission_init` tool called           | Tool (Python script)             |
| `→ PERSONA_PENDING`  | `mission_role_record` tool called    | Tool (Python script)             |
| `→ ACTIVE`           | `mission_persona_record` tool called | Tool (Python script)             |
| `ACTIVE → SUSPENDED` | OpenCode session closes unexpectedly | Plugin (`session.deleted` event) |
| `SUSPENDED → ACTIVE` | `s9 mission resume`                  | CLI (state + OpenCode launch)    |
| `ACTIVE → ENDED`     | `/dismiss` command                   | `mission-end` skill              |
| `ACTIVE → ENDED`     | Catastrophic crash confirmed stale   | `s9 doctor` (manual confirm only) |
| `SUSPENDED → ENDED`  | Manual cleanup or `s9 doctor`        | CLI                              |

#### Session Resume

When a session closes unexpectedly (crash, terminal switch, accidental close), the plugin auto-suspends the mission.
The Director resumes it with:

```bash
s9 mission resume              # resume most recently suspended mission
s9 mission resume void-vortex  # resume by codename
s9 mission resume 42           # resume by mission ID
```

`s9 mission resume`:
1. Validates the mission exists and is in `SUSPENDED` state
2. Updates `opencode_session_id` on the mission to a new pending session ID
3. Transitions mission status to `ACTIVE`
4. Launches OpenCode with a context message summarizing the resumed mission state

#### Stale Mission Detection

The existing `s9 doctor` command is extended to detect and offer cleanup of stale missions. There are two stale
conditions, treated with different levels of caution:

1. **Suspended stale:** Mission has been in `SUSPENDED` state for longer than the configurable threshold (default:
   7 days). This is the normal crash path — the plugin fired and suspended the mission, but the Director never
   resumed it. These missions are safe candidates for `--auto-clean`.

2. **Active stale:** Mission is in `ACTIVE` state but `last_activity_at` has not been updated for longer than the
   threshold. This should only occur after a catastrophic crash (SIGKILL, hard power-off) where the plugin's
   `session.deleted` handler never had a chance to fire. These missions are **never** eligible for `--auto-clean`
   — they require explicit Director confirmation before being ended. The Director may also choose to resume an
   active-stale mission if the work is still relevant.

`s9 doctor` will:
1. Query for missions matching either stale condition
2. Display each stale mission with details (codename, persona, status, tasks, last activity)
3. For suspended-stale missions: prompt the Director to Resume, End, or Skip
4. For active-stale missions: warn that this likely indicates a hard crash and require explicit confirmation
   before ending — Resume is always offered as an alternative

For automated cleanup of suspended missions only: `s9 doctor --auto-clean --older-than 30d`


### 5. Desk Mode for Background Agent Workers

Desk mode enables an Admin agent to orchestrate background worker agents without requiring the Director to manage
each worker individually.

#### Overview

```
Director
  └─ talks to → Admin Agent (interactive OpenCode session)
                  ├─ summons → Engineer (desk mode, background)
                  ├─ summons → Architect (desk mode, background)
                  └─ sends tasks via s9 messaging system
```

Workers run in headless OpenCode sessions via `opencode run`. Each worker processes one message at a time and then
waits for the next. The Director only interacts with the Admin; workers are invisible infrastructure.

#### Launching Desk Mode Workers

```bash
# Admin summons a background worker (role is required for desk mode)
s9 summon engineer --desk
```

This spawns a background Python process that:
1. Launches the worker's initial session via
   `opencode run "Initialize your mission with mission-start skill. Role: engineer. Mode: desk."`
2. Records the worker's session ID from the database once the mission is active
3. Enters a polling loop, checking for unread messages addressed to the worker's session
4. For each message received: invokes `opencode run --session <id> "<message body>"`
5. After each invocation, the session auto-suspends; the next invocation resumes it
6. Responds to `SIGTERM` by gracefully invoking the `mission-end` skill before exiting

#### Worker Lifecycle

Each `opencode run` invocation resumes the worker's existing session (via `--session <id>`), so the worker retains
full conversational context across messages. The session auto-suspends when the invocation completes (via the
plugin's `session.deleted` handler), and the next incoming message resumes it again. This means the worker
accumulates context over its lifetime, which is the desired behavior — it needs to remember prior instructions,
completed work, and ongoing task state to be useful as a background collaborator.

The polling loop runs in the external Python process, not inside the agent's context. This is a deliberate design
choice: an agent running its own polling loop would accumulate context noise from repeated sleep/wake/check
cycles — tool calls, empty results, timing artifacts — that are operationally irrelevant to the actual work. By
externalizing the loop to Python, the agent's context contains only meaningful message exchanges.

#### Admin Orchestration Tools

The Admin agent uses tools (not CLI commands) to orchestrate workers:

- **`worker_message`** — Sends a message to a worker session (invokes a Python script that calls `site_nine`
  messaging functions directly)
- **`worker_status`** — Returns the current status of active worker missions for a given role (invokes a Python
  script that calls `site_nine` mission functions directly)
- **`worker_terminate`** — Signals a worker to gracefully end its mission and exit; sends a termination message
  to the worker's session which the polling process acts on (invokes a Python script that calls `site_nine`
  functions directly)


### 6. Database Schema Changes

The following additions to the `missions` table are required:

```sql
-- Bind missions to OpenCode sessions
ALTER TABLE missions ADD COLUMN opencode_session_id TEXT UNIQUE;
CREATE INDEX idx_missions_session_id ON missions(opencode_session_id);

-- Track mission mode (interactive vs desk)
ALTER TABLE missions ADD COLUMN mode TEXT DEFAULT 'interactive';
CREATE INDEX idx_missions_mode ON missions(mode);

-- Track session activity for analytics and UI
ALTER TABLE missions ADD COLUMN last_activity_at TEXT;

-- Track suspension for resume and stale detection
ALTER TABLE missions ADD COLUMN suspension_time TEXT;
ALTER TABLE missions ADD COLUMN suspension_reason TEXT;

-- Add new statuses to application-level enum:
-- ROLE_PENDING, PERSONA_PENDING, ACTIVE, SUSPENDED, ENDED
-- (existing: ACTIVE, ENDED — SUSPENDED is new; ROLE_PENDING and PERSONA_PENDING are transient)
CREATE INDEX idx_missions_suspended ON missions(status, suspension_time)
  WHERE status = 'SUSPENDED';
```

The `opencode_session_id` column is nullable to maintain compatibility with existing missions created before this
migration.


### 7. Skill and Tool Inventory

#### New Tools (`.opencode/tools/`)

**Mission lifecycle:**

| Tool                     | Type | Responsibility                                                                   |
|--------------------------|------|----------------------------------------------------------------------------------|
| `mission_init`           | code | Create mission record, bind session, generate codename                           |
| `mission_role_record`    | code | Set mission role, transition to `PERSONA_PENDING`                                |
| `mission_persona_record` | code | Set mission persona, transition to `ACTIVE`                                      |
| `mission_rename_session` | code | Rename the OpenCode session file to match the mission (looks up by session ID)   |
| `mission_rename_dismissed` | code | Rename the OpenCode session file with `[DISMISSED]` suffix on mission end      |
| `mission_end`            | code | End the current mission, transition to `ENDED`                                   |
| `mission_summary`        | code | Generate a summary of files, commits, and tasks for the current mission          |

**Task management:**

| Tool           | Type | Responsibility                                  |
|----------------|------|-------------------------------------------------|
| `task_create`  | code | Create a new task                               |
| `task_show`    | code | Show a task by ID, list tasks by filter, generate reports, or list mission-scoped tasks |
| `task_claim`   | code | Claim a task for the current mission            |
| `task_update`  | code | Update task progress notes                      |
| `task_close`   | code | Close a task with status and notes              |
| `task_release` | code | Release a task back to TODO (for handoffs)      |

**Handoffs:**

| Tool              | Type | Responsibility                                        |
|-------------------|------|-------------------------------------------------------|
| `handoff_create`  | code | Create a handoff record and document in the database  |
| `handoff_list`    | code | Return pending handoffs for the current mission's role |
| `handoff_delete`  | code | Consume (delete) a handoff after reviewing it         |

**Persona:**

| Tool              | Type | Responsibility                                        |
|-------------------|------|-------------------------------------------------------|
| `persona_suggest` | code | Suggest unused persona names for a given role         |
| `persona_show`    | code | Show persona details including bio                    |
| `persona_set_bio` | code | Save a generated bio for a persona                    |

**Dashboard:**

| Tool                | Type | Responsibility                                                    |
|---------------------|------|-------------------------------------------------------------------|
| `mission_dashboard` | code | Return the role-filtered task dashboard for the current mission's role |

**Desk mode (Admin only):**

| Tool               | Type | Responsibility                                          |
|--------------------|------|---------------------------------------------------------|
| `worker_message`   | code | Send a message to a worker session                      |
| `worker_status`    | code | Return current status of active worker missions for a given role |
| `worker_terminate` | code | Signal a worker to gracefully end its mission and exit  |

#### Updated/New Skills (`.opencode/skills/`)

| Skill               | Status                          | Responsibility                                         |
|---------------------|---------------------------------|--------------------------------------------------------|
| `mission-start`     | New (replaces `session-start`)  | Orchestrate mission initialization workflow via tools  |
| `mission-end`       | Renamed (from `session-end`)    | Orchestrate graceful mission end via tools             |
| `task-claim`        | Updated                         | Now invokes `task_claim` tool instead of CLI           |
| `task-update`       | Updated                         | Now invokes `task_update` tool instead of CLI          |
| `task-close`        | Updated                         | Now invokes `task_close` tool instead of CLI           |
| `task-create`       | Updated                         | Now invokes `task_create` tool instead of CLI          |
| `task-query`        | Updated                         | Now invokes `task_show` tool instead of CLI            |
| `handoff-workflow`  | Updated                         | Now invokes `handoff_create`, `task_release`,          |
|                     |                                 | `handoff_list`, `handoff_delete` tools instead of CLI  |
| `tasks-report`      | Updated                         | Now invokes `task_show` and `mission_dashboard` tools  |
|                     |                                 | instead of `s9 task report`, `s9 task list`, `s9       |
|                     |                                 | dashboard`                                             |

#### Deleted Skills

| Skill             | Reason                                                         |
|-------------------|----------------------------------------------------------------|
| `session-start`   | Replaced by `mission-start` skill + decomposed tools; deleted  |


## Strengths of This Approach

**Eliminates zombie missions.** The plugin's `session.deleted` handler auto-suspends any active mission when a
session closes. It is no longer possible for a mission to remain `ACTIVE` after its OpenCode session has ended.

**Removes manual heartbeats.** The plugin's `session.updated` handler automatically updates `last_activity_at`
whenever the agent does anything. Agents no longer need to periodically call `s9 mission heartbeat`.

**Clean context for agents.** Deterministic operations (database writes, record creation) happen in tools. The agent's
context only contains the results — not the process. This eliminates the operational noise that accumulated in the old
`session-start` skill (UUIDs, database confirmations, intermediate state).

**Resilient to session interruptions.** Suspend/resume means that crashes, terminal switches, or accidental closures
do not lose mission state. The Director can resume exactly where they left off.

**Enables multi-agent orchestration.** Desk mode provides a practical model for background workers without requiring
new OpenCode primitives. Admin agents can delegate tasks to specialized workers, reducing Director cognitive load.

**Clear separation of concerns.** Tools own persistence. Skills own interactive decision-making. The plugin owns
lifecycle automation. Each component has a single responsibility that can be tested and reasoned about independently.

**Backward compatible.** The `opencode_session_id` column is nullable. Existing missions without a session ID
continue to work. The `/summon` command inside OpenCode is retained as an alternative to `s9 summon`.


## Implementation Plan

### Phase 1: Database Foundation

1. Write and test database migration adding `opencode_session_id`, `mode`, `last_activity_at`,
   `suspension_time`, and `suspension_reason` columns to the `missions` table
2. Add indexes for session ID and suspended mission queries
3. Add new mission status values (`ROLE_PENDING`, `PERSONA_PENDING`, `SUSPENDED`) to the application-level enum
4. Implement `s9 mission suspend <id>` CLI command
5. Implement `s9 mission resume <id>` CLI command — transitions `SUSPENDED → ACTIVE`, binds new session ID,
   and launches OpenCode with a context message summarizing the resumed mission state
6. Extend `s9 doctor` to detect and surface stale suspended missions

**Acceptance criteria:** Migration runs cleanly on existing database; new CLI commands work; existing missions
unaffected.

### Phase 2: Tools Implementation

**Mission lifecycle tools:**

1. Implement `mission_init` tool (TypeScript + Python)
2. Implement `mission_role_record` tool (TypeScript + Python)
3. Implement `mission_persona_record` tool (TypeScript + Python)
4. Implement `mission_rename_session` tool (TypeScript + Python)
5. Implement `mission_rename_dismissed` tool (TypeScript + Python)
6. Implement `mission_end` tool (TypeScript + Python)
7. Implement `mission_summary` tool (TypeScript + Python)

**Task management tools:**

8. Implement `task_create` tool (TypeScript + Python)
9. Implement `task_show` tool (TypeScript + Python)
10. Implement `task_claim` tool (TypeScript + Python)
11. Implement `task_update` tool (TypeScript + Python)
12. Implement `task_close` tool (TypeScript + Python)
13. Implement `task_release` tool (TypeScript + Python)

**Handoff tools:**

14. Implement `handoff_create` tool (TypeScript + Python)
15. Implement `handoff_list` tool (TypeScript + Python)
16. Implement `handoff_delete` tool (TypeScript + Python)

**Persona tools:**

17. Implement `persona_suggest` tool (TypeScript + Python)
18. Implement `persona_show` tool (TypeScript + Python)
19. Implement `persona_set_bio` tool (TypeScript + Python)

**Dashboard tool:**

20. Implement `mission_dashboard` tool (TypeScript + Python)

**Tests:**

21. Write unit tests for each Python script

**Acceptance criteria:** Each tool can be invoked by an agent in a live OpenCode session and produces correct
database changes; double-binding prevention works correctly; all tool groups (mission, task, handoff, persona,
dashboard) have passing unit tests.

### Phase 3: Skills Update

**New and renamed skills:**

1. Write the `mission-start` skill (replaces `session-start`)
2. Rename `session-end` skill to `mission-end`; update it to invoke `mission_end` and `mission_rename_dismissed` tools

**Updated skills (replace CLI calls with tool invocations):**

3. Update `task-claim` skill to invoke `task_claim` tool instead of `s9 task claim`
4. Update `task-update` skill to invoke `task_update` tool instead of `s9 task update`
5. Update `task-close` skill to invoke `task_close` tool instead of `s9 task close`
6. Update `task-create` skill to invoke `task_create` tool instead of `s9 task create`
7. Update `task-query` skill to invoke `task_show` tool instead of `s9 task show`, `s9 task list`,
   `s9 task report`, and `s9 task mine`
8. Update `handoff-workflow` skill to invoke `handoff_create`, `task_release`, `handoff_list`, and
   `handoff_delete` tools instead of CLI equivalents
9. Update `tasks-report` skill to invoke `task_show` and `mission_dashboard` tools instead of
   `s9 task report`, `s9 task list`, and `s9 dashboard`

**Launcher:**

10. Update `s9 summon` to construct and inject appropriate instruction messages
11. Update the `/summon` slash command to support the same arguments as `s9 summon`

**Validation:**

12. Validate end-to-end: `s9 summon architect` → agent runs `mission-start` → mission is `ACTIVE`
13. Validate resume flow: `s9 mission resume` → agent resumes suspended mission
14. Delete `session-start` skill — `mission-start` is its full replacement, no transition period

**Acceptance criteria:** Full mission initialization workflow succeeds via both `s9 summon` and `/summon`;
role/persona pre-specification works; persona auto-selection works; resume flow works; all updated skills
invoke tools exclusively (no direct `s9` CLI calls).

### Phase 4: Plugin Implementation

1. Create `.opencode/plugins/site-nine.ts`
2. Implement `session.updated` handler with throttled activity tracking (max 1 DB write/min)
3. Implement `session.deleted` handler to auto-suspend active missions with exponential backoff retry on DB failure
4. Implement Python scripts for plugin database operations (query by session ID, update activity, suspend)
5. Add comprehensive logging (debug, info, warn, error)
6. Validate: closing OpenCode while a mission is active results in `SUSPENDED` status

**Acceptance criteria:** Plugin loads without errors; activity tracking fires correctly; auto-suspend fires on
session close; non-site-nine sessions are ignored silently; no OpenCode instability introduced.

### Phase 5: Desk Mode

1. Implement `s9 summon <role> --desk` command
2. Write the Python polling script that manages desk agent lifecycle
3. Implement SIGTERM handler for graceful desk agent termination
4. Implement `worker_terminate` tool (TypeScript + Python)
5. Validate end-to-end: Admin summons desk worker → sends message → worker processes → Admin gets result

**Acceptance criteria:** Desk workers can be summoned, receive messages, process tasks, and be terminated
gracefully; session context is preserved across multiple `opencode run` invocations.

### Phase 6: Cleanup and Documentation

1. Update all existing skills that reference `s9 mission heartbeat` to remove heartbeat calls
2. Update `mission-end` skill to use `mission_close` tool for database operations instead of CLI
3. Rename `session-start` skill to `mission-start` and `session-end` skill to `mission-end`
4. Write operator guide for desk mode orchestration
5. Update `AGENTS.md` and relevant skill documents to reflect new workflow
6. Monitor for one week: plugin logs, suspend/resume usage, any instability


## References

- **Supersedes:** ADR-011 (Site-nine as OpenCode Integration Platform, prior draft)
- **Also supersedes:** ADR-010 (OpenCode Session Lifecycle Integration for Auto-Dismissal)
- **Related Task:** OPR-M-0129 (Investigate OpenCode session lifecycle hooks)
- **Related ADR:** ADR-006 (Entity Model Clarity — Personas, Missions, Agents)
- **Related ADR:** ADR-008 (Agent Messaging System)
- **Related ADR:** ADR-009 (Agent Coordination Patterns)
- **OpenCode Custom Tools:** https://opencode.ai/docs/custom-tools/
- **OpenCode Plugins:** https://opencode.ai/docs/plugins/
- **OpenCode Skills:** https://opencode.ai/docs/skills/
