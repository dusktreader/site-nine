# ADR-010: OpenCode Session Lifecycle Integration for Auto-Dismissal

**Status:** REJECTED  
**Date:** 2026-02-15  
**Deciders:** Tucker (Director), Angra-mainyu (Architect)  
**Related Tasks:** OPR-M-0129  
**Superseded By:** ADR-011 (Site-nine as OpenCode Integration Platform)  

## Context

**NOTE: This ADR was rejected in favor of a more comprehensive architectural vision. See ADR-011: Site-nine as
OpenCode Integration Platform for the revised approach that embraces tight integration and session-first design.**

### The Zombie Possession Problem

Site-nine currently suffers from "zombie possessions" - possession records that remain in ACTIVE or IDLE status indefinitely
after their OpenCode sessions have ended. This occurs when:

1. **Director closes OpenCode window** without using `/dismiss` command
2. **OpenCode crashes or exits unexpectedly** during an agent session
3. **Network disconnection** causes session to terminate
4. **Agent forgets to run possession-end skill** before OpenCode closes

**Current workflow requires:**
- Director must explicitly use `/dismiss` command
- Agent must execute possession-end skill when dismissed
- Agent must run `s9 possession end <possession-id>` to update database
- All of these steps must happen BEFORE the OpenCode session closes

**If any step is skipped:**
- Possession remains ACTIVE in database indefinitely
- `s9 inquisitor` flags possessions without heartbeat for >8h as "stale"
- Dashboard shows inflated active possession counts
- Tasks remain claimed by ended possessions
- System accumulates operational debt

**Current workarounds:**
- Manual cleanup: Director runs `s9 possession end <id>` for each zombie
- `s9 inquisitor` detection: Flags stale possessions but doesn't auto-fix
- Documentation emphasis: Skills repeatedly warn agents not to end prematurely

**Why this is insufficient:**
- Director must remember to dismiss agents (extra cognitive load)
- Agents have no control over unexpected session termination
- No automatic recovery from crashes or disconnections
- Cleanup is reactive rather than preventive

### Root Cause Analysis

The fundamental issue is **coupling between OpenCode session lifecycle and site-nine possession lifecycle**:

```
Current (manual):
OpenCode Session ❌ Site-nine Possession
     ↓                      ↓
  Closes              Still ACTIVE
                           ↓
                    Manual cleanup required

Desired (automatic):
OpenCode Session ✅ Site-nine Possession
     ↓                      ↓
  Closes              Auto-ends
                           ↓
                    Clean state
```

The possession lifecycle should be **automatically synchronized** with the OpenCode session lifecycle, not dependent on
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
        await $`s9 possession end <possession-id>`
      }
    },
  }
}
```

### Possession Identification Challenge

The core technical challenge is **mapping OpenCode sessions to site-nine possessions**:

**What OpenCode plugins know:**
- Session ID (e.g., `aFZ8rQJo`) from `session.deleted` event
- Session metadata (title, directory, timestamps)
- Project directory path

**What site-nine possessions track:**
- Possession ID (e.g., `113`)
- Daemon name, role, codename
- Possession file path
- Start/end times
- **No direct reference to OpenCode session ID**

**Existing session detection solution:**

Site-nine **already solves this problem** in the `s9 possession rename-tui` command. The
`OpenCodeSessionManager.detect_session()` method (see `src/site_nine/opencode/manager.py:74-169`) uses a cascade of
detection methods to correlate possessions with OpenCode sessions:

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
2. Plugin queries for ACTIVE/IDLE possessions in the project
3. For each possession, run existing `detect_session()` logic to find its OpenCode session
4. Compare detected session ID with event session ID
5. If match found, auto-end that possession

**Why this is architecturally superior:**

- **Reuses proven code:** `detect_session()` already handles edge cases (multiple sessions, renamed sessions, etc.)
- **No schema migration:** Works with existing database structure
- **Backward compatible:** Handles legacy possessions without modification
- **Maintainable:** Single source of truth for session detection logic
- **Robust:** Falls back through multiple detection methods if primary fails

## Decision

We will implement an **OpenCode lifecycle plugin** that uses existing session detection logic to automatically end
missions when their sessions close. This approach requires **no database schema changes** and leverages proven code
paths already in production.

### Core Approach: Reuse Existing Session Detection

Instead of adding new database fields, the plugin will:

1. Receive `session.deleted` event from OpenCode (with session ID)
2. Query site-nine for ACTIVE/IDLE possessions in the current project
3. For each possession, invoke existing `detect_session()` logic to find its OpenCode session
4. Compare detected session ID with event session ID
5. Auto-end possession if IDs match

**Architectural advantages:**
- **Zero schema migration:** Works with existing database structure
- **Proven detection logic:** Reuses `OpenCodeSessionManager.detect_session()` from `rename-tui` command
- **Graceful fallback:** Detection cascade handles edge cases (UUID markers, content correlation, etc.)
- **Single source of truth:** Session detection logic maintained in one place
- **Backward compatible:** Handles all existing possessions without modification

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
        // Find active possessions in the current project
        const possessionsResult = await $`s9 possession list --status ACTIVE --status IDLE --format json`
        const possessions = JSON.parse(possessionsResult.stdout)

        if (!possessions || possessions.length === 0) {
          console.info(`[site-nine] No active possessions found for session ${eventSessionId}`)
          return
        }

        // For each possession, detect its OpenCode session and compare
        for (const possession of possessions) {
          try {
            // Use existing detection logic to find possession's session
            const detectResult = await $`s9 possession detect-session --possession-id ${possession.id} --format json`
            const detection = JSON.parse(detectResult.stdout)

            if (detection.session_id === eventSessionId) {
              // Found the possession corresponding to this session
              console.info(`[site-nine] Auto-ending possession ${possession.id} (${possession.daemon_name}) for session ${eventSessionId}`)
              await $`s9 possession end ${possession.id} --reason "session_closed" --auto`
              console.info(`[site-nine] Successfully ended possession ${possession.id}`)
              
              // Only end one possession per session
              return
            }
          } catch (detectError) {
            // Detection failed for this possession - skip it
            console.debug(`[site-nine] Could not detect session for possession ${possession.id}:`, detectError)
            continue
          }
        }

        console.info(`[site-nine] No possession matched session ${eventSessionId}`)
      } catch (error) {
        console.error(`[site-nine] Failed to auto-end possession for session ${eventSessionId}:`, error)
        // Don't throw - plugin errors shouldn't crash OpenCode
      }
    },
  }
}
```

**Key design elements:**

1. **Leverages existing detection:** Calls `s9 possession detect-session` command (wraps `OpenCodeSessionManager.detect_session()`)
2. **Minimal query surface:** Only queries for ACTIVE/IDLE possessions (fast)
3. **One possession per session:** Stops after first match (enforces 1:1 relationship)
4. **Graceful degradation:** If detection fails for a possession, continues to next
5. **Comprehensive logging:** Info/debug/error levels for troubleshooting
6. **Never crashes OpenCode:** All errors caught and logged

**CLI Support:**

Add new commands to support plugin operations:

```bash
# Detect which OpenCode session corresponds to a possession (wraps OpenCodeSessionManager.detect_session())
s9 possession detect-session --possession-id <possession-id> --format json
# Returns: {"session_id": "aFZ8rQJo", "detection_method": "db_recency", "confidence": "high"}

# List possessions with status filter
s9 possession list --status ACTIVE --status IDLE --format json

# End possession with automation support
s9 possession end <possession-id> --reason <reason> --auto
```

**New command: `s9 possession detect-session`**

Wraps existing `OpenCodeSessionManager.detect_session()` logic for CLI/plugin use:

```python
# In src/site_nine/cli/possession.py
@possession.command()
@click.option("--possession-id", required=True, type=int)
@click.option("--format", type=click.Choice(["json", "text"]), default="text")
def detect_session(possession_id: int, format: str):
    """Detect which OpenCode session corresponds to a possession."""
    from site_nine.opencode.manager import OpenCodeSessionManager
    
    possession = db.get_possession(possession_id)
    if not possession:
        raise click.ClickException(f"Possession {possession_id} not found")
    
    manager = OpenCodeSessionManager()
    session_id = manager.detect_session(possession.possession_file_path)
    
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
- Minimal possession file updates (no manual Summary/Outcomes editing)
- Records auto-end reason in possession record
- Suitable for plugin/automation use

### Session-to-Possession Correlation Logic

**Flow:**

1. Plugin receives `session.deleted` event with session ID `S`
2. Query: Get all possessions with status ACTIVE or IDLE
3. For each possession `P`:
   - Call `detect_session(P)` → returns session ID `S'`
   - If `S == S'`: This possession corresponds to the deleted session → Auto-end
   - If `S != S'`: Continue to next possession
4. If no match found: Log and exit (non-agent session or already ended)

**Detection cascade (existing logic in `OpenCodeSessionManager`):**

```python
def detect_session(possession_file_path: Path) -> str | None:
    """Detect OpenCode session ID for a possession using cascade of methods."""
    
    # Method 1: Query OpenCode SQLite DB for recent session (most reliable)
    session_id = self._detect_via_db_recency(possession_file_path)
    if session_id:
        return session_id
    
    # Method 2: Search for UUID marker in session data
    session_id = self._detect_via_db_uuid_marker(possession_file_path)
    if session_id:
        return session_id
    
    # Method 3: Correlate git changes with session diffs
    session_id = self._detect_via_content_correlation(possession_file_path)
    if session_id:
        return session_id
    
    # Method 4: Find most recent session diff file
    session_id = self._detect_via_diff_recency(possession_file_path)
    if session_id:
        return session_id
    
    # Method 5: Find most recent session file (fallback)
    session_id = self._detect_via_session_recency(possession_file_path)
    return session_id
```

**Why this is robust:**

- **DB recency:** Works for 95% of cases (normal session lifecycle)
- **UUID marker:** Catches renamed sessions (set during `rename-tui`)
- **Content correlation:** Handles edge cases where DB is stale
- **Diff recency:** Works even if session metadata is corrupted
- **Session recency:** Last-resort fallback

**Performance considerations:**

- Query returns 0-5 possessions typically (most users have ≤1 active possession)
- Detection methods are fast (DB query is milliseconds)
- Plugin timeout: 5 seconds max (prevents hanging OpenCode shutdown)
- Async execution: Non-blocking

### Integration Points

**Modified workflows:**

1. **possession-start skill:**
   - No changes required
   - Existing workflow (possession registration, session rename) provides sufficient context for detection
   - UUID marker set during `rename-tui` enables detection cascade

2. **possession-end skill:**
   - No changes needed
   - Manual dismissal still runs full workflow
   - Sets status to ENDED (plugin skips already-ended possessions)

3. **Plugin activation:**
   - Automatically loaded from `.opencode/plugins/`
   - Only activates on `session.deleted` events
   - Idempotent: Checks possession status before ending
   - Uses existing detection logic (no new code paths)

**Deployment:**
- Plugin file added to project `.opencode/plugins/`
- Auto-loads on OpenCode startup
- No user configuration required
- No database migrations required

## Alternatives Considered

### Alternative 1: Periodic Cleanup Daemon

**Approach:** Run a background process that periodically checks for stale possessions (no heartbeat for >8h) and
auto-ends them.

**Pros:**
- Simple to implement (cron job or systemd timer)
- No OpenCode integration required
- Works for all possessions regardless of OpenCode usage

**Cons:**
- Reactive, not preventive (8h delay before cleanup)
- Requires separate daemon process (operational overhead)
- Doesn't solve immediate problem (session closes, possession stays active for hours)
- Heartbeat-based detection can have false positives (agent taking long break)
- No graceful handling of crashes (possession file may be incomplete)

**Rejected because:** Doesn't address root cause (session-possession coupling). Adding a daemon for cleanup is treating
the symptom, not the disease. We want immediate synchronization, not delayed cleanup.

### Alternative 2: Store Session ID in Database

**Approach:** Add `opencode_session_id` column to possessions table, store during possession-start, query directly in plugin.

**Pros:**
- Fast O(1) lookup (indexed column)
- No detection cascade needed
- Direct 1:1 mapping

**Cons:**
- Requires database migration (ALTER TABLE, CREATE INDEX)
- Requires modifying possession-start skill to capture session ID
- Adds operational complexity (new CLI command, skill updates)
- Doesn't work for existing possessions (needs backfill or fallback)
- Duplicates data (session ID already inferable from detection logic)
- More moving parts = more potential failure modes

**Rejected because:** Existing detection logic already solves this problem reliably. Adding database fields would
increase complexity without significant performance benefit (detection is fast, possessions list is small). We prefer
reusing proven code over adding new schema. The YAGNI principle applies: detection works well enough that we don't need
explicit storage.

### Alternative 3: Parse Session ID from Possession Files

**Approach:** Store session ID only in possession markdown file (not database), parse file when plugin needs to find
possession.

**Pros:**
- No database migration required
- Session ID visible in human-readable possession file
- Simple implementation

**Cons:**
- File parsing is slow and error-prone (YAML frontmatter or regex)
- No indexing (O(n) scan of all possession files on every session.deleted)
- Race conditions (file may be locked during write)
- Doesn't work if possession file is corrupted or missing
- Plugin execution happens outside agent context (may not have file access)
- Still requires session ID capture during possession-start

### Alternative 4: Heartbeat Timeout with Automatic End

**Approach:** Enhance existing heartbeat system to automatically end possessions after N minutes without heartbeat.

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

**Approach:** Improve `s9 inquisitor` to offer one-click cleanup for stale possessions instead of just detection.

**Pros:**
- No plugin or automation required
- Director maintains full control
- Simple to implement (add `--fix` flag to `s9 inquisitor`)

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

**Approach:** Use OpenCode SDK to store possession ID in session metadata (if supported), then plugin reads it directly.

**Pros:**
- No need to query site-nine database from plugin
- Session carries its own possession context
- Simpler plugin logic

**Cons:**
- **BLOCKED:** OpenCode SDK doesn't currently support custom session metadata
- Would require OpenCode feature addition (out of our control)
- Session metadata may not persist across crashes
- Still need database for possession status checks

**Rejected because:** Not feasible with current OpenCode API. If OpenCode adds custom metadata in future, we could
simplify, but can't depend on it now.

## Consequences

### Positive

- ✅ **Eliminates zombie possessions:** Sessions closing automatically end corresponding possessions
- ✅ **Zero cognitive load:** Director doesn't need to remember `/dismiss` command
- ✅ **Crash-resilient:** Works even if OpenCode crashes or network disconnects
- ✅ **Immediate cleanup:** Possession ends when session closes (no delay)
- ✅ **Audit trail:** All auto-ends logged with reason and timestamp
- ✅ **Backward compatible:** Works with all existing possessions (no migration needed)
- ✅ **Manual override:** Director can still use `/dismiss` for graceful shutdown (preferred)
- ✅ **Idempotent:** Plugin checks status before ending (safe to run multiple times)
- ✅ **No operational overhead:** Plugin auto-loads, no daemon or cron needed
- ✅ **Leverages OpenCode platform:** Uses official plugin API (stable, supported)
- ✅ **No database changes:** Reuses existing detection logic (proven code path)
- ✅ **Simple deployment:** Single plugin file, no schema updates or skill modifications

### Negative

- ⚠️ **Plugin maintenance:** Plugin code must be maintained alongside site-nine
- ⚠️ **OpenCode dependency:** Relies on OpenCode plugin system stability
- ⚠️ **Auto-end less graceful than manual dismissal:** Possession file won't have full Summary/Outcomes
  - Mitigation: Director should still use `/dismiss` when possible; auto-end is safety net
- ⚠️ **Detection can fail:** If all detection methods fail, possession won't auto-end
  - Mitigation: Detection cascade has 5 fallback methods; very reliable in practice
- ⚠️ **Performance overhead:** Plugin runs detection for each ACTIVE/IDLE possession on session close
  - Mitigation: Fast detection (milliseconds), small possession count (0-5 typically), async execution
- ⚠️ **Plugin errors invisible:** If plugin fails silently, zombies still occur
  - Mitigation: Plugin logs all operations; can be monitored via OpenCode logs

### Risks & Mitigation

| Risk | Mitigation |
|------|-----------|
| **Plugin ends wrong possession (false positive)** | - Detection cascade uses 5 methods (DB recency most reliable)<br>- Check possession status before ending<br>- Log all auto-ends with session ID and possession ID<br>- UUID markers provide explicit correlation |
| **Plugin fails to end possession (false negative)** | - Detection cascade has multiple fallback methods<br>- Comprehensive error logging<br>- Fallback to `s9 inquisitor` detection (existing)<br>- Manual cleanup still available |
| **Detection logic fails for edge cases** | - Cascade has 5 fallback methods (proven in production)<br>- UUID marker set during `rename-tui` (explicit)<br>- Content correlation handles unusual scenarios<br>- Session recency as last resort |
| **OpenCode plugin system changes/breaks** | - Plugin uses stable public API only<br>- Version pin OpenCode in deployment<br>- Monitor OpenCode release notes<br>- Maintain fallback manual cleanup |
| **Multiple possessions per session (edge case)** | - Plugin stops after first match (1:1 relationship)<br>- Detection returns most recently active session<br>- Document: One agent per session (existing best practice) |
| **Race condition: plugin runs before possession created** | - Possession created during possession-start (before session can close)<br>- Session rename happens early in workflow<br>- Plugin only queries ACTIVE/IDLE possessions (newly created) |
| **Performance: plugin slows OpenCode shutdown** | - Plugin runs async (non-blocking)<br>- Detection is fast (milliseconds per possession)<br>- Small possession count (0-5 typically)<br>- Timeout: Plugin aborts after 5 seconds |

## Implementation Plan

### Phase 1: CLI Command for Session Detection

**Tasks:**
1. Implement CLI command: `s9 possession detect-session --possession-id <id> --format json`
   - Wraps existing `OpenCodeSessionManager.detect_session()` method
   - Returns JSON: `{"session_id": "...", "detection_method": "...", "confidence": "..."}`
2. Enhance `OpenCodeSessionManager` to track detection method/confidence (for debugging)
3. Enhance CLI command: `s9 possession end <id>` with `--reason` and `--auto` flags
4. Enhance CLI command: `s9 possession list` with `--status` filter and `--format json` output
5. Write tests: CLI commands, JSON formatting, session detection wrapper

**Acceptance criteria:**
- `detect-session` correctly wraps existing detection logic
- Returns valid JSON with session ID (or null if not detected)
- `possession end --auto` skips prompts and minimally updates possession file
- `possession list --status ACTIVE --format json` returns parseable possession data

### Phase 2: Implement Plugin

**Tasks:**
1. Create `.opencode/plugins/site-nine-lifecycle.ts`
2. Implement `session.deleted` event handler
3. Add session-to-possession correlation logic (calls `detect-session` for each possession)
4. Add safety checks (status verification, single-possession ending)
5. Add comprehensive logging (info, debug, error levels)
6. Test plugin with manual session creation/deletion
7. Test plugin with crash scenarios (kill OpenCode process)

**Acceptance criteria:**
- Plugin loads automatically on OpenCode startup
- Plugin correctly ends possessions when sessions close
- Plugin logs all operations (audit trail)
- Plugin doesn't crash OpenCode if site-nine commands fail
- Plugin stops after first possession match (no double-ending)

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
- No zombie possessions observed in monitoring period

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
- **Related ADR:** ADR-006 (Entity Model Clarity - Daemons, Possessions, Agents)
- **Related ADR:** ADR-009 (Agent Coordination Patterns - possession scoping)
- **OpenCode Plugin Documentation:** https://opencode.ai/docs/plugins
- **OpenCode SDK Documentation:** https://opencode.ai/docs/sdk
- **Skills Reference:**
  - `possession-start` skill (`.opencode/skills/possession-start/SKILL.md`)
  - `possession-end` skill (`.opencode/skills/possession-end/SKILL.md`)
- **Current zombie detection:** `s9 inquisitor` command

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
- **Preferred:** Director uses `/dismiss` → Agent runs possession-end skill → Graceful shutdown
- **Fallback:** Session closes unexpectedly → Plugin auto-ends possession → Prevents zombie

We preserve the manual workflow as the "happy path" and use automation to prevent failure modes.

**Principle: Fail-Safe Defaults**

Plugin is designed to fail safely:
- Errors don't crash OpenCode (caught and logged)
- Detection fails? Skip silently (fallback to manual cleanup)
- Possession already ended? No-op (idempotent)
- Wrong possession? Prevented by multi-method detection cascade

**Principle: Reuse > Reinvent**

We leverage existing, proven session detection logic rather than building new infrastructure:
- `OpenCodeSessionManager.detect_session()` already handles edge cases
- No new database schema or data duplication
- Single source of truth for session correlation
- Minimal new code = fewer bugs

### Future Enhancements

**Possible improvements after observing production behavior:**

1. **Enhanced possession file cleanup:** Auto-end could attempt basic Summary/Outcomes based on task completion
2. **Session idle timeout:** Extend plugin to handle `session.idle` for long-inactive sessions
3. **Multi-possession sessions:** Support multiple agents in one session (advanced use case)
4. **Metrics dashboard:** Track auto-end vs manual dismissal rates over time
5. **OpenCode metadata integration:** If OpenCode adds custom session metadata API, store possession ID there for
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

2. Should auto-end attempt to update possession file Summary/Outcomes?
   - Pro: More complete possession record
   - Con: Complex heuristics; may generate poor summaries
   - **Decision:** Minimal updates only; manual dismissal still preferred

3. Should we notify Director when auto-end occurs?
   - Pro: Awareness of unexpected session closures
   - Con: Notification fatigue if sessions close frequently
   - **Decision:** Log only (passive); Director can review logs if concerned

4. What happens if possession has unclaimed tasks?
   - Current: Tasks remain claimed by possession
   - Option 1: Auto-unclaim tasks when possession ends
   - Option 2: Keep tasks claimed (preserve work state)
   - **Decision:** Keep tasks claimed (existing behavior); separate task cleanup logic

5. Should plugin query all possessions or only recent ones?
   - Current approach: Query ACTIVE/IDLE possessions only
   - Alternative: Query possessions updated in last N hours (more selective)
   - **Decision:** ACTIVE/IDLE filter is sufficient; typically 0-5 possessions

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
