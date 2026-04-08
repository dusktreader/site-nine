# ADR-009: Agent Coordination Patterns

**Status:** ACCEPTED  
**Date:** 2026-02-04  
**Deciders:** Tucker (Director), Ahura Mazda (Architect)  
**Related Tasks:** ARC-H-0057  
**Related ADRs:** ADR-006 (Entity Model Clarity), ADR-008 (Agent Messaging System)

## Context

While ADR-008 defines how agents communicate asynchronously through messaging, we need to establish patterns for how 
agents coordinate work, discover available help, and interact with the Director.

### Current Gaps

**Possession scope ambiguity:**
- Possessions can claim tasks, but there's no concept of working on an entire epic
- Once a possession completes a task, the possession ends
- No way to work through multiple tasks in sequence within a single possession
- Engineers working on epics must start new possessions for each task

**Availability discovery:**
- Agents can't see who's available to help with questions
- No way to advertise "I'm available for questions about epic X"
- Agents don't know if they should wait for help or ask Director to summon someone
- No visibility into which possessions are actively coordinating vs just working

**Director communication unclear:**
- Should Director be "Possession 0" in the messaging system?
- How does Director participate in agent coordination?
- When should agents message vs chat with Director?
- Director's role as observer vs participant needs clarification

**Minion mode confusion:**
- Originally conceived as blocking command (`s9 comms desk`), later reimplemented as `MinionWorker`
- But agents need to remain in OpenCode chat to talk to Director
- Need non-blocking way to advertise availability
- Need periodic status output so Director knows agent isn't stuck

## Decision

We will implement a coordination system with three key patterns: **Possession Scoping**, **Minion Mode**, and 
**Communication Channels**.

### Core Principles

1. **Possession Scoping:** Possessions can be scoped to tasks, epics, or general work (mutually exclusive)
2. **Minion Mode:** Possessions can advertise availability without blocking chat
3. **Director Channel:** Director communicates via OpenCode chat, not messaging system

### Possession Scoping

Possessions have three possible scopes (mutually exclusive):

```bash
# Task-scoped (current behavior)
s9 possession start <daemon> --role <role> --task <task-id>
# Works on specific task, possession ends when task completes

# Epic-scoped (NEW)
s9 possession start <daemon> --role <role> --epic <epic-id>
# Works on epic, can claim multiple tasks sequentially

# General (NEW)
s9 possession start <daemon> --role <role>
# No specific scope, flexible coordination work
```

**Schema:**
```sql
ALTER TABLE possessions ADD COLUMN epic_id TEXT REFERENCES epics(id) ON DELETE SET NULL;

CREATE INDEX idx_possessions_epic_id ON possessions(epic_id);

-- Validation: Possession has either epic_id OR a task pointing to it via current_possession_id
-- NOT both
```

**Semantics:**

**Task-scoped possessions:**
- Claim one specific task
- Work on it until complete
- Possession ends (existing behavior)

**Epic-scoped possessions:**
- Possession belongs to epic
- Can claim multiple tasks from that epic sequentially
- Task claiming validates: `task.epic_id == possession.epic_id`
- Task role must match possession role
- Possession ends when agent decides or epic complete

**General possessions:**
- No specific scope
- Can claim any task (subject to role matching)
- Used for coordination, administration, helping across epics
- Possession ends when agent decides

**Epic possession workflow:**
```bash
# Start possession for epic
s9 possession start ahura-mazda --role Architect --epic EPC-H-0004

# Claim first task
s9 task claim ARC-H-0057
# work...
s9 task complete ARC-H-0057

# Claim next task in epic
s9 task next  # Auto-finds next TODO task in possession.epic_id matching possession.role
# or manually: s9 task claim ARC-H-0058

# Continue until epic done or agent decides to end possession
s9 possession end
```

**New command:**
```bash
s9 task next
# Finds next TODO task in current possession's epic matching possession role
# Claims it automatically
# Error if no epic_id on possession
# Error if no tasks available
```

### Minion Mode

Minion mode is a **possession attribute** that advertises availability for questions, implemented as a **monitoring
command** that provides periodic status output.

**Schema:**
```sql
ALTER TABLE possessions ADD COLUMN minion_mode_active INTEGER DEFAULT 0;

CREATE INDEX idx_possessions_minion_mode ON possessions(minion_mode_active);

-- Note: minion_mode scope inferred from possession.epic_id
-- If epic_id IS NOT NULL → minion for that epic
-- If epic_id IS NULL → general minion availability
```

**Commands:**
```bash
# Start minion mode (default --start flag)
s9 comms desk                      # General availability
s9 comms desk --epic EPC-H-0004    # Epic-specific (only if possession.epic_id already set)
s9 comms desk --start              # Explicit

# Stop minion mode
s9 comms desk --stop
```

**Behavior when starting:**
```
✓ Minion mode enabled for EPC-H-0004
Monitoring for messages (checking every 30s)...

[30s later]
Checking comms... No new messages. (0 unread)

[30s later]  
Checking comms... 2 new messages!
- MSG-H-0201 from Possession #58: "Question about design"
- MSG-M-0202 from Possession #71: "Need clarification"

[Agent can still chat with Director between checks]
Agent: "Got 2 questions, handling them now"

[30s later]
Checking comms... No new messages. (0 unread)
```

**Key features:**
- Runs in foreground with periodic status output (every 30s)
- Shows Director the agent is alive and monitoring
- Agent can still interact with Director between status checks
- Exit with `s9 comms desk --stop` or Ctrl+C
- Sets `minion_mode_active=1` on start, `0` on stop
- Automatically disabled when possession ends

**Validation:**
```bash
# If possession already epic-scoped, --epic flag is redundant but allowed
s9 possession start ahura-mazda --role Architect --epic EPC-H-0004
s9 comms desk              # Infers epic from possession.epic_id
s9 comms desk --epic EPC-H-0004  # Explicit, must match possession.epic_id

# If possession is general, can't specify --epic
s9 possession start ahura-mazda --role Architect
s9 comms desk              # OK - general availability
s9 comms desk --epic EPC-H-0004  # ERROR - possession not scoped to epic
```

### Possession Discovery

Agents need to see who's available before sending messages.

**Enhanced possession list:**
```bash
s9 possession list --role Architect --active-only --epic EPC-H-0004
```

**New filters:**
- `--epic <epic-id>` - Filter by possessions working on epic
- (No `--minion-mode` flag - availability shown in output by default)

**Updated display:**
```
Active Possessions - Architect Role
┏━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃ ID    ┃ Daemon      ┃ Codename   ┃ Availability        ┃
┡━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
│ 62    │ ahura-mazda │ swift-...  │ Minion (EPC-H-0004) │
│ 58    │ thoth       │ cosmic-... │ Minion (All)        │
│ 71    │ ptah        │ iron-...   │ Working (EPC-H-0004)│
│ 72    │ maat        │ void-...   │ Working (ARC-H-0057)│
│ 73    │ osiris      │ neon-...   │ Working             │
└───────┴─────────────┴────────────┴─────────────────────┘
```

**Availability column logic:**
```python
if possession.minion_mode_active:
    if possession.epic_id:
        return f"Minion ({possession.epic_id})"
    else:
        return "Minion (All)"
else:
    if possession.epic_id:
        return f"Working ({possession.epic_id})"
    elif possession.current_task_id:
        task = get_task(possession.current_task_id)
        return f"Working ({task.id})"
    else:
        return "Working"
```

**Discovery workflow:**
```bash
# Engineer needs architect help
Engineer: s9 possession list --role Architect --epic EPC-H-0004 --json
# Parse JSON, check for minion_mode_active=1

# If found, send message
Engineer: s9 comms send --to-possession 62 "Question about ToolAdapter design..."

# If not found, ask Director
Engineer: "No Architect available for EPC-H-0004. Should I wait or do you want to summon one?"
Director: "Let me summon one now"
Director: /summon architect
```

### Communication Channels

Three distinct channels for different purposes:

#### 1. Agent ↔ Director (OpenCode Chat)

**Channel:** OpenCode TUI chat interface  
**Nature:** Synchronous, conversational, immediate  
**Use cases:**
- Agent asks Director for guidance/decisions
- Agent requests Director summon another agent
- Director gives instructions
- Agent reports progress/blockers
- Casual coordination

**Example:**
```
Agent: "I need an Architect for this epic. Should I wait or is someone available?"
Director: "Let me summon one now"
Director: /summon architect
```

#### 2. Agent ↔ Agent (Messaging System)

**Channel:** Database-backed async messaging (ADR-008)  
**Nature:** Asynchronous, structured, persistent  
**Use cases:**
- Technical questions between agents
- Epic coordination discussions
- Role-wide announcements
- Threaded decision-making

**Example:**
```bash
Engineer: s9 comms send --to-mission 62 "Question about adapter registry design"
Architect (in minion mode): s9 comms reply MSG-M-0201 "Use singleton pattern..."
```

#### 3. Director Observing Messages

**Director's role:** Observer, not participant  
**Capabilities:**
- View all conversations/discussions: `s9 comms list`, `s9 comms show <conv-id>`
- Check message status: `s9 comms status <msg-id>` (who read a broadcast)
- Monitor coordination: See how agents are collaborating
- Intervene in chat: Tell agents to adjust approach if needed

**Director does NOT:**
- Send messages through messaging system (no Possession 0)
- Receive messages in inbox
- Participate in discussions
- Have minion mode

**Director communicates with agents via OpenCode chat only.**

### Integration with Handoffs

Minion mode complements the existing handoff system (ADR-006):

**Handoff workflow:**
```bash
# Architect finishes design, hands off to Engineer
Architect: s9 handoff create OPR-H-0061 --to-role Engineer --summary "Ready for implementation"

# Administrator sees pending handoff
Admin: s9 handoff list --role Engineer --status pending

# Admin in minion mode, coordinates
Admin: s9 comms discuss --role Engineer "Task OPR-H-0061 ready for implementation"

# Engineer accepts handoff
Engineer: s9 handoff accept <handoff-id>
```

## Alternatives Considered

### Alternative 1: Director as Possession 0

**Approach:** Create special possession with `id=0`, `codename="prime-directive"` for Director to send/receive messages.

**Pros:**
- Director can participate in messaging system directly
- Consistent interface (all communication through messages)
- Director has message inbox like agents

**Cons:**
- Director lifecycle doesn't match possession lifecycle
- Director is always available (no start/end)
- Minion mode doesn't apply to Director
- OpenCode chat already provides better synchronous communication
- Adds complexity to schema (special case `id=0`)

**Rejected because:** Director operates at a different abstraction level. OpenCode chat is the natural communication 
channel for Director ↔ Agent. Messaging system is for async agent coordination.

### Alternative 2: Explicit Epic Group Membership

**Approach:** When starting epic-scoped possession, add possession to explicit epic_participants table.

**Pros:**
- Clear "who's working on this epic" query
- Could support multiple epics per possession
- Explicit membership tracking

**Cons:**
- Adds junction table complexity
- Can already query: `SELECT * FROM possessions WHERE epic_id = 'EPC-H-0004'`
- Tasks already link possessions to epics via `current_possession_id`
- Doesn't add value over simple `possessions.epic_id` field

**Rejected because:** Simple foreign key `possessions.epic_id` provides same information without junction table.

### Alternative 3: Minion Mode as Blocking Interactive Command

**Approach:** `s9 comms desk` runs interactive TUI showing incoming messages, agent handles in UI.

**Pros:**
- Dedicated interface for message handling
- Could have rich UI (like email client)
- Clear "minion mode" vs "normal mode" distinction

**Cons:**
- Blocks OpenCode chat - agent can't talk to Director
- Requires complex TUI implementation
- Agent loses conversational flow with Director
- Can't easily switch between minion work and other tasks

**Rejected because:** Agent needs to remain available in OpenCode chat to talk to Director. Minion mode must be 
non-blocking with status output, not a separate interactive mode.

### Alternative 4: Allow Both Task and Epic Scope on Possession

**Approach:** Possession can have `epic_id` AND claim task from different epic.

**Pros:**
- More flexible
- Agent can help across epics while primary epic set

**Cons:**
- Confusing semantics (what does "epic-scoped" mean if you can claim tasks elsewhere?)
- Harder to answer "what's this possession working on?"
- Validation complexity
- Most use cases don't need this flexibility

**Rejected because:** Mutually exclusive scoping is clearer. If agent needs to help across epics, use general-scoped 
possession.

## Consequences

### Positive

- ✅ **Epic-scoped possessions:** Agents can work through multiple tasks in one possession
- ✅ **Discovery mechanism:** Agents can see who's available before messaging
- ✅ **Clear availability:** Minion mode advertises "I'm here to help"
- ✅ **Director visibility:** Periodic minion mode output shows agent is active
- ✅ **Communication clarity:** Three distinct channels (chat, messages, observation)
- ✅ **Flexible scoping:** Task/epic/general covers all coordination patterns
- ✅ **No blocking:** Minion mode doesn't prevent Director communication
- ✅ **Simple schema:** Minimal new fields (epic_id, minion_mode_active)

### Negative

- ⚠️ **New concepts:** Agents must learn possession scoping and minion mode patterns
- ⚠️ **Validation complexity:** Must enforce mutual exclusivity of scopes
- ⚠️ **Minion mode polling:** 30s checks could miss urgent messages (acceptable tradeoff)
- ⚠️ **Epic possession lifecycle:** Less clear when possession should end (agent decides)
- ⚠️ **Task claiming logic:** `s9 task next` adds new workflow to learn

### Risks & Mitigation

| Risk | Mitigation |
|------|-----------|
| **Epic possessions never end** | Add possession duration warnings; Directors can check long-running possessions; Add `s9 possession stats` to show possession age |
| **Agents claim tasks outside their epic** | Validation: `task.epic_id == possession.epic_id` for epic-scoped possessions; Return clear error |
| **Minion mode spam** | 30s check interval is reasonable; Add `--interval` flag if needed; Agent can exit with Ctrl+C or `--stop` |
| **Confusion about Director channel** | Clear documentation in skills; Update possession-start to explain channels; Training/onboarding |
| **Availability column ambiguity** | Show full epic ID for clarity; Could add tooltip/help text; JSON output provides structured data |
| **Possession scope creep** | Clear validation errors; Documentation of scope semantics; Examples in skills |

## Implementation Status

### Phase 1: Possession Scoping ✅ (Complete)

- ✅ **Schema migration** (OPR-H-0091): `possessions.epic_id` field added with foreign key constraint
- ✅ **Update possession start** (OPR-H-0092): `--epic` flag added, mutual exclusivity validation working
- ✅ **Epic scoping validation** (OPR-H-0093): Task claims validate epic_id matching in `TaskManager.claim_task()`
- ✅ **Update possession display**: Epic shown in `s9 possession show` and JSON output
- ✅ **Testing**: 13 tests covering epic-scoped possessions and task claiming validation
- ⛔ **`s9 task next`**: Deferred indefinitely — possessions no longer claim task sequences in practice

### Phase 2: Possession Discovery ⛔ (Superseded)

The `s9 comms desk` interactive command and possession-list discovery pattern described here were
**not implemented**. Instead, the architecture evolved (ADR-014) to explicit Admin orchestration via
`summon_minion` / `worker_message` / `watch_inbox`. Discovery via `s9 possession list --minion-mode`
is no longer needed — the Admin knows the possession IDs of every worker it spawned.

### Phase 3: Minion Mode ✅ (Implemented via MinionWorker, not `s9 comms desk`)

The `s9 comms desk` blocking command described in this ADR was **never built**. Minion mode was
implemented instead as a persistent Python process (`src/site_nine/workers/minion_worker.py`), launched
headlessly via `s9 summon --minion`. This diverges from the original design in three ways:

- No interactive `s9 comms desk` command; workers are fully headless
- Polling loop and inbox checking are handled by `MinionWorker`, not the agent itself
- Admin spawns and coordinates workers via `summon_minion` / `worker_message` / `watch_inbox` tools

**Completed (as-built):**
- ✅ `possessions.minion_mode_active` schema field
- ✅ `MinionWorker` class with 30s polling loop (`src/site_nine/workers/minion_worker.py`)
- ✅ `s9 summon --minion` CLI flag that launches `minion_worker.py`
- ✅ `summon_minion` / `exorcise_minion` OpenCode tools for Admin orchestration
- ✅ `watch_inbox` tool for Admin to block-wait on worker responses
- ✅ Graceful shutdown (SIGTERM/SIGINT → possession-end skill)
- ✅ Log output redirected to `~/.local/state/site-nine/logs/minion-worker-{role}.log`
- ✅ Inquisitor (ENG-M-0246) auto-exorcises zombie possessions after 8 hours

**Remaining gaps (tracked in ARC-H-0257):**
- ⏸️ Worker-maintained markdown journal replacing role-scoped log file
- ⏸️ Admin timeout / crash-detection strategy when `watch_inbox` blocks indefinitely
- ⏸️ Auto-restart / crash recovery for `minion_worker.py` process itself
- ⏸️ Git worktree isolation for parallel workers (PROPOSED — ADR-015)

### Phase 4: Skills and Documentation ✅ (Complete)

- ✅ `possession-start` skill updated with Admin orchestration paths (EPC-H-0008)
- ✅ Minion mode orchestration guide: `.opencode/docs/guides/minion-mode-orchestration.md`
- ✅ Admin orchestration guide: `.opencode/docs/guides/admin-orchestration.md`
- ✅ AGENTS.md updated with tool references and Director→Admin→Workers hierarchy

## References

- Related Task: ARC-H-0057 (Design ToolAdapter protocol)
- Related Epic: EPC-H-0004 (Multi-Tool Adapter System)
- Related ADR: ADR-006 (Entity Model Clarity - Daemons, Possessions, Agents)
- Related ADR: ADR-008 (Agent Messaging System)
- Related ADR: ADR-014 (Message-Driven Coordination Architecture — supersedes handoff patterns and s9 comms desk)
- Related ADR: ADR-015 (Git Worktree Isolation for Minion Workers — PROPOSED)
- Open gaps task: ARC-H-0257 (Minion worker robustness and observability)

## Notes

**Design Philosophy:**
- Simple scoping: Three clear options (task/epic/general), mutually exclusive
- Non-blocking coordination: Minion mode doesn't block Director communication
- Clear channels: Chat for Director, messages for agents, observation for Director
- Explicit coordination: Admin knows all worker possession IDs; no discovery polling needed

**Communication Channel Summary:**

| Channel | Participants | Nature | Use Case |
|---------|-------------|--------|----------|
| **OpenCode Chat** | Agent ↔ Director | Sync | Guidance, requests, coordination |
| **Messaging** | Agent ↔ Agent | Async | Technical questions, discussions |
| **Observation** | Director → Messages | Read-only | Monitoring, oversight |

**Note on workflow examples:** The `s9 comms desk` and `s9 possession list --role` patterns described in
the original ADR were not implemented. The actual coordination pattern is Admin-driven via
`summon_minion` / `worker_message` / `watch_inbox` tools. See ADR-014 and
`.opencode/docs/guides/minion-mode-orchestration.md` for current patterns.

---

**Status:** ACCEPTED
**Last reviewed:** 2026-04-06
