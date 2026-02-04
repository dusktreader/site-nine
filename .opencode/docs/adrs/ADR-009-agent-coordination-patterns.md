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

**Mission scope ambiguity:**
- Missions can claim tasks, but there's no concept of working on an entire epic
- Once a mission completes a task, the mission ends
- No way to work through multiple tasks in sequence within a single mission
- Engineers working on epics must start new missions for each task

**Availability discovery:**
- Agents can't see who's available to help with questions
- No way to advertise "I'm available for questions about epic X"
- Agents don't know if they should wait for help or ask Director to summon someone
- No visibility into which missions are actively coordinating vs just working

**Director communication unclear:**
- Should Director be "Mission 0" in the messaging system?
- How does Director participate in agent coordination?
- When should agents message vs chat with Director?
- Director's role as observer vs participant needs clarification

**Desk mode confusion:**
- Originally conceived as blocking command (`s9 comms desk`)
- But agents need to remain in OpenCode chat to talk to Director
- Need non-blocking way to advertise availability
- Need periodic status output so Director knows agent isn't stuck

## Decision

We will implement a coordination system with three key patterns: **Mission Scoping**, **Desk Mode**, and 
**Communication Channels**.

### Core Principles

1. **Mission Scoping:** Missions can be scoped to tasks, epics, or general work (mutually exclusive)
2. **Desk Mode:** Missions can advertise availability without blocking chat
3. **Director Channel:** Director communicates via OpenCode chat, not messaging system

### Mission Scoping

Missions have three possible scopes (mutually exclusive):

```bash
# Task-scoped (current behavior)
s9 mission start <persona> --role <role> --task <task-id>
# Works on specific task, mission ends when task completes

# Epic-scoped (NEW)
s9 mission start <persona> --role <role> --epic <epic-id>
# Works on epic, can claim multiple tasks sequentially

# General (NEW)
s9 mission start <persona> --role <role>
# No specific scope, flexible coordination work
```

**Schema:**
```sql
ALTER TABLE missions ADD COLUMN epic_id TEXT REFERENCES epics(id) ON DELETE SET NULL;

CREATE INDEX idx_missions_epic_id ON missions(epic_id);

-- Validation: Mission has either epic_id OR a task pointing to it via current_mission_id
-- NOT both
```

**Semantics:**

**Task-scoped missions:**
- Claim one specific task
- Work on it until complete
- Mission ends (existing behavior)

**Epic-scoped missions:**
- Mission belongs to epic
- Can claim multiple tasks from that epic sequentially
- Task claiming validates: `task.epic_id == mission.epic_id`
- Task role must match mission role
- Mission ends when agent decides or epic complete

**General missions:**
- No specific scope
- Can claim any task (subject to role matching)
- Used for coordination, administration, helping across epics
- Mission ends when agent decides

**Epic mission workflow:**
```bash
# Start mission for epic
s9 mission start ahura-mazda --role Architect --epic EPC-H-0004

# Claim first task
s9 task claim ARC-H-0057
# work...
s9 task complete ARC-H-0057

# Claim next task in epic
s9 task next  # Auto-finds next TODO task in mission.epic_id matching mission.role
# or manually: s9 task claim ARC-H-0058

# Continue until epic done or agent decides to end mission
s9 mission end
```

**New command:**
```bash
s9 task next
# Finds next TODO task in current mission's epic matching mission role
# Claims it automatically
# Error if no epic_id on mission
# Error if no tasks available
```

### Desk Mode

Desk mode is a **mission attribute** that advertises availability for questions, implemented as a **monitoring 
command** that provides periodic status output.

**Schema:**
```sql
ALTER TABLE missions ADD COLUMN desk_mode_active INTEGER DEFAULT 0;

CREATE INDEX idx_missions_desk_mode ON missions(desk_mode_active);

-- Note: desk_mode scope inferred from mission.epic_id
-- If epic_id IS NOT NULL → desk for that epic
-- If epic_id IS NULL → general desk availability
```

**Commands:**
```bash
# Start desk mode (default --start flag)
s9 comms desk                      # General availability
s9 comms desk --epic EPC-H-0004    # Epic-specific (only if mission.epic_id already set)
s9 comms desk --start              # Explicit

# Stop desk mode
s9 comms desk --stop
```

**Behavior when starting:**
```
✓ Desk mode enabled for EPC-H-0004
Monitoring for messages (checking every 30s)...

[30s later]
Checking comms... No new messages. (0 unread)

[30s later]  
Checking comms... 2 new messages!
- MSG-H-0201 from Mission #58: "Question about design"
- MSG-M-0202 from Mission #71: "Need clarification"

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
- Sets `desk_mode_active=1` on start, `0` on stop
- Automatically disabled when mission ends

**Validation:**
```bash
# If mission already epic-scoped, --epic flag is redundant but allowed
s9 mission start ahura-mazda --role Architect --epic EPC-H-0004
s9 comms desk              # Infers epic from mission.epic_id
s9 comms desk --epic EPC-H-0004  # Explicit, must match mission.epic_id

# If mission is general, can't specify --epic
s9 mission start ahura-mazda --role Architect
s9 comms desk              # OK - general availability
s9 comms desk --epic EPC-H-0004  # ERROR - mission not scoped to epic
```

### Mission Discovery

Agents need to see who's available before sending messages.

**Enhanced mission list:**
```bash
s9 mission list --role Architect --active-only --epic EPC-H-0004
```

**New filters:**
- `--epic <epic-id>` - Filter by missions working on epic
- (No `--desk-mode` flag - availability shown in output by default)

**Updated display:**
```
Active Missions - Architect Role
┏━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃ ID    ┃ Persona     ┃ Codename   ┃ Availability        ┃
┡━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
│ 62    │ ahura-mazda │ swift-...  │ Desk (EPC-H-0004)   │
│ 58    │ thoth       │ cosmic-... │ Desk (All)          │
│ 71    │ ptah        │ iron-...   │ Working (EPC-H-0004)│
│ 72    │ maat        │ void-...   │ Working (ARC-H-0057)│
│ 73    │ osiris      │ neon-...   │ Working             │
└───────┴─────────────┴────────────┴─────────────────────┘
```

**Availability column logic:**
```python
if mission.desk_mode_active:
    if mission.epic_id:
        return f"Desk ({mission.epic_id})"
    else:
        return "Desk (All)"
else:
    if mission.epic_id:
        return f"Working ({mission.epic_id})"
    elif mission.current_task_id:
        task = get_task(mission.current_task_id)
        return f"Working ({task.id})"
    else:
        return "Working"
```

**Discovery workflow:**
```bash
# Engineer needs architect help
Engineer: s9 mission list --role Architect --epic EPC-H-0004 --json
# Parse JSON, check for desk_mode_active=1

# If found, send message
Engineer: s9 comms send --to-mission 62 "Question about ToolAdapter design..."

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
Architect (in desk mode): s9 comms reply MSG-M-0201 "Use singleton pattern..."
```

#### 3. Director Observing Messages

**Director's role:** Observer, not participant  
**Capabilities:**
- View all conversations/discussions: `s9 comms list`, `s9 comms show <conv-id>`
- Check message status: `s9 comms status <msg-id>` (who read a broadcast)
- Monitor coordination: See how agents are collaborating
- Intervene in chat: Tell agents to adjust approach if needed

**Director does NOT:**
- Send messages through messaging system (no Mission 0)
- Receive messages in inbox
- Participate in discussions
- Have desk mode

**Director communicates with agents via OpenCode chat only.**

### Integration with Handoffs

Desk mode complements the existing handoff system (ADR-006):

**Handoff workflow:**
```bash
# Architect finishes design, hands off to Engineer
Architect: s9 handoff create OPR-H-0061 --to-role Engineer --summary "Ready for implementation"

# Administrator sees pending handoff
Admin: s9 handoff list --role Engineer --status pending

# Admin in desk mode, coordinates
Admin: s9 comms discuss --role Engineer "Task OPR-H-0061 ready for implementation"

# Engineer accepts handoff
Engineer: s9 handoff accept <handoff-id>
```

## Alternatives Considered

### Alternative 1: Director as Mission 0

**Approach:** Create special mission with `id=0`, `codename="prime-directive"` for Director to send/receive messages.

**Pros:**
- Director can participate in messaging system directly
- Consistent interface (all communication through messages)
- Director has message inbox like agents

**Cons:**
- Director lifecycle doesn't match mission lifecycle
- Director is always available (no start/end)
- Desk mode doesn't apply to Director
- OpenCode chat already provides better synchronous communication
- Adds complexity to schema (special case `id=0`)

**Rejected because:** Director operates at a different abstraction level. OpenCode chat is the natural communication 
channel for Director ↔ Agent. Messaging system is for async agent coordination.

### Alternative 2: Explicit Epic Group Membership

**Approach:** When starting epic-scoped mission, add mission to explicit epic_participants table.

**Pros:**
- Clear "who's working on this epic" query
- Could support multiple epics per mission
- Explicit membership tracking

**Cons:**
- Adds junction table complexity
- Can already query: `SELECT * FROM missions WHERE epic_id = 'EPC-H-0004'`
- Tasks already link missions to epics via `current_mission_id`
- Doesn't add value over simple `missions.epic_id` field

**Rejected because:** Simple foreign key `missions.epic_id` provides same information without junction table.

### Alternative 3: Desk Mode as Blocking Interactive Command

**Approach:** `s9 comms desk` runs interactive TUI showing incoming messages, agent handles in UI.

**Pros:**
- Dedicated interface for message handling
- Could have rich UI (like email client)
- Clear "desk mode" vs "normal mode" distinction

**Cons:**
- Blocks OpenCode chat - agent can't talk to Director
- Requires complex TUI implementation
- Agent loses conversational flow with Director
- Can't easily switch between desk work and other tasks

**Rejected because:** Agent needs to remain available in OpenCode chat to talk to Director. Desk mode must be 
non-blocking with status output, not a separate interactive mode.

### Alternative 4: Allow Both Task and Epic Scope on Mission

**Approach:** Mission can have `epic_id` AND claim task from different epic.

**Pros:**
- More flexible
- Agent can help across epics while primary epic set

**Cons:**
- Confusing semantics (what does "epic-scoped" mean if you can claim tasks elsewhere?)
- Harder to answer "what's this mission working on?"
- Validation complexity
- Most use cases don't need this flexibility

**Rejected because:** Mutually exclusive scoping is clearer. If agent needs to help across epics, use general-scoped 
mission.

## Consequences

### Positive

- ✅ **Epic-scoped missions:** Agents can work through multiple tasks in one mission
- ✅ **Discovery mechanism:** Agents can see who's available before messaging
- ✅ **Clear availability:** Desk mode advertises "I'm here to help"
- ✅ **Director visibility:** Periodic desk mode output shows agent is active
- ✅ **Communication clarity:** Three distinct channels (chat, messages, observation)
- ✅ **Flexible scoping:** Task/epic/general covers all coordination patterns
- ✅ **No blocking:** Desk mode doesn't prevent Director communication
- ✅ **Simple schema:** Minimal new fields (epic_id, desk_mode_active)

### Negative

- ⚠️ **New concepts:** Agents must learn mission scoping and desk mode patterns
- ⚠️ **Validation complexity:** Must enforce mutual exclusivity of scopes
- ⚠️ **Desk mode polling:** 30s checks could miss urgent messages (acceptable tradeoff)
- ⚠️ **Epic mission lifecycle:** Less clear when mission should end (agent decides)
- ⚠️ **Task claiming logic:** `s9 task next` adds new workflow to learn

### Risks & Mitigation

| Risk | Mitigation |
|------|-----------|
| **Epic missions never end** | Add mission duration warnings; Directors can check long-running missions; Add `s9 
mission stats` to show mission age |
| **Agents claim tasks outside their epic** | Validation: `task.epic_id == mission.epic_id` for epic-scoped missions; 
Return clear error |
| **Desk mode spam** | 30s check interval is reasonable; Add `--interval` flag if needed; Agent can exit with Ctrl+C or 
`--stop` |
| **Confusion about Director channel** | Clear documentation in skills; Update session-start to explain channels; 
Training/onboarding |
| **Availability column ambiguity** | Show full epic ID for clarity; Could add tooltip/help text; JSON output provides 
structured data |
| **Mission scope creep** | Clear validation errors; Documentation of scope semantics; Examples in skills |

## Implementation Plan

### Phase 1: Mission Scoping

**Tasks:**
1. **Schema migration:** Add `missions.epic_id` field
2. **Update mission start:** Add `--epic` flag, validate mutual exclusivity with `--task`
3. **Epic scoping validation:** Prevent task claims outside mission epic
4. **Implement `s9 task next`:** Find and claim next task in mission epic
5. **Update mission display:** Show mission scope in `s9 mission show`
6. **Testing:** Mission scoping workflows, validation edge cases

### Phase 2: Mission Discovery

**Tasks:**
1. **Add `--epic` filter** to `s9 mission list`
2. **Update mission list display:** Add Availability column
3. **Implement availability logic:** desk_mode_active + epic_id + current_task_id
4. **JSON output:** Ensure availability data in JSON mode (OPR-M-0074 dependency)
5. **Testing:** Discovery queries, filtering

### Phase 3: Desk Mode

**Tasks:**
1. **Schema migration:** Add `missions.desk_mode_active` field
2. **Implement `s9 comms desk`:** Start/stop flags, periodic checking
3. **Periodic status output:** 30s loop with "Checking comms..." messages
4. **Inbox integration:** Check `s9 comms inbox`, display message summaries
5. **Auto-disable on mission end:** Clear desk_mode_active when mission ends
6. **Testing:** Desk mode lifecycle, status output, Ctrl+C handling

### Phase 4: Skills Updates

**Tasks:**
1. **Update session-start skill:** Explain communication channels
2. **Add discovery patterns:** Show agents how to find available help
3. **Document workflows:** Epic missions, desk mode, asking Director for help
4. **JSON usage examples:** Update skills to use `--json` for data queries
5. **Testing:** Run through full coordination workflows

## References

- Related Task: ARC-H-0057 (Design ToolAdapter protocol)
- Related Task: OPR-M-0074 (Add --json output flag to all s9 commands)
- Related Epic: EPC-H-0004 (Multi-Tool Adapter System)
- Related ADR: ADR-006 (Entity Model Clarity - Personas, Missions, Agents)
- Related ADR: ADR-008 (Agent Messaging System)
- Handoffs: `.opencode/work/migrations/003_add_handoffs_table.sql`

## Notes

**Design Philosophy:**
- Simple scoping: Three clear options (task/epic/general), mutually exclusive
- Non-blocking coordination: Desk mode doesn't prevent Director communication
- Clear channels: Chat for Director, messages for agents, observation for Director
- Explicit availability: Missions advertise when they're available to help

**Communication Channel Summary:**

| Channel | Participants | Nature | Use Case |
|---------|-------------|--------|----------|
| **OpenCode Chat** | Agent ↔ Director | Sync | Guidance, requests, coordination |
| **Messaging** | Agent ↔ Agent | Async | Technical questions, discussions |
| **Observation** | Director → Messages | Read-only | Monitoring, oversight |

**Workflow Examples:**

**Example 1: Engineer needs Architect**
```bash
# Check availability
Engineer: s9 mission list --role Architect --epic EPC-H-0004
# Shows: ahura-mazda (Mission 62) - Desk (EPC-H-0004)

# Send message
Engineer: s9 comms send --to-mission 62 "Question about adapter design..."

# Architect (in desk mode) sees it
[30s check]
Checking comms... 1 new message!
- MSG-M-0203 from Mission #71: "Question about adapter design..."

Architect: s9 comms reply MSG-M-0203 "Use singleton pattern for registry..."
```

**Example 2: No one available**
```bash
# Check availability
Engineer: s9 mission list --role Architect --epic EPC-H-0004
# Shows: No results

# Ask Director
Engineer: "No Architect available for EPC-H-0004. Need design help."
Director: "Let me summon one now"
Director: /summon architect
```

**Example 3: Epic-scoped mission**
```bash
# Start epic mission
s9 mission start ahura-mazda --role Architect --epic EPC-H-0004

# Enter desk mode
s9 comms desk
✓ Desk mode enabled for EPC-H-0004
Monitoring for messages (checking every 30s)...

# Work on tasks
s9 task claim ARC-H-0057
# work...
s9 task complete ARC-H-0057

# Next task
s9 task next
# Claims ARC-H-0058 automatically

# Continue until epic done
s9 mission end
```

---

**Status:** ACCEPTED  
**Next Step:** Create implementation tasks
