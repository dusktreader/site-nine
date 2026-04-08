# ADR-014: Message-Driven Coordination Architecture

**Status**: Proposed  
**Date**: 2026-02-28  
**Deciders**: Tucker Beck, Dagon (Possession 150)  
**Related**: ADR-008 (Agent Messaging System), ADR-009 (Agent Coordination Patterns)

> **Implementation Note (2026-04-07):** The `worker_spawn` tool referenced throughout this ADR was renamed to
> `summon_minion` after this document was written. Wherever this ADR says `worker_spawn`, the current tool name
> is `summon_minion`. The return value `status: "spawned"` was also updated to `status: "summoned"`. No other
> behaviour changed.

## Context

Site-nine currently has two overlapping coordination mechanisms:

1. **Handoffs** - Agents create handoff documents and DB records, next agent discovers via `handoff_list()`
2. **Messages** - Agents send messages to specific possessions via `worker_message()`

During testing of minion mode workers (ADM-H-0202, Possession 150), we discovered fundamental problems with the handoff system in a message-driven orchestration model:

- **Race conditions**: Multiple minion workers polling for handoffs create ambiguity about who claims what
- **Unclear lifecycle**: When does a worker stop looking for handoffs? Who decides when work is done?
- **Redundancy**: Messages can carry the same context/instructions that handoffs provide
- **Pattern confusion**: Handoffs imply sequential work (A→B→C), minion mode implies parallel work (Admin→1,2,3 simultaneously)
- **Discovery overhead**: Handoffs require polling/checking, messages are explicit delivery

The original vision for site-nine assumed Director would summon agents one-by-one in interactive sessions. Handoffs made sense for this sequential model. However, the actual usage pattern has evolved toward:

**Director ↔ Admin ↔ Workers**

Where:
- Director interacts with a single Admin agent
- Admin orchestrates multiple minion mode workers
- Workers execute tasks in parallel via message-driven coordination

In this model, handoffs add complexity without providing value.

## Decision

**We will remove the handoff system entirely and standardize on message-driven coordination.**

### New Architecture

```
Director (Human)
    ↓
  Admin Agent (Interactive, summoned by Director)
    ↓
  ├─ Worker 1 (minion mode, message-driven)
  ├─ Worker 2 (minion mode, message-driven)
  └─ Worker 3 (minion mode, message-driven)
```

**Core principles:**

1. **Director summons Admin** - The entry point is always an Administrator agent in interactive mode
2. **Admin orchestrates workers** - Admin uses `worker_spawn()` tool to spawn workers as needed
3. **Messages are the coordination mechanism** - All work assignment via `worker_message()` tool
4. **Explicit addressing** - Messages target specific `possession_id`, no discovery/polling for work
5. **Workers are stateless** - Each message is self-contained with full context needed to complete work
6. **Agents never use CLI** - All coordination via tools (`worker_spawn`, `worker_message`, etc.)

### What Replaces Handoffs

| Handoff Feature | Message-Driven Replacement |
|----------------|---------------------------|
| Context document in `.opencode/work/handoffs/` | Message body (markdown, full context) |
| `handoff_create()` with summary | `worker_message()` with detailed instructions |
| `handoff_list()` for discovery | Admin explicitly assigns via `worker_message()` |
| Role-based routing | Admin checks `worker_status()`, sends to specific possession |
| Task association | Message includes `task_id` parameter |

### Worker Spawning

Admin agents use the `worker_spawn()` tool to create minion-mode workers:

```typescript
// Spawn a worker
const result = worker_spawn({ 
  role: "Engineer",
  daemon: "hephaestus",  // optional - auto-selected if omitted
  poll_interval: 30  // optional - seconds between message checks
})
// Returns: { possession_id: 123, role: "Engineer", daemon: "hephaestus", status: "spawned" }
```

**Important:** Agents must NEVER use `s9 summon` CLI. The `worker_spawn` tool is the only way for agents to spawn workers. CLI is for Director only.

### Example Workflow

**Before (Handoff-based):**
```typescript
// Agent A creates handoff
handoff_create({
  task_id: "ENG-H-0150",
  to_role: "Engineer", 
  summary: "Implement feature X",
  files: ["src/foo.py"],
  acceptance_criteria: "..."
})
task_release({ task_id: "ENG-H-0150" })

// Later... Agent B starts possession
handoff_list({ role: "Engineer" })  // Discovers handoff
// Reads handoff document
task_claim({ task_id: "ENG-H-0150" })
handoff_delete({ handoff_id: 1 })
// Does work
```

**After (Message-driven):**
```typescript
// Admin spawns worker
const worker = worker_spawn({ role: "Engineer" })
// Returns: { possession_id: 123, daemon: "wayland", ... }

// Admin sends work directly
worker_message({
  from_possession_id: 150,
  to_possession_id: 123,
  task_id: "ENG-H-0150",
  priority: "HIGH",
  body: `
## Task: Implement feature X

**Files**: src/foo.py
**Acceptance criteria**: 
- Feature works end-to-end
- Tests added and passing
- No breaking changes

**Context**: [Full explanation of what's needed]
  `
})

// Worker receives message, does work
// Worker optionally sends status back to admin
worker_message({
  from_possession_id: 123,
  to_possession_id: 150,
  body: "Task ENG-H-0150 complete. All tests passing."
})
```

## Implementation Plan

This is a major architectural change requiring coordinated work across multiple components.

### Phase 1: Core Removal (CRITICAL PATH)

1. **Remove handoff tools** (ENG-C-0217)
   - Delete `.opencode/tools/handoff_*.ts`
   - Remove tool implementations (`.opencode/tools/handoff_*.py`)
   - Remove from tool exports

2. **Remove handoff CLI commands** (ENG-H-0218)
   - Delete `src/site_nine/cli/handoff.py`
   - Remove from CLI registration

3. **Remove handoff database support** (ENG-M-0219)
   - Keep `handoffs` table for now (data preservation)
   - Remove HandoffManager class
   - Remove handoff models
   - Mark table as deprecated in schema comments

4. **Remove handoff skill** (DOC-C-0220)
   - Delete `.opencode/skills/handoff-workflow/`
   - Remove from skill registry

5. **Create worker_spawn tool** (ENG-H-0230) - **CRITICAL**
   - Agents must NEVER use `s9 summon` CLI (CLI is Director-only)
   - Create `.opencode/tools/worker_spawn.ts` (TypeScript)
   - Create `.opencode/tools/worker_spawn.py` (Python implementation)
   - Spawns minion_worker.py via subprocess.Popen
   - Returns spawned possession_id for subsequent worker_message calls
   - Parameters: role, daemon (optional), model (optional), poll_interval (optional)
   - Validates role, waits for possession creation, returns possession details

### Phase 2: Documentation Rewrite (HIGH PRIORITY)

6. **Create message-driven coordination guide** (DOC-H-0221)
   - New comprehensive guide for Admin agents
   - Worker lifecycle (spawn via worker_spawn, message, monitor, terminate)
   - Message patterns and best practices
   - Example workflows for common scenarios
   - Troubleshooting guide

7. **Update possession-start skill** (DOC-H-0222)
   - Remove handoff discovery steps (Step 7)
   - Update Step 11 to use worker_spawn tool (not s9 summon CLI)
   - Add message-driven workflow explanation
   - Update examples to show Admin patterns

8. **Update all role documentation** (DOC-H-0223)
   - Remove handoff references from all 9 role docs
   - Add message coordination patterns
   - Show Admin orchestration patterns (using worker_spawn tool)
   - Update Administrator doc with new central role

9. **Update AGENTS.md** (DOC-C-0224)
   - Remove handoff tool references
   - Add worker_spawn to coordination tools section
   - Add comprehensive message-driven section
   - Clarify Director→Admin→Workers hierarchy
   - Update coordination examples

10. **Update minion-mode-orchestration.md** (DOC-M-0225)
    - Already mostly message-driven, but refine
    - Remove any handoff references
    - Strengthen Admin orchestration patterns
    - Update examples to use worker_spawn

11. **Archive/update ADR-009** (DOC-M-0226)
     - ADR-009 defined Agent Coordination Patterns (including handoffs)
     - Update to reflect message-only coordination
     - Or create superseding ADR (this one)

### Phase 3: Code Cleanup

12. **Remove handoff references from codebase** (ENG-M-0227)
     - Grep for "handoff" references
     - Remove unused imports
     - Clean up any handoff-related logic in possessions/tasks

13. **Update tests** (TST-H-0228)
     - Remove handoff-related tests
     - Add message coordination tests
     - Update integration tests to use message patterns

### Phase 4: Schema Evolution (OPTIONAL, LATER)

14. **Drop handoffs table** (ENG-L-0229)
    - Only after Phase 1-3 complete and stable
    - Create migration to drop table
    - Archive any existing handoff data

## Consequences

### Positive

- **Simpler mental model**: One coordination mechanism (messages), not two
- **Explicit coordination**: No ambiguity about who does what
- **Better for parallel work**: Admin can orchestrate multiple workers simultaneously
- **No race conditions**: Messages target specific possessions, no polling conflicts
- **Clearer lifecycle**: Message sent → received → processed → done
- **More flexible**: Message body can contain arbitrary context/instructions
- **Better observability**: Message history shows exactly what was assigned to whom

### Negative

- **Breaking change**: Existing workflows/guides need rewriting
- **Loss of discovery pattern**: Can no longer have "next available agent picks up work"
  - Mitigation: Admin explicitly checks `worker_status()` and assigns
- **More orchestration burden on Admin**: Must explicitly route work
  - Mitigation: This is actually better - Admin has full control and visibility
- **Context documents lost**: `.opencode/work/handoffs/` pattern goes away
  - Mitigation: Message body can contain full markdown context
  - Alternative: Use task notes or possession notes for persistent context

### Risks

1. **Large scope**: Touches tools, CLI, docs, skills, potentially DB schema
   - Mitigation: Break into phases, critical path first
   
2. **Existing data**: Handoff records in database
   - Mitigation: Keep table, mark deprecated, drop later
   
3. **Learning curve**: Admins need to learn orchestration patterns
   - Mitigation: Comprehensive documentation with examples
   
4. **Incomplete cleanup**: References scattered across codebase
   - Mitigation: Thorough grep, systematic approach

## Alternative Considered

**Keep both handoffs and messages, clarify when to use each**

- Handoffs for sequential interactive work
- Messages for parallel minion mode work

**Rejected because:**
- Still confusing (two mechanisms)
- Still has race conditions with multiple workers
- Adds complexity without sufficient value
- Messages can handle both use cases

## Notes

This ADR represents a fundamental shift in site-nine's coordination model:

**Old model**: Director summons agents sequentially, handoffs between them  
**New model**: Director summons Admin, Admin orchestrates workers via messages

This aligns better with:
- How the system is actually being used (see Possession 150 testing)
- Modern distributed system patterns (message-driven, explicit addressing)
- Reducing cognitive load (one coordination mechanism)

The handoff system served us well during early development, but has become a liability as the architecture matured toward orchestrated parallel execution.

## Status

**Proposed** - Pending approval

Once approved, create tasks for all implementation phases and assign to appropriate roles.

## References

- ADR-008: Agent Messaging System (foundation for this change)
- ADR-009: Agent Coordination Patterns (being superseded/refined)
- ADR-013: Site-nine as OpenCode Integration Platform
- Possession 150: Desk mode testing that revealed these issues
- Task ADM-H-0202: Inter-agent communication testing
