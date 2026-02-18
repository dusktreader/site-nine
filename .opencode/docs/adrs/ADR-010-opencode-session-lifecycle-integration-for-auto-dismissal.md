# ADR-010: OpenCode Session Lifecycle Integration for Auto-Dismissal

**Status:** REJECTED  
**Date:** 2026-02-15  
**Deciders:** Tucker (Director), Angra-mainyu (Architect)  
**Related Tasks:** OPR-M-0129  
**Superseded By:** ADR-011 (Site-nine as OpenCode Integration Platform)  

## Context

**NOTE: This ADR was rejected in favor of a more comprehensive architectural vision. See ADR-011: Site-nine as
OpenCode Integration Platform for the revised approach that embraces tight integration and session-first design.**

### The Zombie Mission Problem

Site-nine currently suffers from "zombie missions" - mission records that remain in ACTIVE or IDLE status indefinitely
after their OpenCode sessions have ended. This occurs when:

1. **Director closes OpenCode window** without using `/dismiss` command
2. **OpenCode crashes or exits unexpectedly** during an agent session
3. **Network disconnection** causes session to terminate
4. **Agent forgets to run session-end skill** before OpenCode closes

**Current workflow requires:**
- Director must explicitly use `/dismiss` command
- Agent must execute session-end skill when dismissed
- Agent must run `s9 mission end <mission-id>` to update database
- All of these steps must happen BEFORE the OpenCode session closes

**If any step is skipped:**
- Mission remains ACTIVE in database indefinitely
- `s9 doctor` flags missions without heartbeat for >8h as "stale"
- Dashboard shows inflated active mission counts
- Tasks remain claimed by ended missions
- System accumulates operational debt

**Current workarounds:**
- Manual cleanup: Director runs `s9 mission end <id>` for each zombie
- `s9 doctor` detection: Flags stale missions but doesn't auto-fix
- Documentation emphasis: Skills repeatedly warn agents not to end prematurely

**Why this is insufficient:**
- Director must remember to dismiss agents (extra cognitive load)
- Agents have no control over unexpected session termination
- No automatic recovery from crashes or disconnections
- Cleanup is reactive rather than preventive

### Root Cause Analysis

The fundamental issue is **coupling between OpenCode session lifecycle and site-nine mission lifecycle**:

```
Current (manual):
OpenCode Session ❌ Site-nine Mission
     ↓                      ↓
  Closes              Still ACTIVE
                           ↓
                    Manual cleanup required

Desired (automatic):
OpenCode Session ✅ Site-nine Mission
     ↓                      ↓
  Closes              Auto-ends
                           ↓
                    Clean state
```

The mission lifecycle should be **automatically synchronized** with the OpenCode session lifecycle, not dependent on
manual agent/Director actions.

### OpenCode Plugin System

OpenCode provides a robust plugin system that can hook into session lifecycle events:

**Available Session Events:**
- `session.created` - New session starts
- `session.deleted` - Session is deleted/closed
- `session.idle` - Session becomes idle
- `session.error` - Session encounters error
- `session.updated` - Session metadata changes

**Plugin Capabilities:**
- Execute shell commands via Bun's `$` API
- Access OpenCode SDK client for API calls
- Hook into lifecycle events reactively
- Local plugins: `.opencode/plugins/*.{js,ts}`
- npm plugins: Specified in `opencode.json`

**Plugin execution context:**
```typescript
export const MyPlugin = async ({ project, client, $, directory, worktree }) => {
  return {
    event: async ({ event }) => {
      if (event.type === "session.deleted") {
        // Execute cleanup logic
        await $`s9 mission end <mission-id>`
      }
    },
  }
}
```

### Mission Identification Challenge

The core technical challenge is **mapping OpenCode sessions to site-nine missions**:

**What OpenCode plugins know:**
- Session ID (e.g., `aFZ8rQJo`) from `session.deleted` event
- Session metadata (title, directory, timestamps)
- Project directory path

**What site-nine missions track:**
- Mission ID (e.g., `113`)
- Persona name, role, codename
- Mission file path
- Start/end times
- **No direct reference to OpenCode session ID**

**Existing session detection solution:**

Site-nine **already solves this problem** in the `s9 mission rename-tui` command. The
`OpenCodeSessionManager.detect_session()` method (see `src/site_nine/opencode/manager.py:74-169`) uses a cascade of
detection methods to correlate missions with OpenCode sessions:

1. **DB recency (most reliable):** Queries OpenCode's SQLite database for the most recently updated session in the
   current project directory
2. **UUID marker:** Searches for UUID marker in session data (if provided)
3. **Content correlation:** Compares git changes with session diffs
4. **Diff recency:** Finds most recent session diff file
5. **Session recency:** Falls back to most recent session file

**Key architectural insight:**

The plugin can leverage this **existing, battle-tested session detection mechanism** rather than requiring new database
schema changes. The approach:

1. Plugin receives `session.deleted` event with session ID
2. Plugin queries for ACTIVE/IDLE missions in the project
3. For each mission, run existing `detect_session()` logic to find its OpenCode session
4. Compare detected session ID with event session ID
5. If match found, auto-end that mission

**Why this is architecturally superior:**

- **Reuses proven code:** `detect_session()` already handles edge cases (multiple sessions, renamed sessions, etc.)
- **No schema migration:** Works with existing database structure
- **Backward compatible:** Handles legacy missions without modification
- **Maintainable:** Single source of truth for session detection logic
- **Robust:** Falls back through multiple detection methods if primary fails

## Decision

We will implement an **OpenCode lifecycle plugin** that uses existing session detection logic to automatically end
missions when their sessions close. This approach requires **no database schema changes** and leverages proven code
paths already in production.

### Core Approach: Reuse Existing Session Detection

Instead of adding new database fields, the plugin will:

1. Receive `session.deleted` event from OpenCode (with session ID)
2. Query site-nine for ACTIVE/IDLE missions in the current project
3. For each mission, invoke existing `detect_session()` logic to find its OpenCode session
4. Compare detected session ID with event session ID
5. Auto-end mission if IDs match

**Architectural advantages:**
- **Zero schema migration:** Works with existing database structure
- **Proven detection logic:** Reuses `OpenCodeSessionManager.detect_session()` from `rename-tui` command
- **Graceful fallback:** Detection cascade handles edge cases (UUID markers, content correlation, etc.)
- **Single source of truth:** Session detection logic maintained in one place
- **Backward compatible:** Handles all existing missions without modification

### Implementation: OpenCode Lifecycle Plugin

**Create `.opencode/plugins/site-nine-lifecycle.ts`:**

```typescript
import type { Plugin } from "@opencode-ai/plugin"

export const SiteNineLifecycle: Plugin = async ({ $, directory }) => {
  return {
    event: async ({ event }) => {
      // Only handle session deletion events
      if (event.type !== "session.deleted") {
        return
      }

      const eventSessionId = event.properties?.id
      if (!eventSessionId) {
        console.warn("[site-nine] Session deleted event missing session ID")
        return
      }

      try {
        // Find active missions in the current project
        const missionsResult = await $`s9 mission list --status ACTIVE --status IDLE --format json`
        const missions = JSON.parse(missionsResult.stdout)

        if (!missions || missions.length === 0) {
          console.info(`[site-nine] No active missions found for session ${eventSessionId}`)
          return
        }

        // For each mission, detect its OpenCode session and compare
        for (const mission of missions) {
          try {
            // Use existing detection logic to find mission's session
            const detectResult = await $`s9 mission detect-session --mission-id ${mission.id} --format json`
            const detection = JSON.parse(detectResult.stdout)

            if (detection.session_id === eventSessionId) {
              // Found the mission corresponding to this session
              console.info(`[site-nine] Auto-ending mission ${mission.id} (${mission.persona_name}) for session ${eventSessionId}`)
              await $`s9 mission end ${mission.id} --reason "session_closed" --auto`
              console.info(`[site-nine] Successfully ended mission ${mission.id}`)
              
              // Only end one mission per session
              return
            }
          } catch (detectError) {
            // Detection failed for this mission - skip it
            console.debug(`[site-nine] Could not detect session for mission ${mission.id}:`, detectError)
            continue
          }
        }

        console.info(`[site-nine] No mission matched session ${eventSessionId}`)
      } catch (error) {
        console.error(`[site-nine] Failed to auto-end mission for session ${eventSessionId}:`, error)
        // Don't throw - plugin errors shouldn't crash OpenCode
      }
    },
  }
}
```

**Key design elements:**

1. **Leverages existing detection:** Calls `s9 mission detect-session` command (wraps `OpenCodeSessionManager.detect_session()`)
2. **Minimal query surface:** Only queries for ACTIVE/IDLE missions (fast)
3. **One mission per session:** Stops after first match (enforces 1:1 relationship)
4. **Graceful degradation:** If detection fails for a mission, continues to next
5. **Comprehensive logging:** Info/debug/error levels for troubleshooting
6. **Never crashes OpenCode:** All errors caught and logged

**CLI Support:**

Add new commands to support plugin operations:

```bash
# Detect which OpenCode session corresponds to a mission (wraps OpenCodeSessionManager.detect_session())
s9 mission detect-session --mission-id <mission-id> --format json
# Returns: {"session_id": "aFZ8rQJo", "detection_method": "db_recency", "confidence": "high"}

# List missions with status filter
s9 mission list --status ACTIVE --status IDLE --format json

# End mission with automation support
s9 mission end <mission-id> --reason <reason> --auto
```

**New command: `s9 mission detect-session`**

Wraps existing `OpenCodeSessionManager.detect_session()` logic for CLI/plugin use:

```python
# In src/site_nine/cli/mission.py
@mission.command()
@click.option("--mission-id", required=True, type=int)
@click.option("--format", type=click.Choice(["json", "text"]), default="text")
def detect_session(mission_id: int, format: str):
    """Detect which OpenCode session corresponds to a mission."""
    from site_nine.opencode.manager import OpenCodeSessionManager
    
    mission = db.get_mission(mission_id)
    if not mission:
        raise click.ClickException(f"Mission {mission_id} not found")
    
    manager = OpenCodeSessionManager()
    session_id = manager.detect_session(mission.mission_file_path)
    
    if format == "json":
        result = {
            "session_id": session_id,
            "detection_method": manager.last_detection_method,  # Added to manager
            "confidence": manager.last_detection_confidence,    # Added to manager
        }
        click.echo(json.dumps(result))
    else:
        click.echo(f"Detected session: {session_id}")
```

**`--auto` flag behavior:**
- Skips interactive prompts
- Minimal mission file updates (no manual Summary/Outcomes editing)
- Records auto-end reason in mission record
- Suitable for plugin/automation use

### Session-to-Mission Correlation Logic

**Flow:**

1. Plugin receives `session.deleted` event with session ID `S`
2. Query: Get all missions with status ACTIVE or IDLE
3. For each mission `M`:
   - Call `detect_session(M)` → returns session ID `S'`
   - If `S == S'`: This mission corresponds to the deleted session → Auto-end
   - If `S != S'`: Continue to next mission
4. If no match found: Log and exit (non-agent session or already ended)

**Detection cascade (existing logic in `OpenCodeSessionManager`):**

```python
def detect_session(mission_file_path: Path) -> str | None:
    """Detect OpenCode session ID for a mission using cascade of methods."""
    
    # Method 1: Query OpenCode SQLite DB for recent session (most reliable)
    session_id = self._detect_via_db_recency(mission_file_path)
    if session_id:
        return session_id
    
    # Method 2: Search for UUID marker in session data
    session_id = self._detect_via_db_uuid_marker(mission_file_path)
    if session_id:
        return session_id
    
    # Method 3: Correlate git changes with session diffs
    session_id = self._detect_via_content_correlation(mission_file_path)
    if session_id:
        return session_id
    
    # Method 4: Find most recent session diff file
    session_id = self._detect_via_diff_recency(mission_file_path)
    if session_id:
        return session_id
    
    # Method 5: Find most recent session file (fallback)
    session_id = self._detect_via_session_recency(mission_file_path)
    return session_id
```

**Why this is robust:**

- **DB recency:** Works for 95% of cases (normal session lifecycle)
- **UUID marker:** Catches renamed sessions (set during `rename-tui`)
- **Content correlation:** Handles edge cases where DB is stale
- **Diff recency:** Works even if session metadata is corrupted
- **Session recency:** Last-resort fallback

**Performance considerations:**

- Query returns 0-5 missions typically (most users have ≤1 active mission)
- Detection methods are fast (DB query is milliseconds)
- Plugin timeout: 5 seconds max (prevents hanging OpenCode shutdown)
- Async execution: Non-blocking

### Integration Points

**Modified workflows:**

1. **session-start skill:**
   - No changes required
   - Existing workflow (mission registration, session rename) provides sufficient context for detection
   - UUID marker set during `rename-tui` enables detection cascade

2. **session-end skill:**
   - No changes needed
   - Manual dismissal still runs full workflow
   - Sets status to ENDED (plugin skips already-ended missions)

3. **Plugin activation:**
   - Automatically loaded from `.opencode/plugins/`
   - Only activates on `session.deleted` events
   - Idempotent: Checks mission status before ending
   - Uses existing detection logic (no new code paths)

**Deployment:**
- Plugin file added to project `.opencode/plugins/`
- Auto-loads on OpenCode startup
- No user configuration required
- No database migrations required

## Alternatives Considered

### Alternative 1: Periodic Cleanup Daemon

**Approach:** Run a background process that periodically checks for stale missions (no heartbeat for >8h) and
auto-ends them.

**Pros:**
- Simple to implement (cron job or systemd timer)
- No OpenCode integration required
- Works for all missions regardless of OpenCode usage

**Cons:**
- Reactive, not preventive (8h delay before cleanup)
- Requires separate daemon process (operational overhead)
- Doesn't solve immediate problem (session closes, mission stays active for hours)
- Heartbeat-based detection can have false positives (agent taking long break)
- No graceful handling of crashes (mission file may be incomplete)

**Rejected because:** Doesn't address root cause (session-mission coupling). Adding a daemon for cleanup is treating
the symptom, not the disease. We want immediate synchronization, not delayed cleanup.

### Alternative 2: Store Session ID in Database

**Approach:** Add `opencode_session_id` column to missions table, store during session-start, query directly in plugin.

**Pros:**
- Fast O(1) lookup (indexed column)
- No detection cascade needed
- Direct 1:1 mapping

**Cons:**
- Requires database migration (ALTER TABLE, CREATE INDEX)
- Requires modifying session-start skill to capture session ID
- Adds operational complexity (new CLI command, skill updates)
- Doesn't work for existing missions (needs backfill or fallback)
- Duplicates data (session ID already inferable from detection logic)
- More moving parts = more potential failure modes

**Rejected because:** Existing detection logic already solves this problem reliably. Adding database fields would
increase complexity without significant performance benefit (detection is fast, missions list is small). We prefer
reusing proven code over adding new schema. The YAGNI principle applies: detection works well enough that we don't need
explicit storage.

### Alternative 3: Parse Session ID from Mission Files

**Approach:** Store session ID only in mission markdown file (not database), parse file when plugin needs to find
mission.

**Pros:**
- No database migration required
- Session ID visible in human-readable mission file
- Simple implementation

**Cons:**
- File parsing is slow and error-prone (YAML frontmatter or regex)
- No indexing (O(n) scan of all mission files on every session.deleted)
- Race conditions (file may be locked during write)
- Doesn't work if mission file is corrupted or missing
- Plugin execution happens outside agent context (may not have file access)
- Still requires session ID capture during session-start

### Alternative 4: Heartbeat Timeout with Automatic End

**Approach:** Enhance existing heartbeat system to automatically end missions after N minutes without heartbeat.

**Pros:**
- Uses existing heartbeat infrastructure
- No OpenCode integration required
- Simple threshold-based logic

**Cons:**
- Requires choosing timeout threshold (5 min? 30 min? 2 hours?)
  - Too short: False positives (agent taking break gets auto-ended)
  - Too long: Zombies linger for extended period
- Doesn't distinguish between "agent working silently" and "session closed"
- No immediate response to session closure
- Aggressive timeout might interrupt legitimate long-running operations
- Still requires periodic daemon to check heartbeats

**Rejected because:** Can't distinguish between "silent but active" and "session closed". We want immediate,
event-driven cleanup, not time-based heuristics.

### Alternative 5: Manual Cleanup Command (Status Quo++)

**Approach:** Improve `s9 doctor` to offer one-click cleanup for stale missions instead of just detection.

**Pros:**
- No plugin or automation required
- Director maintains full control
- Simple to implement (add `--fix` flag to `s9 doctor`)

**Cons:**
- Still manual (Director must remember to run it)
- Reactive, not preventive (zombies exist until Director notices)
- Doesn't help with crash scenarios (Director may not know session crashed)
- Doesn't solve Director cognitive load problem
- No improvement over current situation (just easier cleanup)

**Rejected because:** Doesn't fundamentally solve the problem. Manual cleanup is the current workaround we're trying
to eliminate, not enhance.

### Alternative 6: Wrapper Script Instead of Plugin

**Approach:** Create a wrapper script (`s9-opencode`) that launches OpenCode and traps EXIT signals to run cleanup.

**Pros:**
- No plugin required
- Works with OpenCode as-is
- Can catch Ctrl+C and other signals

**Cons:**
- Requires Director to use wrapper instead of `opencode` command (adoption friction)
- Doesn't catch OpenCode crashes (EXIT traps don't fire on crashes)
- Doesn't handle "close window" action (TUI/desktop app)
- Fragile (easy to bypass by running `opencode` directly)
- Doesn't work for multi-session scenarios (which session closed?)

**Rejected because:** Fragile and incomplete solution. Plugin approach is more robust and integrated with OpenCode's
actual lifecycle.

### Alternative 7: Store Session ID in OpenCode Session Metadata

**Approach:** Use OpenCode SDK to store mission ID in session metadata (if supported), then plugin reads it directly.

**Pros:**
- No need to query site-nine database from plugin
- Session carries its own mission context
- Simpler plugin logic

**Cons:**
- **BLOCKED:** OpenCode SDK doesn't currently support custom session metadata
- Would require OpenCode feature addition (out of our control)
- Session metadata may not persist across crashes
- Still need database for mission status checks

**Rejected because:** Not feasible with current OpenCode API. If OpenCode adds custom metadata in future, we could
simplify, but can't depend on it now.

## Consequences

### Positive

- ✅ **Eliminates zombie missions:** Sessions closing automatically end corresponding missions
- ✅ **Zero cognitive load:** Director doesn't need to remember `/dismiss` command
- ✅ **Crash-resilient:** Works even if OpenCode crashes or network disconnects
- ✅ **Immediate cleanup:** Mission ends when session closes (no delay)
- ✅ **Audit trail:** All auto-ends logged with reason and timestamp
- ✅ **Backward compatible:** Works with all existing missions (no migration needed)
- ✅ **Manual override:** Director can still use `/dismiss` for graceful shutdown (preferred)
- ✅ **Idempotent:** Plugin checks status before ending (safe to run multiple times)
- ✅ **No operational overhead:** Plugin auto-loads, no daemon or cron needed
- ✅ **Leverages OpenCode platform:** Uses official plugin API (stable, supported)
- ✅ **No database changes:** Reuses existing detection logic (proven code path)
- ✅ **Simple deployment:** Single plugin file, no schema updates or skill modifications

### Negative

- ⚠️ **Plugin maintenance:** Plugin code must be maintained alongside site-nine
- ⚠️ **OpenCode dependency:** Relies on OpenCode plugin system stability
- ⚠️ **Auto-end less graceful than manual dismissal:** Mission file won't have full Summary/Outcomes
  - Mitigation: Director should still use `/dismiss` when possible; auto-end is safety net
- ⚠️ **Detection can fail:** If all detection methods fail, mission won't auto-end
  - Mitigation: Detection cascade has 5 fallback methods; very reliable in practice
- ⚠️ **Performance overhead:** Plugin runs detection for each ACTIVE/IDLE mission on session close
  - Mitigation: Fast detection (milliseconds), small mission count (0-5 typically), async execution
- ⚠️ **Plugin errors invisible:** If plugin fails silently, zombies still occur
  - Mitigation: Plugin logs all operations; can be monitored via OpenCode logs

### Risks & Mitigation

| Risk | Mitigation |
|------|-----------|
| **Plugin ends wrong mission (false positive)** | - Detection cascade uses 5 methods (DB recency most reliable)<br>- Check mission status before ending<br>- Log all auto-ends with session ID and mission ID<br>- UUID markers provide explicit correlation |
| **Plugin fails to end mission (false negative)** | - Detection cascade has multiple fallback methods<br>- Comprehensive error logging<br>- Fallback to `s9 doctor` detection (existing)<br>- Manual cleanup still available |
| **Detection logic fails for edge cases** | - Cascade has 5 fallback methods (proven in production)<br>- UUID marker set during `rename-tui` (explicit)<br>- Content correlation handles unusual scenarios<br>- Session recency as last resort |
| **OpenCode plugin system changes/breaks** | - Plugin uses stable public API only<br>- Version pin OpenCode in deployment<br>- Monitor OpenCode release notes<br>- Maintain fallback manual cleanup |
| **Multiple missions per session (edge case)** | - Plugin stops after first match (1:1 relationship)<br>- Detection returns most recently active session<br>- Document: One agent per session (existing best practice) |
| **Race condition: plugin runs before mission created** | - Mission created during session-start (before session can close)<br>- Session rename happens early in workflow<br>- Plugin only queries ACTIVE/IDLE missions (newly created) |
| **Performance: plugin slows OpenCode shutdown** | - Plugin runs async (non-blocking)<br>- Detection is fast (milliseconds per mission)<br>- Small mission count (0-5 typically)<br>- Timeout: Plugin aborts after 5 seconds |

## Implementation Plan

### Phase 1: CLI Command for Session Detection

**Tasks:**
1. Implement CLI command: `s9 mission detect-session --mission-id <id> --format json`
   - Wraps existing `OpenCodeSessionManager.detect_session()` method
   - Returns JSON: `{"session_id": "...", "detection_method": "...", "confidence": "..."}`
2. Enhance `OpenCodeSessionManager` to track detection method/confidence (for debugging)
3. Enhance CLI command: `s9 mission end <id>` with `--reason` and `--auto` flags
4. Enhance CLI command: `s9 mission list` with `--status` filter and `--format json` output
5. Write tests: CLI commands, JSON formatting, session detection wrapper

**Acceptance criteria:**
- `detect-session` correctly wraps existing detection logic
- Returns valid JSON with session ID (or null if not detected)
- `mission end --auto` skips prompts and minimally updates mission file
- `mission list --status ACTIVE --format json` returns parseable mission data

### Phase 2: Implement Plugin

**Tasks:**
1. Create `.opencode/plugins/site-nine-lifecycle.ts`
2. Implement `session.deleted` event handler
3. Add session-to-mission correlation logic (calls `detect-session` for each mission)
4. Add safety checks (status verification, single-mission ending)
5. Add comprehensive logging (info, debug, error levels)
6. Test plugin with manual session creation/deletion
7. Test plugin with crash scenarios (kill OpenCode process)

**Acceptance criteria:**
- Plugin loads automatically on OpenCode startup
- Plugin correctly ends missions when sessions close
- Plugin logs all operations (audit trail)
- Plugin doesn't crash OpenCode if site-nine commands fail
- Plugin stops after first mission match (no double-ending)

### Phase 3: Documentation & Rollout

**Tasks:**
1. Update ADR with implementation notes
2. Document plugin in `.opencode/docs/guides/`
3. Add troubleshooting guide for plugin issues
4. Announce to team: New auto-dismissal feature
5. Monitor for 1 week: Check plugin logs for issues

**Acceptance criteria:**
- All stakeholders understand new behavior
- Documentation covers troubleshooting common issues
- No zombie missions observed in monitoring period

### Phase 4: Monitoring & Iteration

**Tasks:**
1. Add metrics: Track auto-ends vs manual dismissals
2. Monitor plugin error rate and detection success rate
3. Gather Director feedback on behavior
4. Iterate on detection logic if issues found
5. Consider enhancements (e.g., session idle timeout)

## References

- **Related Task:** OPR-M-0129 (Investigate OpenCode session lifecycle hooks)
- **Related Epic:** EPC-H-0004 (Multi-Tool Adapter System) - related operational improvements
- **Related ADR:** ADR-006 (Entity Model Clarity - Personas, Missions, Agents)
- **Related ADR:** ADR-009 (Agent Coordination Patterns - mission scoping)
- **OpenCode Plugin Documentation:** https://opencode.ai/docs/plugins
- **OpenCode SDK Documentation:** https://opencode.ai/docs/sdk
- **Skills Reference:**
  - `session-start` skill (`.opencode/skills/session-start/SKILL.md`)
  - `session-end` skill (`.opencode/skills/session-end/SKILL.md`)
- **Current zombie detection:** `s9 doctor` command

## Notes

### Design Philosophy

**Principle: Platform-Integrated > Workarounds**

We chose to integrate with OpenCode's official plugin system rather than build external workarounds (daemons, wrappers,
polling). This:
- Leverages platform capabilities (event-driven, lifecycle hooks)
- Reduces operational complexity (no separate processes)
- Stays synchronized with platform evolution (plugin API is supported)
- Provides better UX (immediate, invisible, reliable)

**Principle: Safety Nets, Not Replacements**

Auto-dismissal is a **safety net**, not a replacement for proper workflow:
- **Preferred:** Director uses `/dismiss` → Agent runs session-end skill → Graceful shutdown
- **Fallback:** Session closes unexpectedly → Plugin auto-ends mission → Prevents zombie

We preserve the manual workflow as the "happy path" and use automation to prevent failure modes.

**Principle: Fail-Safe Defaults**

Plugin is designed to fail safely:
- Errors don't crash OpenCode (caught and logged)
- Detection fails? Skip silently (fallback to manual cleanup)
- Mission already ended? No-op (idempotent)
- Wrong mission? Prevented by multi-method detection cascade

**Principle: Reuse > Reinvent**

We leverage existing, proven session detection logic rather than building new infrastructure:
- `OpenCodeSessionManager.detect_session()` already handles edge cases
- No new database schema or data duplication
- Single source of truth for session correlation
- Minimal new code = fewer bugs

### Future Enhancements

**Possible improvements after observing production behavior:**

1. **Enhanced mission file cleanup:** Auto-end could attempt basic Summary/Outcomes based on task completion
2. **Session idle timeout:** Extend plugin to handle `session.idle` for long-inactive sessions
3. **Multi-mission sessions:** Support multiple agents in one session (advanced use case)
4. **Metrics dashboard:** Track auto-end vs manual dismissal rates over time
5. **OpenCode metadata integration:** If OpenCode adds custom session metadata API, store mission ID there for
   bidirectional lookup

**Potential OpenCode feature requests:**

- Custom session metadata fields (avoid database lookup)
- Session lifecycle hooks with richer context (e.g., exit reason)
- Plugin configuration UI (enable/disable plugins per project)

### Open Questions

**For implementation:**
1. Should we add a grace period before auto-ending (e.g., 30 seconds after session.deleted)?
   - Pro: Allows for race conditions where session restarts quickly
   - Con: Delays cleanup, complicates logic
   - **Decision:** No grace period initially; can add if needed

2. Should auto-end attempt to update mission file Summary/Outcomes?
   - Pro: More complete mission record
   - Con: Complex heuristics; may generate poor summaries
   - **Decision:** Minimal updates only; manual dismissal still preferred

3. Should we notify Director when auto-end occurs?
   - Pro: Awareness of unexpected session closures
   - Con: Notification fatigue if sessions close frequently
   - **Decision:** Log only (passive); Director can review logs if concerned

4. What happens if mission has unclaimed tasks?
   - Current: Tasks remain claimed by mission
   - Option 1: Auto-unclaim tasks when mission ends
   - Option 2: Keep tasks claimed (preserve work state)
   - **Decision:** Keep tasks claimed (existing behavior); separate task cleanup logic

5. Should plugin query all missions or only recent ones?
   - Current approach: Query ACTIVE/IDLE missions only
   - Alternative: Query missions updated in last N hours (more selective)
   - **Decision:** ACTIVE/IDLE filter is sufficient; typically 0-5 missions

**For rollout:**
1. Should we enable plugin by default or require opt-in?
   - **Decision:** Enable by default (plugin file present); can disable by removing file

---

**Status:** REJECTED  
**Rejection Reason:** During review, Director proposed a more comprehensive architectural vision that treats site-nine as
a tightly integrated OpenCode platform rather than a loosely coupled CLI tool. The detection-based approach in this ADR
is elegant for retrofitting existing architecture, but doesn't fully leverage the potential of tight OpenCode
integration. See ADR-011 for session-first architecture, automatic lifecycle management, desk mode orchestration, and
enhanced plugin capabilities.

**Next Steps:**
1. Create ADR-011: Site-nine as OpenCode Integration Platform
2. Explore session-first design (session ID as primary key)
3. Design desk mode for multi-agent orchestration
4. Define plugin capabilities for rich automation
5. Plan migration path from current architecture
