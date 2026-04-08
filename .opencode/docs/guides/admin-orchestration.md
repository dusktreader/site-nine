# Admin Orchestration Guide

This guide covers the Administrator's role as the bridge between the Director's goals and the minions who
execute them. It focuses on practical message-driven coordination patterns.

## Overview

The Administrator sits between the Director (human) and minions (background agents):

```
Director (human)
  └─ summons → Administrator (interactive session)
                 ├─ summons → Engineer minion (minion mode)
                 ├─ summons → Tester minion (minion mode)
                 └─ summons → Documentarian minion (minion mode)
```

The Director gives you a goal. You break it down, summon minions, assign tasks, monitor progress, and report
back. Minions are invisible to the Director — you manage them autonomously.

## Core Responsibilities

- Break down Director goals into concrete tasks
- Summon minions with the right roles for each task
- Assign work explicitly via messages with enough context to act
- Monitor progress via `worker_status` and `watch_inbox`
- Review completed work before assigning next steps
- Dismiss minions when their phase is done
- Report outcomes to the Director

## Message-Driven Coordination

### Assigning Work

Every work assignment should include:

1. **Task ID** — so the minion can claim it
2. **Goal** — what success looks like
3. **Context** — relevant ADRs, prior work, constraints
4. **Report request** — ask for a reply when done

```typescript
worker_message({
  to_possession_id: 83,
  body: `Claim and complete ENG-H-0150: Implement rate limiting for MCP calls.

Design is in ADR-012. Key constraints:
- Use token bucket algorithm
- Max 50 calls/minute per client
- Configuration via environment variable RATE_LIMIT_MAX_CALLS

Run \`make qa\` when done and reply with results.`
})
```

### Checking for Responses

After assigning work, block until the minion reports back:

```typescript
watch_inbox()
// Returns when any minion sends a message
```

If you have multiple minions running in parallel, call `watch_inbox` once per expected response:

```typescript
// Assign to two minions
worker_message({ to_possession_id: 83, body: "Implement ENG-H-0150" })
worker_message({ to_possession_id: 84, body: "Implement ENG-H-0151" })

// Wait for both
watch_inbox()
watch_inbox()
```

### Status Checks

Check which minions are active and their possession IDs:

```typescript
worker_status({ role: "Engineer" })
```

Use this if you need to find a minion's possession ID or verify they're still running.

## Workflow Patterns

### Sequential Pipeline

Design → Implement → Test → Document, each phase waiting on the previous:

```typescript
// Phase 1: Design
const arch = summon_minion({ role: "Architect" })
worker_message({ to_possession_id: arch.possession_id, body: "Design rate limiting system (ARC-H-0150). Write ADR-012 with implementation plan." })
watch_inbox()
// Architect replies: "ADR-012 written and committed"

// Phase 2: Implement
const eng = summon_minion({ role: "Engineer" })
worker_message({ to_possession_id: eng.possession_id, body: "Implement rate limiting per ADR-012 (ENG-H-0151). Run make qa and reply with results." })
watch_inbox()
// Engineer replies: "ENG-H-0151 complete, all tests passing"

// Phase 3: Test
const tst = summon_minion({ role: "Tester" })
worker_message({ to_possession_id: tst.possession_id, body: "Validate rate limiting feature (TST-H-0152). Engineer reports complete. Test edge cases." })
watch_inbox()
// Tester replies: "All scenarios pass. One edge case found, created TST-H-0153."

// Clean up
exorcise_minion({ to_possession_id: arch.possession_id })
exorcise_minion({ to_possession_id: eng.possession_id })
exorcise_minion({ to_possession_id: tst.possession_id })
```

### Parallel Execution

Independent tasks can run at the same time:

```typescript
const eng1 = summon_minion({ role: "Engineer" })
const eng2 = summon_minion({ role: "Engineer" })

// Assign independent tasks simultaneously
worker_message({ to_possession_id: eng1.possession_id, body: "Implement ENG-H-0160: Add retry logic" })
worker_message({ to_possession_id: eng2.possession_id, body: "Implement ENG-H-0161: Add connection pooling" })

// Wait for both
watch_inbox()
watch_inbox()
```

### Interactive Refinement

When a minion needs input to continue:

```typescript
worker_message({ to_possession_id: 83, body: "Implement the cache invalidation strategy for task ENG-H-0170." })
watch_inbox()
// Minion replies: "Two options: TTL-based or event-driven. Which do you prefer?"

worker_message({ to_possession_id: 83, body: "Use TTL-based. Set default TTL to 300 seconds, configurable via CACHE_TTL env var." })
watch_inbox()
// Minion replies: "Done. ENG-H-0170 complete."
```

## Creating Tasks for Minions

Create tasks before summoning minions so they have something to claim:

```typescript
task_create({
  title: "Implement rate limiting for MCP calls",
  role: "Engineer",
  priority: "HIGH",
  description: `Add token bucket rate limiter per ADR-012.

Acceptance criteria:
- RateLimiter class in src/site_nine/rate_limit.py
- Integration with MCP client in src/site_nine/mcp.py
- Unit tests with ≥90% coverage
- make qa passes`
})
```

Check what tasks are already available before creating new ones:

```typescript
possession_dashboard({ role: "Administrator" })
task_show({ role: "Engineer", status: "TODO" })
```

## Handling Minion Problems

### Minion asks a question

```typescript
// Minion sends: "Should I use SQLite or PostgreSQL for the cache?"
worker_message({ to_possession_id: 83, body: "Use SQLite — match existing database choice." })
watch_inbox()
```

### Minion reports a blocker

```typescript
// Minion sends: "Missing dependency: redis-py not in pyproject.toml"
task_create({
  title: "Add redis-py dependency for cache implementation",
  role: "Engineer",
  priority: "HIGH",
  description: "ENG-H-0170 is blocked waiting for this."
})
worker_message({ to_possession_id: 83, body: "Add redis-py to pyproject.toml yourself — Engineers can modify pyproject.toml. Then continue." })
```

### Minion becomes unresponsive

```typescript
// 1. Check status
worker_status({ role: "Engineer" })

// 2. Send ping
worker_message({ to_possession_id: 83, body: "Status update?" })

// 3. If still no response after reasonable wait, restart
exorcise_minion({ to_possession_id: 83 })
const eng = summon_minion({ role: "Engineer" })
worker_message({ to_possession_id: eng.possession_id, body: "Resume ENG-H-0150 — prior minion became unresponsive. Task is UNDERWAY; check its notes for progress." })
```

## Reporting to Director

Keep the Director informed via the OpenCode chat. After key milestones:

- When a phase completes: "Architect finished ADR-012 design. Starting implementation."
- When blocked: "ENG-H-0150 blocked on missing test infrastructure. Creating task."
- When done: "Epic EPC-H-0004 complete. 3 tasks merged, all tests passing."

Don't over-report — the Director doesn't need updates for every minor step.

## Wrapping Up

When your orchestration goal is complete:

1. Dismiss all minions:
   ```typescript
   exorcise_minion({ to_possession_id: 83 })
   exorcise_minion({ to_possession_id: 84 })
   ```

2. Review outstanding tasks:
   ```typescript
   task_show({ status: "UNDERWAY" })
   ```

3. Report to Director: what was done, any follow-up tasks created, any concerns

4. Run the `possession-end` skill when Director dismisses you

## See Also

- **minion-mode-orchestration.md**: Deep reference for summoning and managing minions
- **AGENTS.md**: Full tool reference
- **roles/administrator.md**: Administrator role overview and QA tiers
- **ADR-014**: Message-driven minion coordination architecture
