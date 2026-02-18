# ADR-011: Site-nine as OpenCode Integration Platform

**Status:** SUPERSEDED BY ADR-013
**Date:** 2026-02-15
**Deciders:** Tucker (Director), Angra-mainyu (Architect)
**Related Tasks:** OPR-M-0129
**Supersedes:** ADR-010 (OpenCode Session Lifecycle Integration for Auto-Dismissal)


## Context

### The Architectural Shift

Site-nine currently operates as a **loosely coupled CLI tool** that agents use manually within OpenCode sessions. This
ADR proposes a fundamental paradigm shift: **site-nine as a tightly integrated OpenCode platform** where the mission
lifecycle, agent orchestration, and task management are seamlessly synchronized with OpenCode's session lifecycle.

**Current paradigm (loosely coupled):**
```
OpenCode Session
    ↓ (manual)
Agent invokes: s9 mission start
    ↓ (agent works)
Agent invokes: s9 mission heartbeat (periodically)
    ↓ (manual)
Agent invokes: s9 mission end
    ↓ (if forgotten)
Zombie mission remains ACTIVE forever
```

**Proposed paradigm (tightly integrated, opt-in):**
```
Director launches: s9 summon architect angra-mainyu
    ↓ (launches OpenCode with initial instruction)
OpenCode session starts
    ↓ (instruction injected)
Agent receives: "Your role is architect, persona is angra-mainyu. Initialize your mission with mission-init"
    ↓ (agent executes mission initialization workflow)
mission-init → role-record → persona-select → persona-record:
    - Gets sessionID from OpenCode tool context
    - Creates mission with opencode_session_id=sessionID
    - Records role and persona
    - Mission transitions from ROLE_PENDING → PERSONA_PENDING → ACTIVE
    ↓ (automatic lifecycle tracking)
Plugin detects session.updated → updates last_activity_at timestamp
    ↓ (automatic suspend on close)
Plugin detects session.deleted → Mission.suspend() (can resume later)
    ↓ (manual ending when truly done)
Director uses /dismiss → session-end skill → Mission.end() + close tasks + goodbye
    ↓
Mission lifecycle: auto-suspend (safe), explicit end (final)

Alternative: Director launches regular OpenCode session
    ↓
OpenCode session starts normally
    ↓
Agent works WITHOUT mission-init skill
    ↓
No mission created, plugin does nothing
    ↓
Director works on personal projects, no site-nine tracking
```

### Why Tight Integration?

**Problem 1: Manual coupling is fragile**
- Agents must remember to start missions
- Agents must remember to send heartbeats
- Agents must remember to end missions
- Any step forgotten → zombie missions, stale data, operational debt

**Problem 2: Detection is a workaround**
- ADR-010 proposed detecting which session corresponds to a mission
- This is solving the wrong problem: sessions and missions should be **inherently coupled**
- Detection is retrofitting a connection that should exist from the start

**Problem 3: Limited orchestration capabilities**
- Current model: Director summons one agent at a time, talks directly to each
- Director must context-switch between agents
- No way for Admin to orchestrate multiple background workers
- Messaging system underutilized

**Problem 4: Missed opportunities**
- OpenCode plugins have access to rich session context (messages, diffs, metadata)
- This context could enable powerful automation (auto-summaries, stuck detection, task correlation)
- Current architecture doesn't leverage this

### The Vision: Site-nine as OpenCode Platform

**Core principle:** Site-nine sessions launched via `s9 summon` are automatically tracked as missions. OpenCode sessions
launched directly remain independent.

**Opt-in model:**
- `s9 summon` → Site-nine managed session (automatic mission tracking)
- `opencode` → Regular session (no site-nine involvement)
- Skills create missions explicitly using session ID from context
- Same OpenCode, different modes depending on launch method

**Key capabilities enabled:**
1. **Automatic lifecycle management:** Site-nine sessions auto-track missions
2. **Session-first architecture:** Session ID is ground truth, no detection needed
3. **Desk mode orchestration:** Background agents await instructions from Admin
4. **Rich automation:** Plugin uses session context for summaries, stuck detection, task claiming
5. **Invisible infrastructure:** Director doesn't think about missions - they just work
6. **Coexistence:** Regular OpenCode sessions work normally for non-site-nine tasks


## Technical Research Findings

During design, we investigated OpenCode's architecture to understand platform capabilities and constraints. Key
findings:

### Session Schema (Verified: `packages/sdk/js/src/gen/types.gen.ts`)

**Session object structure:**
- Fixed fields: `id`, `projectID`, `directory`, `parentID`, `title`, `version`, timing, summary, share, revert
- **No custom metadata fields** - Sessions don't support arbitrary key-value metadata
- Session titles are mutable (users can rename via UI)
- Message parts support `metadata: { [key: string]: unknown }` but sessions themselves don't

**Implication:** Cannot use session metadata for mission tracking. Session ID is the only reliable identifier.

### Tool Context Capabilities (Verified: `packages/plugin/src/tool.ts`)

**Custom tools receive rich context:**
- ✅ `context.sessionID` - Direct access to current session UUID
- ✅ `context.messageID` - Current message identifier
- ✅ `context.agent` - Agent type/name
- ✅ `context.directory` - Session working directory
- ✅ `context.worktree` - Git worktree root

**Tool execution constraints:**
- ❌ **Tools cannot be interactive** - `stdio: ["ignore", "pipe", "pipe"]` (stdin ignored)
- ❌ **Tools cannot call other tools** - No SDK client access, no tool-to-tool communication
- ❌ **`context.ask()` is permission-only** - Only for yes/no permission requests, not interactive prompts
- ✅ **Can execute Python scripts** - Tools can spawn scripts and pass context via stdin JSON

**Implication:** Skills must be decomposed into:
1. **Code-based skills** (TypeScript + Python) for deterministic persistence operations
2. **Agent-driven skills** (markdown instructions) for interactive selection/orchestration workflows

### OpenCode TUI (Verified: `packages/opencode/src/cli/cmd/tui/routes/session/index.tsx`)

**Output rendering:**
- ❌ **ANSI color codes are stripped** - `stripAnsi()` called explicitly on tool output
- ✅ **Markdown formatting works** - Supports GitHub-flavored markdown
- ✅ **Plain text works** - Simple formatted output displays correctly

**Implication:** Skills should output markdown for formatting, not ANSI codes.

### Plugin Capabilities (Verified: `packages/plugin/src/index.ts`)

**Event system:**
- ✅ `session.created` - New session started
- ✅ `session.updated` - Session state changed (messages, tool calls, edits)
- ✅ `session.deleted` - Session ended/closed
- ✅ Session ID available in events: `event.properties.info.id`
- ✅ Can use `shell.env` hook to inject environment variables

**SDK limitations:**
- ❌ No `session.current()` method - Must track session ID explicitly
- ❌ Cannot query session metadata - Only events provide info

**Implication:** Plugin can monitor lifecycle and execute s9 commands, but cannot introspect session state directly.

### Architecture Decisions from Research

Based on these findings, we made several key architectural choices:

1. **Session ID as ground truth:** Store `opencode_session_id` in missions table, use as unique identifier
2. **Decomposed skills architecture:** Separate code-based (persistence) from agent-driven (interactive) skills
3. **Mission initialization workflow:** Multi-step agent-orchestrated flow (mission-init → role-select/record →
   persona-select/record)
4. **Plugin as lifecycle monitor:** Plugin tracks events and executes s9 commands, doesn't create missions
5. **Markdown output formatting:** All skill output uses markdown, not ANSI codes
6. **No metadata passing:** Skills receive session ID directly from tool context, no env vars or title markers needed


## Decision

We will architect site-nine as a **tightly integrated OpenCode platform** with **opt-in session management**. Director
launches site-nine sessions via `s9 summon` (replacing the current summon command), which launches OpenCode and passes
initial instructions that trigger the mission initialization workflow. Regular `opencode` launches remain independent.

### 0. Unified Summon Command (Replaces Current Summon)

**The `s9 summon` command becomes the session launcher:**

```bash
# Outside OpenCode: Launch new session
s9 summon [role] [persona]

# Case 1: Fully specified
s9 summon architect angra-mainyu
# → Launches OpenCode
# → Initial message: "Your role is architect, persona is angra-mainyu. Initialize your mission with mission-init"
# → Agent: mission-init → role-record architect → persona-select angra-mainyu → persona-record
# → Mission ACTIVE

# Case 2: Role only
s9 summon architect
# → Initial message: "Your role is architect. Initialize your mission with mission-init"
# → Agent: mission-init → role-record architect → persona-select (auto-selects) → persona-record
# → Mission ACTIVE

# Case 3: Nothing specified
s9 summon
# → Initial message: "Initialize your mission with mission-init"
# → Agent: mission-init → role-select → role-record → persona-select (auto-selects) → persona-record
# → Mission ACTIVE

# Inside OpenCode: Summon into current session
/summon [role] [persona]
# → Creates child session with same instruction pattern
# → Enables multi-agent collaboration in parent/child sessions
```

**Key differences from CURRENT implementation:**

**What exists now (manual, loosely coupled):**
- Agent manually invokes `s9 mission start` in session-start skill
- Agent manually invokes `s9 mission heartbeat` periodically (often forgotten)
- Agent manually invokes `s9 mission end` in session-end skill (if remembered)
- No integration with OpenCode session lifecycle
- No automatic suspend/resume capability
- Zombie missions remain ACTIVE forever if agent forgets to end them
- No detection or cleanup of stale missions

**What's changing (automatic, tightly integrated):**
- **`s9 summon` integration:** CLI launches OpenCode and triggers mission-init workflow automatically
- **Plugin-driven lifecycle:** TypeScript plugin observes session events, auto-suspends on `session.deleted`
- **Decomposed skills:** Code-based (Python, persistence) vs agent-driven (Markdown, selection)
- **Suspend by default:** Missions suspended when OpenCode closes (resumable, safe)
- **Explicit ending:** `/dismiss` slash command invokes session-end skill for graceful closure
- **Resume capability:** `s9 summon --resume` auto-resumes recent mission, or `--resume <id-or-codename>` for specific mission
- **Stale detection:** `s9 doctor` identifies and cleans up missions suspended for days
- **Session binding safeguard:** mission-init checks if session already bound to prevent double-binding

**How it works:**

1. **`s9 summon` command:**
   - Parses optional role/persona arguments
   - Generates initial instruction message
   - Launches OpenCode with instruction as first message: `opencode --message "Your role is..."`

2. **Agent receives instruction:**
   - Sees role/persona if provided
   - Executes mission-init skill (creates mission record using `context.sessionID` provided by OpenCode)

3. **Agent orchestrates workflow:**
   - If role provided: calls role-record directly
   - If role missing: calls role-select (shows dashboard), then role-record
   - Calls persona-select (auto-selects by default, or uses provided persona)
   - Calls persona-record (mission becomes ACTIVE)

4. **Skills use session ID directly:**
   - Each skill receives `context.sessionID` from OpenCode
   - No metadata parsing or detection needed
   - Direct database operations via imported Python functions

5. **Plugin monitors lifecycle:**
   - Heartbeat on `session.updated`
   - Auto-suspend on `session.deleted`


### 1. Session-First Architecture

**Session ID becomes the primary correlation key:**

```sql
-- Migration: Make session ID primary correlation field
ALTER TABLE missions ADD COLUMN opencode_session_id TEXT UNIQUE;
CREATE INDEX idx_missions_session_id ON missions(opencode_session_id);

-- Missions are always tied to OpenCode sessions
-- Query by session: O(1) lookup
SELECT * FROM missions WHERE opencode_session_id = ?
```

**Skills operate on session IDs:**

Skills receive session ID from OpenCode tool context and use it directly:

```python
# mission-init skill (TypeScript wrapper + Python implementation)
# Receives context.sessionID from OpenCode
# Creates mission record with opencode_session_id

# Example Python implementation:
def initialize_mission(session_id: str) -> dict:
    db = Database()
    cursor = db.execute(
        "INSERT INTO missions (opencode_session_id, status) VALUES (?, ?)",
        (session_id, "ROLE_PENDING")
    )
    return {"mission_id": cursor.lastrowid, "session_id": session_id}
```

**Database queries by session ID:**

```sql
-- Query mission by session ID (O(1) lookup)
SELECT * FROM missions WHERE opencode_session_id = ?

-- All mission operations use session ID as primary key
UPDATE missions SET status = ? WHERE opencode_session_id = ?
```

**Benefits:**
- Zero detection complexity
- Perfect synchronization between OpenCode and site-nine
- Session ID is authoritative source of truth
- Simple, fast lookups
- Skills have direct database access (no CLI subprocess overhead)

### 2. Automatic Lifecycle Management via Plugin

The site-nine plugin provides lifecycle monitoring for automatic activity tracking and session-end detection. All
mission creation and management is handled by skills, with the plugin observing session events to track last activity
and trigger cleanup on session close.


**Design Principle: Skills Own Persistence, Plugin Maintains Lifecycle**

The plugin's core responsibilities are minimal and focused:

1. **Activity tracking:** Updates `last_activity_at` timestamp on session events (throttled to max 1/min for
   performance). This provides analytics and UI data, but is NOT used for zombie detection—agents waiting for input is
   normal and expected.

2. **Session termination handling:** When `session.deleted` fires (OpenCode closes), the plugin auto-suspends the
   mission. This is the only reliable way to detect session termination without false positives from idle time.

3. **Comprehensive logging:** All lifecycle events are logged for debugging and audit trail.

Mission creation and management remains the responsibility of skills. The plugin never creates missions, invokes CLI
commands, or manages mission state beyond suspend on termination.


**Create `.opencode/plugins/site-nine.ts`:**

```typescript
import type { Plugin } from "@opencode-ai/plugin"

/**
 * site-nine plugin
 * 
 * Lifecycle monitoring for site-nine missions. This plugin observes OpenCode session events
 * and maintains automatic heartbeats and session cleanup, but does NOT create or manage missions.
 * All mission CRUD operations are handled by skills using direct database access.
 */
export const SiteNine: Plugin = async ({ $ }) => {
  console.info('[site-nine] Plugin loaded')
  
  return {
    event: async ({ event }) => {
      const sessionId = event.properties?.id
      if (!sessionId) return

      try {
        switch (event.type) {
          case "session.updated":
            await handleSessionUpdated(sessionId)
            break

          case "session.deleted":
            await handleSessionDeleted(sessionId)
            break
        }
      } catch (error) {
        console.error(`[site-nine] Plugin error for session ${sessionId}:`, error)
        // Never crash OpenCode - silently log and continue
      }
    },
  }
}

/**
 * Track last activity timestamp for analytics and UI (throttled to 1/min to prevent excessive DB writes)
 */
const lastActivityUpdate = new Map<string, number>()
const ACTIVITY_THROTTLE_MS = 60 * 1000 // 1 minute

async function handleSessionUpdated(sessionId: string) {
  const now = Date.now()
  const last = lastActivityUpdate.get(sessionId) || 0
  
  if (now - last < ACTIVITY_THROTTLE_MS) {
    // Too soon, skip update (prevents DB write on every keystroke)
    return
  }
  
  console.debug(`[site-nine] Session ${sessionId} updated, checking for mission`)
  
  // Check if mission exists for this session (query database directly)
  const mission = await queryMissionBySessionId(sessionId)
  
  if (!mission || mission.status !== 'ACTIVE') {
    // No active mission for this session
    return
  }
  
  console.debug(`[site-nine] Updating last activity for mission ${mission.id}`)
  
  // Update last_activity_at timestamp in database
  await updateMissionActivity(mission.id)
  lastActivityUpdate.set(sessionId, now)
}

/**
 * Automatic session suspension when OpenCode closes
 * 
 * IMPORTANT: Session closure does NOT mean mission is finished.
 * - Director might accidentally close OpenCode
 * - Terminal might crash
 * - Director might switch contexts (terminal → neovim → different terminal)
 * 
 * Solution: Auto-SUSPEND (not END) missions when session closes.
 * Director must explicitly use /dismiss command to truly end a mission.
 */
async function handleSessionDeleted(sessionId: string) {
  console.info(`[site-nine] Session ${sessionId} deleted, checking for mission`)
  
  // Check if mission exists for this session
  const mission = await queryMissionBySessionId(sessionId)
  
  if (!mission) {
    console.debug(`[site-nine] No mission found for session ${sessionId}`)
    lastActivityUpdate.delete(sessionId)
    return
  }
  
  if (mission.status === 'ACTIVE') {
    console.info(`[site-nine] Auto-suspending mission ${mission.id} for closed session ${sessionId}`)
    await suspendMission(mission.id, 'Session closed - auto-suspended by plugin')
  } else {
    console.debug(`[site-nine] Mission ${mission.id} not active (status: ${mission.status}), skipping suspend`)
  }
  
  lastActivityUpdate.delete(sessionId)
}

/**
 * Helper: Query mission by session ID
 */
async function queryMissionBySessionId(sessionId: string) {
  const result = execSync(`s9 mission query --session-id ${sessionId} --format json`, { encoding: 'utf-8' })
  return JSON.parse(result)
}

/**
 * Helper: Update mission last activity timestamp
 */
async function updateMissionActivity(missionId: number) {
  execSync(`s9 mission update ${missionId} --report-activity`)
}

/**
 * Helper: Suspend mission with reason
 * 
 * Invokes Python script to suspend the mission (does NOT close tasks - they remain UNDERWAY).
 * Mission can be resumed later with `s9 summon --resume` or `s9 summon --resume <id-or-codename>`.
 */
async function suspendMission(missionId: number, reason: string) {
  execSync(`s9 mission suspend ${missionId} --reason "${reason}"`)
}
```


**Current Lifecycle Flow:**

1. Director runs `s9 summon architect` or `s9 summon desk`
2. Summon command invokes mission-init skill → Creates mission record
3. Mission-init invokes role-select + persona-select skills → Updates mission with role/persona
4. OpenCode launches with session ID available via `context.sessionID` in all skill tools
5. Agent works → Claims tasks (task-claim), updates progress (task-update), closes tasks (task-close)
6. **Three possible endings:**
   - **A. Graceful dismissal:** Director uses `/dismiss` → session-end skill runs → Mission ENDED, tasks closed
   - **B. Session closes (crash/switch):** `session.deleted` event fires → Plugin auto-suspends → Mission SUSPENDED
   - **C. Stale cleanup:** Mission SUSPENDED for days → `s9 doctor` or manual `s9 mission end` → Mission ENDED


**Task Workflow During Session:**

```
Agent claims first task
    ↓
task-claim skill (s9 task claim TASK_ID --mission M --role R)
    ↓
Agent works on task
    ↓
task-update skill (s9 task update TASK_ID --notes "progress...")
    ↓
Task complete
    ↓
task-close skill (s9 task close TASK_ID --status COMPLETE --notes "summary")
    ↓
Agent claims next task (repeat cycle)
    ↓
...continues until session ends...
    ↓
THREE POSSIBLE ENDINGS:

A. Graceful dismissal (preferred):
   Director uses /dismiss → session-end skill runs → Mission ENDED, tasks closed

B. Session closes unexpectedly:
   OpenCode crashes/closed accidentally → session.deleted fires → Plugin auto-suspends mission
   → Mission status = SUSPENDED (can resume later with `s9 summon --resume` or specify mission)

C. Stale mission cleanup:
   Mission SUSPENDED for days → `s9 doctor` detects stale mission → Prompts to end
   OR Director manually runs: `s9 mission end <mission-id>`
```

**Key Distinctions:**
- **task-close** = End one task (mid-session, happens many times)
- **Mission suspend** = Auto-suspend on session close (resumable)
- **Mission end** = Explicit ending via `/dismiss` or stale cleanup (final)
- **Idle ≠ Dead** = Agent waiting for Director input shows as idle but session is alive


**Why "Last Activity" Instead of "Heartbeat"?**

Traditional heartbeats serve as keep-alive signals to detect dead processes. In site-nine with OpenCode integration,
this is unnecessary:

- **Session exists** → OpenCode running → Mission active
- **Session deleted** → OpenCode closed → Mission auto-suspended (not ended, Director may resume)

The `last_activity_at` timestamp serves different purposes:
- **Analytics:** Track how much active time vs. idle time per mission
- **UI/Dashboard:** Show Director when agent last did something
- **NOT for zombie detection:** An old timestamp doesn't mean the session is dead
- **Stale detection:** Combined with SUSPENDED status, helps identify missions that need cleanup

**Common scenarios:**
- **Idle but alive:** Agent completes task, waits 30 minutes for Director input (normal)
- **Crashed/closed:** OpenCode crashes → Mission SUSPENDED → Director resumes later with `s9 summon --resume`
- **Context switch:** Close terminal session → Open in neovim → Resume same mission (no data loss)
- **Truly done:** Director uses `/dismiss` → Mission ENDED (can't resume)

**Common scenario:** Agent completes a task, then waits 30 minutes for Director to provide next instructions. The
`last_activity_at` timestamp is 30 minutes old, but this is perfectly normal - the agent is idle but alive, waiting
for input.

**Only desk mode has idle timeout** because background workers shouldn't run indefinitely without work. Interactive
sessions can be idle as long as the Director keeps OpenCode open.


**Implementation Challenges:**

The plugin implementation above requires:

1. **Database access from TypeScript plugin:**
   - Plugin needs to query missions table to check if mission exists for session
   - Plugin needs to update `last_activity_at` timestamps
   - Plugin needs to suspend missions when sessions end
   - **Solution:** Plugin invokes Python scripts that import site-nine modules for all database interactions. The
     TypeScript plugin NEVER accesses the database directly - all persistence operations go through Python scripts that
     use the existing site-nine database layer

2. **Session closure automation:**
   - When OpenCode closes, `session.deleted` event fires
   - Plugin must SUSPEND mission in database (not END - Director may want to resume)
   - Tasks remain UNDERWAY (not closed) so work can continue after resume
   - **Solution:** Plugin invokes Python script that:
     - Calls `Mission.suspend(session_id, reason="session_closed")`
     - Sets mission.status = 'SUSPENDED'
     - Records suspension_time and reason
     - Logs the suspension
     - Does NOT close tasks

3. **Graceful mission ending:**
   - Director needs way to explicitly END a mission (not just suspend)
   - **Solution:** `/dismiss` slash command invokes session-end skill
   - session-end skill is agent-driven: documentation, task closure, goodbye messages
   - Only explicit dismissal truly ends the mission (sets status='ENDED', closes tasks)

4. **Stale mission cleanup:**
   - Missions suspended for days/weeks accumulate
   - Need automated detection and cleanup
   - **Solution:** `s9 doctor` command:
     - Queries for SUSPENDED missions older than N days
     - Prompts Director to review and end stale missions
     - Can batch-end with `s9 doctor --auto-clean --older-than 7d`
   - Manual cleanup: `s9 mission end <mission-id>` works without OpenCode

5. **Preventing double-binding:**
   - Risk: Session already bound to ACTIVE/SUSPENDED mission, user tries to summon again
   - Could create nested missions or duplicate missions for same session
   - **Solution:** mission-init skill checks for existing binding:
     - Query: `SELECT * FROM missions WHERE opencode_session_id = ? AND status IN ('ACTIVE', 'SUSPENDED')`
     - If found: Return error with mission details and resume instructions
     - If not found: Proceed with mission creation
   - Prevents accidentally creating multiple missions in same session

6. **Logging:**
   - All site-nine operations (CLI, skills, plugin) must log for debugging and audit trail
   - Use consistent log format: `[site-nine] Component: Message`
   - Log levels: debug (verbose), info (important events), warn (recoverable issues), error (failures)


**Why This Plugin Design?**

This design maintains clear separation of concerns compared to the current implementation:

**Current implementation:**
- Manual mission lifecycle via skills (session-start, session-end)
- Director must remember to invoke skills at session start/end
- No automatic activity tracking or suspend-on-close
- OpenCode sessions have no persistent link to missions

**Proposed design:**
- **Skills handle mission CRUD**: Creating, updating, suspending, ending, querying missions (Python with direct database
  access)
- **Plugin handles lifecycle automation**: Last activity tracking and auto-suspend on session close (TypeScript invoking
  Python scripts)
- **session-end skill handles graceful closure**: Agent-driven documentation, task closure, goodbye messages (invoked by
  `/dismiss` command)
- **All database access goes through Python**: Plugin never accesses database directly, always invokes `s9` CLI or
  Python scripts that import site-nine modules
- **Suspend ≠ End**: Auto-suspend is safe/resumable, explicit end is final


### 3. Desk Mode for Multi-Agent Orchestration

**The orchestration model:**
```
Director (human)
    ↓ speaks to
Admin Agent (OpenCode session A, visible)
    ├─ summons → Engineer (OpenCode session B, background "desk" mode)
    ├─ summons → Architect (OpenCode session C, background "desk" mode)
    └─ summons → Operator (OpenCode session D, background "desk" mode)

Admin orchestrates workers via messaging system
Workers await instructions in background
Director only interacts with Admin
```

**Desk mode characteristics:**
- Background OpenCode session invoked via `opencode run` (no TUI)
- Mission mode set to "desk" in database
- Agent processes messages one at a time, auto-closes after each
- Python polling script manages the message loop
- Can be terminated by orchestrator via SIGTERM

**Database schema:**
```sql
-- Add mode field to missions
ALTER TABLE missions ADD COLUMN mode TEXT DEFAULT 'interactive';
-- Values: 'interactive' (default), 'desk' (background worker)

-- Desk mode sessions tracked differently
CREATE INDEX idx_missions_mode ON missions(mode);
```

**Summoning desk mode agents:**
```bash
# Admin summons a background worker (role is REQUIRED for --desk mode)
s9 summon engineer --desk

# This spawns a Python script that:
# 1. Runs: opencode run --title "Mission <codename>" "invoke mission-start skill with role=engineer"
# 2. Mission created with mode='desk', role set, OpenCode session auto-closes
# 3. Python script enters polling loop (checks database for messages)
# 4. Returns immediately so Admin can continue working
```

**Python polling script workflow:**

The `s9 summon <role> --desk` command spawns a background Python process that manages the desk agent lifecycle:

```python
#!/usr/bin/env python3
"""Desk mode polling script - manages message-driven agent lifecycle"""

import signal
import subprocess
import sys
import time
from site_nine.data import get_db, Message

# Global state
session_id = None
running = True

def sigterm_handler(signum, frame):
    """Graceful shutdown on SIGTERM from orchestrator"""
    global running
    running = False
    if session_id:
        # Invoke mission-end skill for graceful closure
        subprocess.run([
            "opencode", "run",
            "--session", session_id,
            "invoke mission-end skill with reason='desk agent terminated by orchestrator'"
        ])
    sys.exit(0)

signal.signal(signal.SIGTERM, sigterm_handler)

# Step 1: Initialize mission via opencode run
result = subprocess.run([
    "opencode", "run",
    "--title", f"Mission {codename}",
    "invoke mission-start skill with role=engineer, mode=desk"
], capture_output=True, text=True)

# Extract session ID from output or query database
session_id = get_session_id_from_db(codename)

# Step 2: Enter polling loop
while running:
    # Check for unread messages for this session
    db = get_db()
    messages = db.execute("""
        SELECT id, sender_session_id, subject, body
        FROM messages
        WHERE recipient_session_id = ? AND read_at IS NULL
        ORDER BY created_at ASC
    """, (session_id,)).fetchall()
    
    if messages:
        for msg in messages:
            # Resume session with message content
            subprocess.run([
                "opencode", "run",
                "--session", session_id,
                msg['body']  # Pass message body as instruction
            ])
            
            # Mark message as read
            db.execute("UPDATE messages SET read_at = ? WHERE id = ?",
                      (datetime.utcnow(), msg['id']))
            db.commit()
    
    # Sleep before next poll
    time.sleep(5)
```

**Key design insights:**

1. **No context blowup:** Each `opencode run` invocation is independent - the agent processes one message, completes, and
   exits. Context doesn't accumulate from polling.

2. **Auto-suspend between messages:** When `opencode run` exits, the plugin's `session.deleted` handler auto-suspends
   the mission. Next `opencode run --session <id>` resumes it.

3. **Graceful termination:** When Admin kills the Python script (SIGTERM), the signal handler invokes mission-end skill
   for proper cleanup.

4. **Session continuity:** The `--session` flag preserves conversation history across message invocations, so the agent
   remembers previous tasks.

**Admin orchestration commands:**
```bash
# Admin summons worker (spawns background Python process)
s9 summon engineer --desk
# Returns immediately, worker process runs in background

# Admin sends task to worker
s9 message send \
  --to-session <worker-session-id> \
  --subject "Implement feature" \
  --body "Add user authentication with JWT tokens"

# Python script polls, sees message, runs:
# opencode run --session <id> "Add user authentication with JWT tokens"
# Agent implements feature, opencode exits, plugin auto-suspends

# Admin checks worker status
s9 mission query --mode desk --status ACTIVE

# Admin terminates worker when done
s9 summon stop <worker-session-id>
# Sends SIGTERM to Python process
# Python handler runs: opencode run --session <id> "invoke mission-end skill"
# Mission ends gracefully, Python exits
```

**Plugin desk mode handling:**

The plugin does NOT need special desk mode handling because:

1. **Each message invocation is short-lived:** `opencode run` processes one message and exits immediately
2. **Auto-suspend works perfectly:** When `opencode run` exits, `session.deleted` fires → plugin auto-suspends mission
3. **No idle timeout needed:** Desk agents don't stay running between messages - the Python polling script manages
   timing
4. **Graceful termination via SIGTERM:** Python script's signal handler ensures mission-end skill runs before exit

The existing `session.deleted` handler in Section 2 is sufficient for desk mode lifecycle management.


### 4. Mission Lifecycle: Suspend, Resume, and Stale Detection

**The Problem:** Session closure ≠ Mission completion

When OpenCode closes (crash, terminal switch, accidental close), the mission isn't necessarily done - Director may want
to resume later. The solution: **suspend by default, end explicitly**.


**Mission Status States:**

```
ROLE_PENDING → PERSONA_PENDING → ACTIVE → SUSPENDED → ENDED
                                     ↓          ↓
                                     ↓          └─→ (resume) → ACTIVE
                                     └─────→ (explicit /dismiss) → ENDED
```

**Status transitions:**
- **ACTIVE → SUSPENDED:** Plugin auto-suspends on `session.deleted` (OpenCode closes)
- **SUSPENDED → ACTIVE:** Director resumes with `s9 summon --resume` (auto-resume recent) or `--resume <id-or-codename>`
- **ACTIVE → ENDED:** Director uses `/dismiss` command → session-end skill runs
- **SUSPENDED → ENDED:** Stale cleanup via `s9 doctor` or manual `s9 mission end <id>`


**The `/dismiss` Slash Command (already exists):**

The existing `/dismiss` command (`.opencode/commands/dismiss.md`) works seamlessly with the new architecture.

**Usage:**
```
/dismiss
/dismiss great work today, thank you!
```

**What it does:**
1. Invokes `session-end` skill (agent-driven)
2. Skill performs graceful closure:
   - Locates mission file
   - Reviews git status, commits, tasks
   - Updates mission file with summary
   - Closes UNDERWAY tasks (sets to PAUSED with notes)
   - Runs `s9 mission end <mission-id>` (sets status=ENDED)
   - Cleans up temporary files
   - Says goodbye with optional dismissal message
3. Mission is truly ENDED (cannot resume)

**Key distinction:**
- **Closing OpenCode** → Mission SUSPENDED (safe, resumable)
- **Using `/dismiss`** → Mission ENDED (final, with documentation)


**Mission Resume:**

**Usage:**
```bash
# Resume most recently suspended mission (auto-resume)
s9 summon --resume

# Resume specific mission by ID or codename
s9 summon --resume <mission-id-or-codename>

# Examples:
s9 summon --resume 123
s9 summon --resume crimson-thunder

# What happens:
# 1. Validates mission exists and is SUSPENDED
# 2. Updates mission.status = ACTIVE
# 3. Binds new OpenCode session to mission (updates opencode_session_id)
# 4. Launches OpenCode with context:
#      "Resuming mission <code-name>. Status: <task-count> tasks claimed, <N> complete, <M> underway."
# 5. Agent can continue work on UNDERWAY tasks
```

**Example flow:**
```
1. Director: s9 summon architect angra-mainyu
2. Agent claims task, starts work
3. Terminal crashes → session.deleted → Mission SUSPENDED
4. Director: s9 summon --resume          # Auto-resumes most recent
   OR: s9 summon --resume crimson-thunder # Resume by codename
5. Agent resumes work on same task
6. Work complete → Director: /dismiss → Mission ENDED
```


**Stale Mission Detection:**

**The `s9 doctor` command (already exists):**

The existing `s9 doctor` command will be enhanced to detect and offer cleanup of stale SUSPENDED missions.

```bash
# Interactive review of stale missions
s9 doctor

# Output (new stale mission detection):
# ⚠️  Found 3 stale missions (SUSPENDED > 7 days):
#
# Mission 45: Operation epic-specter (Architect: Angra-mainyu)
#   Suspended: 2026-02-09 (8 days ago)
#   Tasks: 2 UNDERWAY, 1 COMPLETE
#   Last activity: 2026-02-09 14:23
#
#   Options:
#   [R]esume  [E]nd  [S]kip  [Q]uit
#
# → User selects 'E' → Calls Mission.end(45, reason="stale_cleanup")
#                    → Auto-closes UNDERWAY tasks with status PAUSED

# Automated cleanup (dangerous, use with caution)
s9 doctor --auto-clean --older-than 30d
# Automatically ends all SUSPENDED missions older than 30 days
```

**Detection criteria:**
- Mission status = SUSPENDED
- `suspension_time` > N days (default 7, configurable)
- No recent activity (last_activity_at also old)

**What `s9 doctor` does:**
1. Queries: `SELECT * FROM missions WHERE status='SUSPENDED' AND suspension_time < datetime('now', '-7 days')`
2. For each stale mission:
   - Shows mission details (code name, persona, tasks, last activity)
   - Prompts Director: Resume, End, or Skip?
   - If End: Calls `Mission.end(id, reason="stale_cleanup")`
   - If Resume: Shows command to resume
3. Logs all actions for audit trail

**Manual cleanup (no OpenCode needed):**

```bash
# End specific mission
s9 mission end <mission-id>
s9 mission end 45 --reason "abandoned, switching priorities"

# What it does:
# - Sets mission.status = ENDED
# - Auto-closes UNDERWAY tasks with status PAUSED
# - Records end_time and reason
# - Works without OpenCode session (CLI only)
```


**Database schema additions:**

```sql
-- Add suspension tracking
ALTER TABLE missions ADD COLUMN suspension_time TEXT;
ALTER TABLE missions ADD COLUMN suspension_reason TEXT;

-- Mission status enum (application-level constraint)
-- Values: ROLE_PENDING, PERSONA_PENDING, ACTIVE, SUSPENDED, ENDED

-- Index for stale detection query
CREATE INDEX idx_missions_suspended ON missions(status, suspension_time)
  WHERE status = 'SUSPENDED';
```


### 5. Decomposed Skills Architecture

**Key principle: Separate deterministic code from agent-driven interaction.**

**Why decompose skills:**
- **Clear separation:** Code handles persistence, agents handle decision-making
- **Reusability:** Skip steps when data already provided (e.g., role pre-selected)
- **Token efficiency:** Code skills ~30 tokens, agent skills only run when needed
- **Testability:** Code skills have deterministic inputs/outputs
- **Flexibility:** Agents can orchestrate the flow based on context

**Architecture Pattern:**

Each workflow is decomposed into **code skills** (deterministic) and **agent-driven skills** (interactive):

```
.opencode/skills/
├── mission-init/        # CODE: Initialize mission, generate code name
├── role-select/         # AGENT: Show dashboard, get role choice
├── role-record/         # CODE: Update mission.role_name
├── persona-select/      # AGENT: Auto-select or get persona choice
├── persona-record/      # CODE: Update mission.persona_name, set ACTIVE
├── task-select/         # AGENT: Show tasks, get selection
├── task-claim/          # CODE: Update task.assigned_to
├── task-update/         # CODE: Update task progress
├── task-close/          # CODE: Update task.status
└── dashboard/           # CODE: Return formatted dashboard data
```

**Mission Start Flow:**

```
s9 summon [role] [persona]
    ↓
Agent receives: "Your role is {role}, persona is {persona}. Initialize mission with mission-init"
    ↓
┌─────────────────────────────────────────────┐
│ mission-init (CODE SKILL)                   │
│                                             │
│ Args: none                                  │
│ Returns: mission_id, code_name, status     │
│                                             │
│ Actions:                                    │
│ - Get sessionID from context               │
│ - Check if session already bound:          │
│     SELECT * FROM missions                 │
│     WHERE opencode_session_id = sessionID  │
│       AND status IN ('ACTIVE', 'SUSPENDED')│
│ - If bound: ERROR "Session already bound   │
│   to mission <id>. Use --resume to resume."│
│ - Generate mission code name               │
│ - Create mission record:                   │
│     opencode_session_id = sessionID        │
│     status = ROLE_PENDING                  │
│     code_name = generated                  │
│ - Return mission details                   │
└─────────────────────────────────────────────┘
    ↓
If role provided in summon → skip role-select
If role missing → agent runs role-select
    ↓
┌─────────────────────────────────────────────┐
│ role-select (AGENT-DRIVEN SKILL)            │
│                                             │
│ Args: mission_id                            │
│ Returns: dashboard + recommendations        │
│                                             │
│ Actions:                                    │
│ - Query task counts by role                │
│ - Calculate role recommendations           │
│ - Format dashboard output                  │
│ - Return markdown for agent to show        │
│                                             │
│ Agent then:                                 │
│ - Shows output to Director                 │
│ - Uses question tool if needed             │
│ - Gets role choice from Director           │
│ - Calls role-record with chosen role       │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ role-record (CODE SKILL)                    │
│                                             │
│ Args: mission_id, role                      │
│ Returns: confirmation                       │
│                                             │
│ Actions:                                    │
│ - Update mission.role_name = role          │
│ - Update mission.status = PERSONA_PENDING  │
│ - Return confirmation                      │
└─────────────────────────────────────────────┘
    ↓
If persona provided → persona-select (bio generation only)
If persona missing → persona-select (auto-select, default behavior)
    ↓
┌─────────────────────────────────────────────┐
│ persona-select (AGENT-DRIVEN SKILL)         │
│                                             │
│ Args: mission_id, role, persona (optional)  │
│ Returns: persona + bio                      │
│                                             │
│ Actions:                                    │
│ - If persona provided:                      │
│     - Generate bio for role/persona        │
│     - Return persona + bio                 │
│                                             │
│ - If persona missing (DEFAULT):             │
│     - AUTO-SELECT persona for role         │
│     - Generate bio for selected persona    │
│     - Return persona + bio                 │
│                                             │
│ - Only ask Director if:                     │
│     - Auto-select fails                    │
│     - Director explicitly requests choice  │
│                                             │
│ Agent then:                                 │
│ - Presents persona + bio to Director       │
│ - Confirms or gets override if needed      │
│ - Calls persona-record                     │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ persona-record (CODE SKILL)                 │
│                                             │
│ Args: mission_id, persona, bio              │
│ Returns: "Mission ACTIVE"                   │
│                                             │
│ Actions:                                    │
│ - Update mission.persona_name = persona    │
│ - Store bio in mission record              │
│ - Update mission.status = ACTIVE           │
│ - Return confirmation                      │
└─────────────────────────────────────────────┘
```

**Task Claiming Flow:**

```
Agent wants to claim task
    ↓
┌─────────────────────────────────────────────┐
│ task-select (AGENT-DRIVEN SKILL)            │
│                                             │
│ Args: filters (optional)                    │
│ Returns: task list + recommendations        │
│                                             │
│ Actions:                                    │
│ - Query tasks (by role, priority, tags)    │
│ - Calculate recommendations                │
│ - Format task details                      │
│ - Return markdown list                     │
│                                             │
│ Agent then:                                 │
│ - Shows tasks to Director if needed        │
│ - Chooses task based on context            │
│ - Calls task-claim with task_id            │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ task-claim (CODE SKILL)                     │
│                                             │
│ Args: task_id, mission_id                   │
│ Returns: confirmation                       │
│                                             │
│ Actions:                                    │
│ - Update task.assigned_to = mission_id     │
│ - Update task.status = IN_PROGRESS         │
│ - Create claim timestamp                   │
│ - Return task details                      │
└─────────────────────────────────────────────┘
    ↓
Agent works on task...
    ↓
┌─────────────────────────────────────────────┐
│ task-update (CODE SKILL)                    │
│                                             │
│ Args: task_id, progress_notes, time_spent   │
│ Returns: confirmation                       │
│                                             │
│ Actions:                                    │
│ - Append to task.progress_notes            │
│ - Increment task.time_spent                │
│ - Update task.updated_at                   │
│ - Return confirmation                      │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ task-close (CODE SKILL)                     │
│                                             │
│ Args: task_id, status, notes                │
│ Returns: confirmation                       │
│                                             │
│ Actions:                                    │
│ - Update task.status (COMPLETED/PAUSED/etc)│
│ - Set task.completed_at                    │
│ - Record final notes                       │
│ - Return summary                           │
└─────────────────────────────────────────────┘
```

**Implementation Pattern:**

All skills follow this TypeScript wrapper + Python implementation pattern:

`.opencode/skills/mission-init/tool.ts`:
```typescript
import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description: "Initialize a new site-nine mission",
  args: {},  // No args needed
  async execute(args, context) {
    const { sessionID, worktree } = context
    const script = path.join(worktree, ".opencode/skills/mission-init/execute.py")

    const input = JSON.stringify({ sessionID })
    const result = await Bun.$`echo ${input} | python3 ${script}`.text()
    return result.trim()
  },
})
```

`.opencode/skills/mission-init/execute.py`:
```python
#!/usr/bin/env python3
import sys
import json
from site_nine.models.mission import Mission
from site_nine.database import Database

def main():
    context = json.loads(sys.stdin.read())
    session_id = context['sessionID']

    db = Database()

    # Check if session is already bound to a mission
    existing = db.execute(
        """SELECT id, code_name, status FROM missions
           WHERE opencode_session_id = ?
           AND status IN ('ACTIVE', 'SUSPENDED')""",
        (session_id,)
    ).fetchone()
    
    if existing:
        mission_id, code_name, status = existing
        return f"""ERROR: Session already bound to mission

**Mission ID:** {mission_id}
**Code Name:** {code_name}
**Status:** {status}

Cannot create new mission in session that already has an active/suspended mission.

To resume this mission: Close this session and use `s9 summon --resume {mission_id}` or `s9 summon --resume {code_name}`
To work without mission tracking: Close this session and use `opencode` directly"""

    # Generate mission code name
    code_name = Mission.generate_code_name(db)

    # Create mission record
    mission = Mission.create(
        db=db,
        opencode_session_id=session_id,
        code_name=code_name,
        status='ROLE_PENDING'
    )

    return f"""Mission initialized!

**Mission ID:** {mission.id}
**Code Name:** {code_name}
**Session:** {session_id}
**Status:** ROLE_PENDING

Next: Select a role using role-select skill."""

if __name__ == '__main__':
    try:
        print(main())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
```

**Benefits:**

1. **Separation of concerns:** Code = persistence, Agent = decision-making
2. **Conditional execution:** Skip steps when data pre-provided
3. **Token efficiency:** Code skills tiny, agent skills only when interactive flow needed
4. **Reusability:** Code skills can be called from multiple workflows
5. **Testability:** Each skill has clear contract and can be tested independently
6. **Maintainability:** Changes to interactive logic don't affect persistence logic

**Output formatting guidelines:**
- Use plain text or markdown (OpenCode TUI strips ANSI color codes)
- Markdown formatting works well: `**bold**`, `- lists`, code blocks
- Structure output for both LLM comprehension and human readability
- No ANSI escape codes (they are stripped before display)

**Complete skill list:**

**Mission lifecycle (code):**
- `mission-init` - Initialize mission, generate code name, bind to session
- `role-record` - Update mission.role_name
- `persona-record` - Update mission.persona_name, set ACTIVE
- `mission-update` - Update mission progress notes
- `mission-heartbeat` - Manual heartbeat (usually automatic via plugin)

**Mission lifecycle (agent-driven):**
- `role-select` - Show dashboard, return role recommendations
- `persona-select` - Auto-select persona (default) or prompt if needed, generate bio
- `session-end` - End mission gracefully with documentation, task closure, goodbye (invoked by `/dismiss`)

**Task lifecycle (code):**
- `task-claim` - Claim task, update assigned_to
- `task-update` - Update task progress
- `task-close` - Close task with status

**Task lifecycle (agent-driven):**
- `task-select` - Query and show tasks, return recommendations

**Utilities (code):**
- `dashboard` - Return formatted dashboard data
- `handoff` - Hand off work to another agent


### 6. Enhanced Automation Capabilities

**Future Enhancement: With tight integration, the plugin could provide advanced automation.**

These capabilities are NOT part of the initial implementation (see Section 2 for minimal plugin), but represent future
possibilities once the decomposed skills architecture is stable.


**A. Auto-generate mission summaries from session context:**
```typescript
// Future: Extract meaningful summary from session history
function generateSummary(session: any): string {
  const messages = session.messages || []
  const lastMessages = messages.slice(-10) // Last 10 messages

  // Use simple heuristics or LLM to extract key points
  const summary = extractKeyPoints(lastMessages)
  return summary
}

// Future: Generate enhanced mission summaries when session closes
async function handleSessionDeleted(sessionId: string, client: any) {
  const session = await client.sessions.get(sessionId).catch(() => null)

  if (session) {
    const summary = generateSummary(session)
    // Store enhanced summary in mission record
    await updateMissionSummary(sessionId, summary)
  }
}
```


**B. Detect stuck agents and offer assistance:**
```typescript
// Future: Monitor idle sessions and notify agents
async function handleSessionIdle(sessionId: string, properties: any) {
  const idleDuration = properties.idleDuration

  if (idleDuration > 600 && idleDuration < 610) { // Idle for 10 min, notify once
    const mission = await queryMissionBySessionId(sessionId)

    if (mission) {
      // Future: Send in-session notification to agent
      // Requires OpenCode API for sending messages to active sessions
      console.info(`[site-nine] Session ${sessionId} idle for 10 minutes`)
    }
  }
}
```


**C. Automatically claim tasks based on session activity:**
```typescript
// Future: When engineer starts working on a file, auto-claim related tasks
async function handleSessionUpdated(sessionId: string, client: any) {
  const session = await client.sessions.get(sessionId)
  const recentDiffs = session.diffs?.slice(-5) || []

  if (recentDiffs.length > 0) {
    const modifiedFiles = recentDiffs.map((d: any) => d.path)
    const mission = await queryMissionBySessionId(sessionId)

    if (mission) {
      // Query database for unclaimed tasks related to these files
      const unclaimedTasks = await queryUnclaimedTasksByFiles(modifiedFiles)

      if (unclaimedTasks.length > 0) {
        // Auto-claim first matching task directly in database
        await claimTask(unclaimedTasks[0].id, mission.id)
        console.info(`[site-nine] Auto-claimed task ${unclaimedTasks[0].id} based on file activity`)
      }
    }
  }
}
```


**D. Cross-reference code changes with task descriptions:**
```typescript
// Future: When mission ends, link diffs to completed tasks
async function handleSessionDeleted(sessionId: string, client: any) {
  const session = await client.sessions.get(sessionId)
  const mission = await queryMissionBySessionId(sessionId)

  if (mission) {
    // Get tasks claimed by this mission
    const tasks = await queryTasksByMission(mission.id)

    // Suggest task completion based on diffs
    for (const task of tasks) {
      const relatedDiffs = session.diffs.filter((d: any) =>
        task.related_files?.includes(d.path)
      )

      if (relatedDiffs.length > 0 && task.status !== 'DONE') {
        console.info(`[site-nine] Task ${task.id} may be complete (${relatedDiffs.length} related changes)`)
        // Future: Auto-mark as complete or trigger agent notification
      }
    }
  }
}
```


**Important Notes:**

1. **These are future enhancements**, not current implementation
2. **Plugin remains minimal** until decomposed skills are stable (see Section 2)
3. **All automation should use direct database access**, not CLI subprocess calls
4. **Skills should handle business logic**, plugin only provides lifecycle hooks
5. **OpenCode API support needed** for some features (skill invocation, in-session messaging)


### 7. Comprehensive Logging

**Logging is core functionality, not optional.** All site-nine components must log operations for debugging, audit
trail, and transparency.


**Logging Requirements:**

All site-nine operations MUST log:
- **CLI commands** (`s9 task claim`, `s9 mission start`, etc.)
- **Skills** (mission-init, task-claim, task-close, etc.)
- **Plugin** (activity tracking, session events, auto-suspend)
- **Database operations** (creates, updates, queries)
- **Errors and warnings** (failures, recoverable issues)


**Log Format:**

```
[site-nine] Component: Message
```

Examples:
```
[site-nine] CLI: task claim ENG-H-0037 --mission 42 --role Engineer
[site-nine] Skill:mission-init: Created mission 42 for session abc-123
[site-nine] Plugin: Heartbeat sent for mission 42
[site-nine] Database: Updated mission 42 heartbeat timestamp
[site-nine] Error: Failed to query mission for session xyz-789: database locked
```


**Log Levels:**

- **debug:** Verbose details for troubleshooting (session events, database queries)
- **info:** Important operations (mission created, task claimed, heartbeat sent)
- **warn:** Recoverable issues (database retry, missing session, stale data)
- **error:** Failures that prevent operation (query failed, missing required field)


**Implementation:**

- **Python (CLI/Skills):** Use standard `logging` module with consistent formatter
- **TypeScript (Plugin):** Use `console.debug/info/warn/error` with `[site-nine]` prefix
- **Configuration:** Default log level INFO, DEBUG available via environment variable
- **Output:** stderr for all logs (keeps stdout clean for programmatic use)


**Benefits:**

- Debugging: Trace exact sequence of operations when issues occur
- Audit trail: Record who did what when for compliance and review
- Transparency: Director can see what site-nine is doing under the hood
- Monitoring: Detect patterns, performance issues, error rates


## Alternatives Considered

### Alternative 1: Keep Loose Coupling (Status Quo)

**Approach:** Maintain current architecture where site-nine is independent CLI tool used manually by agents.

**Pros:**
- No breaking changes
- Works without OpenCode
- Simple mental model (CLI tool)
- Already implemented

**Cons:**
- Manual intervention required (agents must remember to start/end missions)
- Zombie missions persist on crashes/unexpected closures
- No orchestration capabilities
- Missed automation opportunities
- Higher cognitive load on Director and agents

**Rejected because:** Doesn't solve fundamental problems (zombie missions, manual coupling fragility). We want to
leverage OpenCode's capabilities, not work around them.

### Alternative 2: Detection-Based Integration (ADR-010)

**Approach:** Use OpenCode plugin to detect session closures and correlate with missions via existing detection logic.

**Pros:**
- No database schema changes
- Reuses proven detection cascade
- Solves zombie mission problem
- Backward compatible

**Cons:**
- Detection is a workaround, not a solution
- Still requires manual mission start/heartbeat
- Doesn't enable orchestration
- Misses automation opportunities
- Treats symptom (zombie missions) not cause (loose coupling)

**Rejected because:** Director's insight revealed this is solving the wrong problem. Sessions and missions should be
inherently coupled, not retroactively correlated. Tight integration unlocks capabilities beyond zombie mission cleanup.

### Alternative 3: Wrapper Script Around OpenCode

**Approach:** Create `s9-opencode` wrapper that launches OpenCode and manages mission lifecycle externally.

**Pros:**
- No plugin required
- Can trap signals and run cleanup
- Works with any OpenCode version

**Cons:**
- Fragile (easy to bypass by running `opencode` directly)
- Doesn't handle crashes (signal traps don't fire)
- Can't access session context (messages, diffs)
- No automatic heartbeats
- Poor UX (requires different command)

**Rejected because:** External wrappers are fragile and miss session context. Plugin integration is more robust and
provides richer capabilities.

### Alternative 4: OpenCode as Optional Enhancement

**Approach:** Make tight integration optional - site-nine works standalone, OpenCode integration enhances when
available.

**Pros:**
- Maintains standalone CLI tool functionality
- Gradual adoption possible
- Backward compatible
- No forced dependency

**Cons:**
- Two code paths to maintain (with/without OpenCode)
- Complex logic to handle both modes
- Unclear which mode is "primary"
- May lead to feature disparity

**Decision:** We'll maintain backward compatibility but make OpenCode integration the **primary, recommended path**.
Standalone CLI use is supported but not optimized. Most users work in OpenCode, so that's where we focus.


## Consequences

### Positive

- ✅ **Eliminates manual coupling:** Mission lifecycle fully automatic with OpenCode sessions
- ✅ **Zero zombie missions:** Impossible to have active mission without active session
- ✅ **Automatic heartbeats:** Every session activity triggers heartbeat (no manual tracking)
- ✅ **Rich automation:** Plugin uses session context for summaries, task claiming, stuck detection
- ✅ **Orchestration unlocked:** Admin can coordinate multiple background workers via desk mode
- ✅ **Reduced cognitive load:** Director doesn't think about missions, they just work
- ✅ **Better UX:** Invisible infrastructure that works seamlessly
- ✅ **Leverages platform:** Uses OpenCode capabilities instead of working around them
- ✅ **Scalable:** Supports multi-agent workflows naturally

### Negative

- ⚠️ **OpenCode dependency:** Tight integration requires OpenCode for site-nine sessions (regular CLI still works)
- ⚠️ **Database migration:** Requires adding `opencode_session_id` and `mode` columns
- ⚠️ **Launcher required:** Director must use `s9 summon` instead of `opencode` for tracked sessions
- ⚠️ **Workflow change:** Requires learning new summon command (but enables automation)
- ⚠️ **Plugin complexity:** More sophisticated plugin logic (more code to maintain)
- ⚠️ **Session context handling:** Skills must properly use `context.sessionID` from OpenCode
- ⚠️ **Desk mode new concept:** Requires documenting and explaining background workers
- ⚠️ **Migration effort:** Existing missions may need backfilling session IDs

### Risks & Mitigation

| Risk | Mitigation |
|------|-----------|
| **Session context not available** | - OpenCode provides `context.sessionID` in skill tools<br>- Verified via source code investigation (see Technical Research)<br>- Fallback to manual `s9 mission start` if needed<br>- Skills can query mission by session ID |
| **Multiple concurrent sessions collision** | - Session IDs are globally unique (OpenCode guarantees)<br>- Each session has unique context object<br>- No shared state between sessions<br>- Database uses session_id as unique constraint |
| **Bypass via manual commands** | - Document: "Use `s9 summon`, not `opencode` directly"<br>- Plugin can still trigger auto-suspend when sessions close<br>- Manual mission commands still available for debugging<br>- Clear separation: summon = tracked, opencode = untracked |
| **Non-site-nine sessions accidentally tracked** | - Plugin checks for mission existence before acting<br>- No auto-creation of missions (skills create explicitly)<br>- Default to no-op if no mission found for session<br>- Log when plugin skips non-s9 sessions |
| **Session ID not unique across projects** | - Include project directory in correlation<br>- Session IDs are globally unique in OpenCode<br>- Query by (session_id, project_path) tuple if needed |
| **Desk mode sessions leak resources** | - Python polling script manages desk agent lifecycle<br>- SIGTERM handler ensures graceful termination via mission-end skill<br>- `s9 summon stop <session-id>` command to terminate desk agents<br>- Monitor active desk sessions via `s9 mission query --mode desk --status ACTIVE` |
| **Plugin uses stale session data** | - Cache session context with TTL<br>- Refetch on critical operations<br>- Handle API errors gracefully |
| **Workflow adoption friction** | - Clear onboarding docs: "Use `s9 summon` not `opencode`"<br>- Add shell alias: `alias s9s='s9 summon'`<br>- Skills can still work manually as fallback<br>- Both modes supported during transition |
| **Desk mode message polling is inefficient** | - Use exponential backoff for polling<br>- Consider webhook-based messaging (future)<br>- Add rate limiting<br>- Monitor message queue performance |


## Implementation Plan

### Phase 0: Research & Prototype (✅ COMPLETED)

**Tasks:**
1. ✅ Research OpenCode session metadata mechanisms:
   - ✅ Checked OpenCode source code (`packages/sdk/js/src/gen/types.gen.ts`)
   - ✅ Verified Session schema has no custom metadata fields
   - ✅ Checked plugin tool context (`packages/plugin/src/tool.ts`)
   - ✅ Discovered `context.sessionID` available in all skill tools
   - ✅ Verified plugin events receive `event.properties` with session info
2. ✅ Analyzed session context passing:
   - ✅ Skills can access session ID via `context.sessionID` (recommended)
   - ✅ No need for title markers or external storage
   - ✅ Session ID flows naturally from OpenCode to skills
3. ✅ Designed decomposed skills architecture:
   - ✅ Separate code-based skills (Python) from agent-driven skills (markdown)
   - ✅ Skills handle all persistence via direct database access
   - ✅ Agent orchestrates multi-step workflows
   - ✅ Plugin remains minimal (monitoring only)
4. ✅ Documented final architecture with implementation details

**Findings:**
- OpenCode provides `context.sessionID` in all skill tool invocations
- Skills can access session context without title markers or metadata passing
- Best approach: Skills own all persistence, plugin only monitors lifecycle
- Mission initialization is multi-step: init → role → persona (agent orchestrated)
- Plugin should NOT auto-create missions or call CLI commands

**Acceptance criteria:**
- ✅ Determined session context mechanism (`context.sessionID`)
- ✅ Designed decomposed skills architecture
- ✅ Verified plugin capabilities and limitations
- ✅ Documented approach with clear separation of concerns

### Phase 1: Database Schema & CLI Foundation

**Tasks:**
1. Create migration: Add `opencode_session_id TEXT UNIQUE` to missions table
2. Create migration: Add `mode TEXT DEFAULT 'interactive'` to missions table
3. Add indexes: `idx_missions_session_id`, `idx_missions_mode`
4. Implement: `s9 summon <role> [persona] [--desk]`
5. Update CLI: Add `--session-id` parameter to mission commands (for debugging)
6. Implement: `s9 mission get --session-id <id>`
7. Write tests: Migration, summon command, session-based queries

**Acceptance criteria:**
- Migration runs cleanly on existing databases
- `s9 summon` successfully launches OpenCode and invokes mission-init skill
- CLI commands accept session IDs for querying
- Backward compatibility maintained (old commands still work)

### Phase 2: Decomposed Skills Implementation

**Tasks:**
1. Implement mission-init skill (code-based): Create mission record with session ID from context
2. Implement role-select skill (agent-driven): Query dashboard, return recommendations
3. Implement role-record skill (code-based): Update mission.role_name
4. Implement persona-select skill (agent-driven): Auto-select or get Director choice
5. Implement persona-record skill (code-based): Update mission.persona_name, set ACTIVE
6. Implement task-claim skill (code-based): Update task.assigned_to
7. Implement task-update skill (code-based): Update task progress
8. Implement task-close skill (code-based): Update task.status
9. Update s9 summon command to invoke mission-init skill
10. Test complete workflow: summon → init → role → persona → active

**Acceptance criteria:**
- Skills decomposed into code (Python) vs. agent-driven (markdown)
- Context.sessionID properly passed to all skills
- Mission initialization multi-step: init → role → persona
- Skills handle database operations directly (no CLI subprocess calls)
- Agent orchestrates workflow based on provided arguments
- Auto-selection works for persona (default behavior)


### Phase 3: Plugin Implementation (Core Lifecycle Automation)

**Tasks:**
1. Create `.opencode/plugins/site-nine.ts`
2. Implement TypeScript helpers to invoke Python scripts for database operations (query missions, update
   last_activity_at, suspend mission, end mission)
3. Implement `session.updated` handler with throttled activity tracking (max 1/min DB writes)
4. Implement `session.deleted` handler to auto-suspend missions
5. Implement `session.idle` handler for desk mode timeout detection (10min max to catch stuck agents)
6. Add comprehensive logging throughout plugin (debug, info, warn, error levels)
7. Add database migration: `ALTER TABLE missions ADD COLUMN last_activity_at TEXT`
8. Test plugin loads without errors
9. Test activity tracking updates on session activity
10. Test auto-suspend on session deletion
11. Document Python script interface for plugin database operations (query, update, suspend, end missions)

**Acceptance criteria:**
- Plugin loads automatically on OpenCode startup
- Plugin tracks last activity (max 1/min updates) when sessions are active
- Plugin does NOT treat idle time as indicator of dead sessions (for interactive mode)
- Plugin auto-suspends missions when sessions end (marks SUSPENDED with auto-suspend reason)
- Plugin logs all operations for debugging and audit trail
- Plugin does NOT create missions (skills handle creation)
- Plugin does NOT interfere with normal OpenCode operation
- Database access layer tested and documented


### Phase 4: Desk Mode & Orchestration

**Tasks:**
1. Implement: `s9 summon <role> --desk` command (role required for desk mode)
2. Create Python polling script that manages desk agent lifecycle
3. Implement SIGTERM handler for graceful desk agent termination
4. Add `s9 summon stop <session-id>` command to terminate desk agents
5. Update messaging system to support session-based addressing
6. Test `opencode run --session <id>` resume functionality
7. Write tests: Desk mode summoning, message polling, graceful shutdown

**Acceptance criteria:**
- Admin can summon background workers with `s9 summon <role> --desk`
- Python polling script successfully manages desk agent lifecycle
- Workers process messages via `opencode run --session <id>` invocations
- Each message invocation auto-closes, preventing context blowup
- Admin can send tasks to workers via messaging system
- Desk agents can be terminated via `s9 summon stop <session-id>`
- SIGTERM handler ensures mission-end skill runs before Python script exits
- Session context preserved across multiple `opencode run` invocations

### Phase 5: Enhanced Automation

**Tasks:**
1. Implement session history analysis for auto-summaries
2. Implement stuck agent detection (idle timeout with notification)
3. Implement automatic task claiming based on file activity
4. Implement task completion suggestion based on diffs
5. Add configuration options for automation behaviors
6. Write tests: Summary generation, stuck detection, auto-claiming

**Acceptance criteria:**
- Auto-generated summaries capture key session information
- Stuck agents receive helpful notifications
- Tasks auto-claimed when agent modifies related files
- Task completion suggestions accurate and useful


### Phase 6: Documentation & Rollout

**Tasks:**
1. Update all skill documentation to reflect automatic lifecycle
2. Write desk mode orchestration guide for Admin agents
3. Create migration guide for existing missions
4. Document plugin behavior and configuration options
5. Create troubleshooting guide for common issues
6. Announce feature to team with examples
7. Monitor for 2 weeks: Plugin logs, desk mode usage, automation accuracy

**Acceptance criteria:**
- All documentation reflects new paradigm
- Examples demonstrate orchestration workflows
- Troubleshooting guide addresses common issues
- Team understands new capabilities
- No major issues during monitoring period

### Phase 7: Advanced Features (Future)

**Potential enhancements after initial rollout:**
1. LLM-powered session summarization (better than heuristics)
2. Webhook-based messaging (replace polling)
3. Multi-level orchestration (Admin → Sub-Admin → Workers)
4. Session context search (query across all sessions)
5. Desk mode resource limits (CPU, memory, timeout)
6. Plugin configuration UI in OpenCode
7. Integration with external tools (GitHub, Jira, etc.)


## Migration Path

### For Existing Missions

**Option 1: Backfill session IDs (best effort)**
```bash
# Script to correlate existing missions with OpenCode sessions
s9 mission backfill-sessions

# Uses detection cascade to find session for each mission
# Populates opencode_session_id where possible
# Missions without detectable session remain null (supported)
```

**Option 2: Leave existing missions as-is**
- Existing missions continue to work (session_id is nullable)
- Only new missions get session IDs (via plugin auto-registration)
- Old missions cleaned up manually or via `s9 doctor`

**Recommendation:** Option 2 (gradual migration, no risk to existing data)

### For Skills

**session-start skill:**
- Deprecated in favor of `s9 summon` automatic initialization
- Can still be used for custom setup if needed
- Should detect if mission already exists (check by session ID) and skip gracefully

**session-end skill:**
- **RESTORED:** Required for graceful mission ending via `/dismiss` command
- Plugin auto-suspends on session close, but explicit `/dismiss` truly ends mission
- Skill handles: documentation, git commits, task closure, goodbye messages
- Invoked by `/dismiss` slash command (not automatic on session close)
- Removes `/dismiss` command references (if any exist) - that's now the trigger mechanism itself

**task-close skill:**
- ✅ Already exists and properly documented
- Used mid-session to close individual tasks (COMPLETE, PAUSED, BLOCKED, ABORTED)
- Agent uses this many times per session as tasks are completed
- This is NOT session ending - it's task completion

**task-claim skill:**
- ✅ Already exists and properly documented  
- Used to start new tasks during a session
- Agent claims task → works on it → closes it → claims next task (repeat)

**Backward compatibility:**
- Skills continue to work with manual workflows
- Automatic summon workflow is preferred but optional
- Manual `session-start` still supported for edge cases
- `/dismiss` command invokes session-end skill for graceful closure

### For Workflows

**Current workflow (manual, still works):**
1. Director summons agent via `opencode`
2. Agent runs `session-start` skill manually
3. Agent works (claims tasks, updates, closes tasks)
4. Director uses `/dismiss` → session-end skill runs → Mission ENDED
   OR Director closes OpenCode → Plugin auto-suspends → Mission SUSPENDED (resumable)

**New workflow (automatic via summon):**
1. Director runs: `s9 summon architect angra-mainyu`
2. Summon command invokes mission-init skill → Creates mission with session ID
3. Summon command invokes role/persona selection → Updates mission to ACTIVE
4. OpenCode launches, agent works:
   - Claims tasks via task-claim skill
   - Updates progress via task-update skill
   - Closes completed tasks via task-close skill
   - Repeats for multiple tasks during session
5. Director uses `/dismiss` → session-end skill runs → Mission ENDED
   OR Director closes OpenCode → Plugin auto-suspends → Mission SUSPENDED

**Resume workflow (new capability):**
1. Mission was auto-suspended (OpenCode crashed or closed)
2. Director runs: `s9 summon --resume` (auto-resumes most recent)
   OR: `s9 summon --resume <id-or-codename>` (specific mission)
3. Mission status: SUSPENDED → ACTIVE
4. Agent continues work on same mission, tasks still UNDERWAY
5. When truly done: `/dismiss` → Mission ENDED

**Alternative workflow (personal work):**
1. Director runs: `opencode` (no site-nine tracking)
2. Works on personal project
3. Closes OpenCode
4. No mission created, no tracking overhead

**Orchestration workflow (new capability):**
1. Director runs: `s9 summon admin admin-prime`
2. Admin summons workers: `s9 summon engineer --mode desk`
3. Admin sends tasks via messaging
4. Workers process in background (claim → work → close → repeat)
5. Workers' sessions end when orchestrator closes them or timeout occurs


## Open Questions

### Resolved During Research

1. **~~Metadata passing mechanism~~ (RESOLVED)**
   - **Finding:** OpenCode sessions have no custom metadata fields (verified via source code inspection)
   - **Solution:** Custom tools receive `context.sessionID` directly - no metadata passing needed
   - **Implementation:** Skills use session ID from tool context, store in `missions.opencode_session_id`

2. **~~Session ID uniqueness~~ (RESOLVED)**
   - **Finding:** OpenCode session IDs are UUIDs, globally unique (verified via TypeScript types)
   - **Solution:** Use session ID as unique identifier, no composite key needed

3. **~~Tool interactivity~~ (RESOLVED)**
   - **Finding:** Tools cannot be interactive (stdin is ignored, no access to `context.ask()` for prompts)
   - **Solution:** Decompose skills into code-based (persistence) and agent-driven (selection) types
   - **Implication:** Interactive flows must be agent-orchestrated, not tool-driven

### Remaining Open Questions

#### Architecture

1. **~~Desk mode session lifetime~~ (RESOLVED - NO LONGER APPLICABLE):**
   - Desk agents don't stay running between messages
   - Each `opencode run` invocation processes one message and auto-closes
   - No idle timeout needed - Python polling script manages timing
   - Resource cleanup via SIGTERM handler calling mission-end skill

2. **Automatic heartbeat frequency:**
   - `session.updated` fires frequently (potentially every message/tool call)
   - Do we heartbeat on every update or throttle?
   - Risk: Database write load if too frequent
   - **Recommendation:** Throttle to max 1 heartbeat per minute
   - **Decision needed:** Confirm throttle interval acceptable

3. **~~Manual vs automatic priority~~ (RESOLVED - NO LONGER APPLICABLE)**
   - Session ending is now fully automated via plugin on `session.deleted`
   - No manual session-end skill exists
   - Plugin always handles mission closure automatically
   - Agents can say goodbye naturally but don't need to invoke any skill

#### Implementation

4. **Plugin error handling:**
   - How aggressively should plugin retry failed commands?
   - Should plugin maintain local state/queue for reliability?
   - What happens if database is locked during auto-suspend?
   - **Recommendation:** No retries (log and continue), no local state (keep stateless)
   - **Decision needed:** Acceptable to lose heartbeat if DB unavailable?

5. **~~Desk mode implementation~~ (RESOLVED):**
   - ✅ `opencode run` provides headless execution
   - ✅ `opencode run --session <id>` resumes sessions successfully
   - ✅ Python polling script manages lifecycle with SIGTERM handler
   - ✅ Each message invocation auto-closes, preventing context blowup
   - **Action:** Implement `s9 summon <role> --desk` command in Phase 4

6. **Launcher UX:**
   - Should `s9 summon` exec into OpenCode (replace process)?
   - Or spawn OpenCode as child process and exit?
   - How to capture session ID for desk mode (return to caller)?
   - **Recommendation:** Spawn and exec for interactive, spawn and return ID for desk mode
   - **Decision needed:** Confirm exec behavior acceptable

7. **~~Auto-summary quality~~ (RESOLVED - NO LONGER APPLICABLE)**
   - Session ending is now a simple database operation (Mission.end())
   - No summaries generated on session close
   - Mission records contain task history for audit trail
   - Agents can provide summaries during work if desired, but not required on closure

#### Rollout

8. **Breaking changes communication:**
   - How to communicate CLI signature changes to agents?
   - Should we maintain old signatures with deprecation warnings?
   - Migration timeline (deprecation period)?
   - **Recommendation:** Update skill markdown files, add release notes
   - **Decision needed:** Acceptable to break existing workflows immediately?

9. **Testing strategy:**
   - How to test multi-agent orchestration scenarios?
   - How to mock OpenCode session lifecycle in tests?
   - Integration tests vs unit tests balance?
   - **Recommendation:** Heavy integration testing with real OpenCode sessions
   - **Decision needed:** Test coverage requirements for approval


## References

- **Supersedes:** ADR-010 (OpenCode Session Lifecycle Integration for Auto-Dismissal)
- **Related Task:** OPR-M-0129 (Investigate OpenCode session lifecycle hooks)
- **Related Epic:** EPC-H-0004 (Multi-Tool Adapter System)
- **Related ADR:** ADR-006 (Entity Model Clarity - Personas, Missions, Agents)
- **Related ADR:** ADR-008 (Agent Messaging System)
- **Related ADR:** ADR-009 (Agent Coordination Patterns)
- **OpenCode Plugin Documentation:** https://opencode.ai/docs/plugins
- **OpenCode SDK Documentation:** https://opencode.ai/docs/sdk
- **Skills Reference:**
  - `session-start` skill (`.opencode/skills/session-start/SKILL.md`)
  - `session-end` skill (`.opencode/skills/session-end/SKILL.md`) - invoked by `/dismiss` command


## Notes

### Design Philosophy

**Principle: Platform-Native > Loosely Coupled**

We embrace OpenCode as our primary platform rather than treating it as just another environment. This means:
- Design for OpenCode first, standalone second
- Leverage platform capabilities deeply (session context, lifecycle hooks, SDK)
- Accept platform dependency as worthwhile tradeoff
- Provide exceptional experience within platform

**Principle: Invisible Infrastructure**

The best infrastructure is invisible. Director should think about **work**, not **mission tracking**:
- Sessions automatically become missions
- Heartbeats happen automatically
- Cleanup happens automatically
- Everything logged, nothing manual

**Principle: Orchestration Over Micromanagement**

Enable Admin to **orchestrate** workers rather than Director **micromanaging** individual agents:
- Admin as conductor, workers as orchestra
- Messaging as coordination mechanism
- Director talks to one agent (Admin), not many
- Natural hierarchy mimics real organizations

**Principle: Rich Context Enables Rich Automation**

OpenCode sessions contain rich context (messages, diffs, tool calls). Use this to:
- Generate meaningful summaries automatically
- Detect when agents need help
- Claim tasks based on actual work
- Cross-reference changes with task descriptions

### Future Vision

This ADR lays groundwork for **site-nine as multi-agent orchestration platform**:

**Phase 1 (this ADR):** Tight OpenCode integration, automatic lifecycle, desk mode
**Phase 2:** Multi-level orchestration (Admin → Sub-Admin → Specialists)
**Phase 3:** Cross-session collaboration (agents working together on shared tasks)
**Phase 4:** External integrations (GitHub, Jira, Slack, etc.)
**Phase 5:** Autonomous agent teams (self-organizing based on task requirements)

The session-first architecture and desk mode orchestration are **foundational building blocks** for this vision.

---

**Status:** PROPOSED
**Next Steps:**
1. Director review and approval of architectural design
2. Director decision on open questions (heartbeat frequency, error handling policy)
3. Create implementation tasks for Phase 1 (database migration, skills, plugin)
4. Prototype mission initialization workflow to validate multi-step agent orchestration
5. Begin implementation once approved
