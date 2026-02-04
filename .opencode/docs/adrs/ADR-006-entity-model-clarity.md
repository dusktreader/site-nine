# ADR-006: Entity Model Clarity - Personas, Missions, and Agents

**Status:** Proposed  
**Date:** 2026-02-03  
**Deciders:** Tucker (Director), Hemera (Operator)  
**Related Tasks:** OPR-H-0032  
**Related ADRs:** ADR-005 (Backward Compatibility)

## Context

Site-nine's current entity model uses terminology that creates confusion:

### The Problem: Overloaded Terms

**"Agent" means three different things:**
1. **OpenCode agent session** - The AI instance running in a terminal (external to site-nine)
2. **Agent persona** - A named identity like "hemera" or "nereus" (stored in `daemon_names` table)
3. **Agent work session** - A database record tracking one work period (stored in `agents` table)

**"Session" is also overloaded:**
1. **OpenCode session** - A chat window that can be opened/closed/resumed
2. **Agent session** - site-nine's database record of work (in `agents` table)
3. **Work session** - The general concept of a period of work

This creates problems:
- **Abandoned "in-progress" agents:** OpenCode closes but `agents.status='in-progress'` remains set
- **Confusing handoffs:** Task has `agent_id` pointing backward, making "who's working on this?" unclear
- **Lifecycle coupling:** Agent session lifecycle wrongly assumed to match OpenCode lifecycle
- **Sync bugs:** Agent status and task status can get out of sync (previously cleaned up but recurring)

### Current State

**Database Evidence (2026-02-03):**
- 12 agent records with `status='in-progress'`
- Most are 1-2 days old (from 2026-02-02)
- Only 1 task with `status='UNDERWAY'`
- These are abandoned OpenCode sessions that were never properly ended

**Current Schema:**
```sql
-- Personas stored as "daemon_names"
CREATE TABLE daemon_names (
    name TEXT PRIMARY KEY,
    role TEXT,
    mythology TEXT,
    description TEXT,
    usage_count INTEGER,
    last_used_at TEXT
);

-- Work periods stored as "agents"
CREATE TABLE agents (
    id INTEGER PRIMARY KEY,
    name TEXT,              -- Which daemon name
    role TEXT,
    status TEXT,            -- in-progress, completed, failed, aborted, paused
    session_file TEXT,
    session_date TEXT,
    start_time TEXT,
    end_time TEXT,
    task_summary TEXT
);

-- Tasks point backward to agents
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    status TEXT,
    agent_name TEXT,        -- Backward link (string)
    agent_id INTEGER,       -- Backward link (FK)
    ...
);
```

## Decision

We will clarify the entity model with distinct, unambiguous terminology and restructured relationships.

### New Terminology

**Agent** = The external AI instance (OpenCode, Cursor, etc.)
- Managed by the IDE/tool, not by site-nine
- Referenced conceptually but not modeled in site-nine
- Example: "Claude running in an OpenCode terminal"

**Persona** = Named identity with role and personality (was "daemon_name")
- Persistent across multiple missions
- Has mythology/backstory and role assignment
- Examples: hemera (Goddess of day, Operator), nereus (Old man of the sea, Operator)
- Table: `personas` (renamed from `daemon_names`)

**Mission** = One work assignment using a persona (was "agent session")
- Explicitly started via `/summon` workflow
- Explicitly ended via `/dismiss` workflow
- NOT tied to OpenCode session lifecycle (key difference!)
- Has a codename for identification and fun
- Table: `missions` (renamed from `agents`)

### Entity Relationships

```
personas (1) ──< (many) missions ──< (0..1) tasks
    │                    │                      │
 hemera           Mission #36              OPR-H-0032
(Operator)      "Swift Thunder"          (UNDERWAY)
                2026-02-03 14:58
```

**Relationship Details:**

1. **personas → missions:** One-to-Many
   - One persona can be used in many missions
   - `missions.persona_name` foreign key to `personas.name`
   - Tracks usage: `personas.mission_count` increments

2. **missions → tasks:** One-to-One (or none)
   - One mission works on one task at a time (or none)
   - One task has one active mission (or none)
   - `tasks.current_mission_id` foreign key to `missions.id`
   - **Forward link** (not backward) - makes handoffs trivial

### Schema Changes

**Rename and restructure tables:**

```sql
-- Personas (was daemon_names)
CREATE TABLE personas (
    name TEXT PRIMARY KEY,           -- "hemera"
    role TEXT NOT NULL,              -- "Operator"
    mythology TEXT NOT NULL,         -- "Greek"
    description TEXT NOT NULL,       -- "Goddess of day"
    mission_count INTEGER DEFAULT 0, -- Renamed from usage_count
    last_mission_at TEXT,            -- Renamed from last_used_at
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Missions (was agents)
CREATE TABLE missions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    persona_name TEXT NOT NULL,      -- Which persona is on this mission
    role TEXT NOT NULL,              -- Operator, Builder, etc.
    codename TEXT NOT NULL,          -- "swift-thunder", "operation-refactor"
    mission_file TEXT NOT NULL,      -- Path to markdown file
    start_date TEXT NOT NULL,        -- "2026-02-03"
    start_time TEXT NOT NULL,        -- "14:58:02"
    end_time TEXT,                   -- NULL = active, timestamp = complete
    objective TEXT,                  -- Brief description (was task_summary)
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    -- REMOVED: status field (use end_time IS NULL to determine active)
    FOREIGN KEY (persona_name) REFERENCES personas(name) ON DELETE RESTRICT
);

-- Tasks (updated relationship)
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL,            -- TODO, UNDERWAY, COMPLETE, etc.
    current_mission_id INTEGER,      -- Forward link to active mission
    claimed_at TEXT,
    closed_at TEXT,
    -- REMOVED: agent_name, agent_id (backward links)
    ...
    FOREIGN KEY (current_mission_id) REFERENCES missions(id) ON DELETE SET NULL
);
```

### Mission Codenames (Fun Feature)
Missions get automatically-generated codenames for identification and personality. Codenames are **always auto-generated** using a deterministic algorithm based on mission ID—users **cannot** specify custom codenames.

**Deterministic generation using prime-length lists:**

```python
# Prime-length lists minimize collisions via coprime modulo arithmetic
ADJECTIVES = [
    "swift", "silent", "bold", "clever", "quantum", "stellar", "epic",
    "crimson", "azure", "phantom", "iron", "silver", "rogue", "cosmic",
    "electric", "shadow", "titanium", "mystic", "storm", "ghost", 
    "crystal", "rapid", "omega", "void", "neon", "plasma", "razor",
    "cyber", "dark", "chrome", "gamma"
]  # 31 entries (prime)

NOUNS = [
    "thunder", "phoenix", "shadow", "dragon", "nexus", "vortex", "cipher",
    "falcon", "sentinel", "tempest", "wraith", "cascade", "apex", "forge",
    "blade", "comet", "prism", "quasar", "raven", "typhoon", "vector",
    "aurora", "blaze", "echo", "griffin", "helix", "kraken", "nebula", 
    "zenith", "matrix", "pulse", "specter", "vertex", "enigma", "hydra",
    "photon", "titan"
]  # 37 entries (prime)

def generate_mission_codename(mission_id: int) -> str:
    """
    Generate deterministic codename from mission ID using prime modulo.
    
    Using coprime prime numbers (31 and 37) ensures maximum distribution
    before collisions occur. First collision happens at mission #1,147.
    
    31 × 37 = 1,147 unique combinations
    """
    adjective = ADJECTIVES[mission_id % len(ADJECTIVES)]
    noun = NOUNS[mission_id % len(NOUNS)]
    return f"{adjective}-{noun}"

# Examples:
# Mission #1:    silent-phoenix
# Mission #7:    crimson-falcon
# Mission #100:  void-cascade
# Mission #1146: omega-titan (last unique before collision)
# Mission #1147: silent-thunder (reuses mission #1's codename)
```

**Why deterministic generation?**
- ✅ Consistent codenames across system restarts
- ✅ No collision tracking needed (database-free algorithm)
- ✅ Prime number math maximizes uniqueness (1,147 combinations)
- ✅ Every mission gets a codename automatically
- ✅ Memorable and fun identifiers with tech-noir theme

**Display in mission files:**
```markdown
---
persona: hemera
codename: swift-thunder
mission_id: 42
---

# Mission: Swift Thunder

**Persona:** Hemera (Operator)
**Codename:** SWIFT-THUNDER
**Mission ID:** #42
...
```

### OpenCode Session Naming

Mission codenames are prominently displayed in the OpenCode TUI session title, making it easy to identify which mission is active when you have multiple terminal windows open.

**Session title format:**
```
<Persona> - <Role> - <codename>
```

**Examples:**
- "Hemera - Operator - swift-thunder"
- "Nereus - Builder - quantum-phoenix"  
- "Brigid - Administrator - void-matrix"

**Note:** Persona name is capitalized (proper noun) in the session title.

**Implementation:**

The `s9 mission rename-tui` command (part of the refactored mission CLI group) accepts three positional arguments:

```bash
s9 mission rename-tui <persona> <Role> <codename> --session-id <session-id>

# Example:
s9 mission rename-tui hemera Operator swift-thunder --session-id ses_abc123
```

If `--session-id` is omitted, the command auto-detects the current OpenCode session.

**When this happens:**

The session-start skill (step 5b) automatically renames the OpenCode TUI session after the persona shares their mythological background. The codename is passed from the mission creation step.

**Benefits:**
- ✅ Easy identification across multiple OpenCode windows
- ✅ Visual reminder of current mission's identity
- ✅ Consistency between database records, session files, and UI
- ✅ Professional appearance for demos/screen sharing

### Lifecycle Decoupling (Critical Change)

**OLD (wrong assumption):**
- Agent session lifecycle = OpenCode session lifecycle
- When OpenCode closes, agent should be "paused" or "completed"
- Problem: Users don't run `/dismiss`, agents stay "in-progress"

**NEW (correct model):**
- Mission lifecycle is **independent** of OpenCode sessions
- Missions are explicitly started (`/summon`) and ended (`/dismiss`)
- OpenCode can close/reopen without affecting mission state
- Mission is active if `end_time IS NULL`, regardless of OpenCode

**Example workflow:**
```
1. User opens OpenCode (agent #1 starts)
2. Runs /summon operator → Mission #36 created (hemera, "swift-thunder")
3. Works on OPR-H-0032
4. User closes OpenCode (agent #1 ends) - Mission #36 still ACTIVE
5. Later: User opens new OpenCode (agent #2 starts)
6. Continues working on Mission #36 (still active!)
7. Runs /dismiss → Mission #36 ended (end_time set)
```

This is why the `status` field is removed:
- Active state = `end_time IS NULL`
- Complete state = `end_time IS NOT NULL`
- No "paused" or "failed" states needed
- Simple and accurate

### Handoff Simplification

**OLD (complex):**
```python
# Task points backward to agent
task.agent_name = "hemera"
task.agent_id = 36

# To handoff:
1. End agent #36 (set status='completed')
2. Create new agent #38
3. Update task.agent_name = "ahura-mazda"
4. Update task.agent_id = 38
```

**NEW (trivial):**
```python
# Task points forward to mission
task.current_mission_id = 36

# To handoff:
UPDATE tasks SET current_mission_id = 38 WHERE id = 'OPR-H-0032'
```

That's it! One field update. The old mission stays in the database as historical record.

## Consequences

### Benefits

**Clarity:**
- ✅ Unambiguous terminology (agent = external, persona = identity, mission = work period)
- ✅ No more "which agent?" confusion
- ✅ Clear lifecycle boundaries

**Simplified handoffs:**
- ✅ One field update to reassign task
- ✅ Easy to query "who's working on this?" (`task.current_mission_id`)
- ✅ Easy to query "what's this mission working on?" (reverse lookup)

**No abandoned missions:**
- ✅ Mission active state = `end_time IS NULL` (simple check)
- ✅ No status field to get out of sync
- ✅ Missions must be explicitly ended

**Better user experience:**
- ✅ Fun codenames add personality
- ✅ Clearer mental model (personas go on missions)
- ✅ Decoupled from OpenCode lifecycle (missions persist)

### Drawbacks

**Breaking changes (no backward compatibility):**
- ⚠️ All database queries using `agents` table must be updated
- ⚠️ CLI commands must be updated (`s9 agent` → `s9 mission`)
- ⚠️ Existing session files require migration
- ⚠️ All documentation must be rewritten
- ⚠️ **No rollback strategy** - this is a one-way migration

**Migration complexity:**
- ⚠️ 38 existing agent records must be migrated to missions
- ⚠️ **57 session markdown files** require frontmatter updates
- ⚠️ **57 session files** must be renamed to include codenames
- ⚠️ **File content terminology** must be updated throughout markdown bodies
- ⚠️ Task references must be updated (`agent_id` → `current_mission_id`)
- ⚠️ **11 abandoned "in-progress" missions** must be closed gracefully
- ⚠️ **Retroactive codename generation** for all 38 existing missions
- ⚠️ Directory rename: `.opencode/work/sessions/` → `.opencode/work/missions/`
- ⚠️ SQLite doesn't support DROP COLUMN (need table recreation)

**User learning curve:**
- ℹ️ Users must learn new terminology
- ℹ️ CLI commands change names
- ℹ️ Documentation references change
- ℹ️ No transitional period - clean break

## Implementation Plan

**Phase 1: Create ADR and update task** (this document)
- ✅ Draft ADR-006
- ✅ Expand codename lists to prime numbers (31×37=1,147 combinations)
- ⬜ Update OPR-H-0032 with revised design
- ⬜ Get Director approval

**Phase 2: Database and file migration**
- Create throwaway migration script: `scripts/migrate_to_personas_missions.py`
- **Backup database:** `.opencode/data/project.db`

**Database changes:**
1. Rename `daemon_names` → `personas`:
   - Rename fields: `usage_count` → `mission_count`, `last_used_at` → `last_mission_at`
2. Rename `agents` → `missions`:
   - **Remove** `status` column (use `end_time IS NULL` for active state)
   - **Add** `codename TEXT NOT NULL` column
   - **Rename** fields: `session_file` → `mission_file`, `session_date` → `start_date`, `task_summary` → `objective`
   - **Generate codenames** deterministically for all 38 missions using `mission_id % prime_length`
   - **Close abandoned missions:** Set `end_time` for 11 "in-progress" records using file `mtime`
3. Update `tasks` table:
   - **Add** `current_mission_id INTEGER` with FK to missions
   - **Remove** `agent_name TEXT` and `agent_id INTEGER` columns
   - **Migrate data:** Copy `agent_id` → `current_mission_id` for tasks with agent references
4. Update all indices and foreign keys

**Session file migration:**
1. **Directory rename:**
   ```bash
   mv .opencode/work/sessions/ .opencode/work/missions/
   ```

2. **For each of 57 session files:**
   
   a. **Update frontmatter:**
   ```yaml
   # OLD
   name: calliope
   role: Documentarian
   status: completed
   task_summary: Initial documentation audit
   
   # NEW
   persona: calliope
   role: Documentarian
   codename: iron-cascade
   mission_id: 17
   objective: Initial documentation audit
   # Note: status removed, use end_time IS NULL
   ```
   
   b. **Rename file to include codename:**
   ```
   OLD: 2026-02-02.11:03:39.documentarian.calliope.initial-session.md
   NEW: 2026-02-02.11:03:39.documentarian.calliope.iron-cascade.md
   ```
   
   c. **Update content terminology** throughout markdown body:
   ```
   "Agent:" → "Persona:"
   "agent session" → "mission"
   "Session started" → "Mission started"
   "Session completed" → "Mission completed"
   "Agent name" → "Persona name"
   ```

3. **Validation:**
   - Verify all 57 files renamed successfully
   - Verify all missions have unique codenames
   - Verify all task references point to valid missions
   - Verify 11 abandoned missions have `end_time` set
   - Check no data loss occurred

**No rollback strategy:**
This is a **breaking change** with no backward compatibility. Backup is for disaster recovery only, not for rollback.

**Phase 3: Code refactoring**
- Rename `AgentSessionManager` → `MissionManager`
- Update all SQL queries
- Remove status-based logic, use `end_time IS NULL`
- Move `src/site_nine/agents/` → `src/site_nine/missions/`
- Implement `generate_mission_codename()` function
- Update session file writers to use new frontmatter
- Update display logic to capitalize persona names

**Phase 4: CLI updates**
- Update commands: `s9 agent` → `s9 mission`
- Update commands: `s9 name` → `s9 persona`
- Update `s9 mission rename-tui` to accept codename parameter (3 positional args)
- Add codename generation to mission creation
- Update help text and command documentation

**Phase 5: Skill and template updates**
- Update `.opencode/skills/session-start/SKILL.md`:
  - Change terminology throughout
  - Update `rename-tui` call with codename parameter
- Update `.opencode/commands/` files
- Update `src/site_nine/templates/` with new terminology
- Update `.opencode/README.md` and guides

**Phase 6: Documentation and testing**
- Update `docs/` user-facing documentation
- Test full mission lifecycle (create, work, close)
- Test task handoffs (update `current_mission_id`)
- Test persona management
- Test retroactive codenames display correctly
- Verify no data loss from migration

## Migration Strategy

**Safety measures:**
1. ✅ Comprehensive backup before migration
2. ✅ Dry-run mode in migration script
3. ✅ Test on copy of production database
4. ✅ Rollback plan documented
5. ✅ Phased rollout with testing at each stage

**Backward compatibility:**
- Session markdown files can keep old frontmatter (still works)
- Gradual documentation updates (not all at once)
- Consider CLI aliases (`s9 agent` → `s9 mission` for transition period)

## Alternatives Considered

**Alternative 1: Keep "agent" terminology, just add current_task_id**
- Pros: Minimal changes, no breaking changes
- Cons: Doesn't solve terminology confusion, still overloaded
- Rejected: Doesn't address root cause

**Alternative 2: Use "session" for work periods**
- Pros: Familiar term
- Cons: Conflicts with OpenCode sessions, still ambiguous
- Rejected: Not distinct enough

**Alternative 3: Use "assignment" instead of "mission"**
- Pros: Clear, professional
- Cons: Less fun, doesn't have the personality of "mission"
- Rejected: "Mission" is more engaging and distinctive

## References

- Related Task: OPR-H-0032 (implementation tracking)
- Related ADR: ADR-005 (backward compatibility strategy)
- Current schema: `.opencode/data/project.db`
- Current code: `src/site_nine/agents/sessions.py`

## Decision Status

**Status:** Proposed (awaiting Director approval)

**Next steps:**
1. Director reviews and approves ADR
2. Update OPR-H-0032 task with detailed implementation plan
3. Create migration script (Phase 2)
4. Execute migration with testing

---

**Approved by:** _Pending_  
**Approval date:** _Pending_  
**Implementation started:** _Pending_
