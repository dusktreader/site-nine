# Epic Possession Workflows and Minion Mode

This guide explains how to work on epic-scoped possessions and coordinate through minion
mode minions.

## Overview

**Epic possessions** are long-running possessions where an agent works through multiple
tasks within a single epic. Instead of ending the possession after each task, the agent
continues claiming tasks until the epic is complete or they choose to end the possession.

**Minion mode** is a headless background execution model where an agent runs as an
asynchronous minion, processing messages from an Admin orchestrator. Minion mode minions are
summoned by Admin agents using `summon_minion` — they don't enter minion mode themselves.

## Epic Possession Workflow

### Starting an Epic Possession

The Director scopes a possession to an epic at summon time:

```bash
s9 summon architect --epic EPC-H-0004
```

This scopes your possession to the epic and enables:

- Using `task_next` to auto-claim the next task in the epic
- Possession continuity across multiple related tasks
- Coordinating with other agents working the same epic

### Working Through Epic Tasks

#### Option 1: Manual Task Claiming

Claim specific tasks one at a time using tools:

```typescript
// Claim specific task
task_claim({ task_id: "ARC-H-0057" })

// Work on task...

// Close task when done
task_close({ task_id: "ARC-H-0057", status: "COMPLETE" })

// Claim next task manually
task_claim({ task_id: "ARC-H-0058" })
```

#### Option 2: Auto-claim with task_next (Recommended)

After closing a task, call `task_next` to claim the next one automatically:

```typescript
// Close current task
task_close({ task_id: "ARC-H-0057", status: "COMPLETE" })

// Auto-claim next task in the epic for your role
task_next()
// Finds next TODO task matching: possession.epic_id + possession.role
```

**Benefits of `task_next`:**

- No need to look up task IDs manually
- Automatically prioritizes tasks
- Ensures you stay within your epic scope
- Faster workflow for sequential work

### When to End an Epic Possession

End your epic possession when:

1. **Epic is complete** — all tasks for your role in the epic are done
2. **Context switch needed** — you need to work on a different epic
3. **Extended break** — you're stopping work for an extended period
4. Director dismisses you with `/dismiss`

**Important:** Don't end the possession between every task. Epic possessions are designed
for continuity.

## Minion Mode Minions

### What is Minion Mode?

Minion mode is a headless background execution model for agent minions. A minion mode
minion:

- Runs in a background OpenCode session (no UI, no Director interaction)
- Processes work assignments sent by an Admin orchestrator via `worker_message`
- Sends status updates back to Admin as it works
- Stays alive between messages, retaining full conversational context

**Minion mode minions are summoned by Admin agents using `summon_minion`** — they don't
enter minion mode on their own. The Director does not interact with them directly.

### The Architecture

```
Director
  └─ summons → Admin Agent (interactive session)
                  ├─ summons → Engineer Minion (minion mode, headless)
                  ├─ summons → Tester Minion (minion mode, headless)
                  └─ coordinates via worker_message / watch_inbox
```

### Summoning Minion Mode Minions (Admin)

Admin agents use `summon_minion` to launch background minions:

```typescript
summon_minion({ role: "engineer", daemon: "hephaestus" })
// Returns: { possession_id: 83 }
```

Minions are invisible to the Director. Admin manages them autonomously.

**See:** `.opencode/docs/guides/minion-mode-orchestration.md` for the complete
orchestration guide.

### Working as a Minion Mode Minion

If you are running in minion mode (the Director summoned you as a background minion):

- You receive work assignments via `worker_message` from your Admin orchestrator
- Process each message as a task assignment
- Send status updates back to Admin using `worker_message`
- The polling infrastructure handles message delivery automatically — you don't check
  for messages yourself

**You don't need to manage the polling loop.** The minion-worker infrastructure sends
messages to your session and invokes your responses.

## Complete Epic Possession Example (Admin Orchestrating Minions)

```typescript
// 1. Admin summons minions for the epic
summon_minion({ role: "architect", daemon: "daedalus" })
// Returns: { possession_id: 82 }

summon_minion({ role: "engineer", daemon: "hephaestus" })
// Returns: { possession_id: 83 }

// 2. Assign epic tasks to Architect
worker_message({
  to_possession_id: 82,
  body: "Design the ToolAdapter protocol (ARC-H-0057). Document in ADR format."
})

// 3. Wait for completion
watch_inbox()
// Architect reports: "Design complete, ADR-009 section 4"

// 4. Assign implementation to Engineer
worker_message({
  to_possession_id: 83,
  body: "Implement ToolAdapter wrapper (OPR-H-0066). See ADR-009 section 4."
})

// 5. Wait for engineering to finish
watch_inbox()
// Engineer reports: "Implementation complete"

// 6. Clean up
exorcise_minion({ to_possession_id: 82 })
exorcise_minion({ to_possession_id: 83 })
```

## Discovery: Finding Agents

Use `worker_status` to find active minion mode minions for a role:

```typescript
worker_status({ role: "Architect" })
```

Returns:

```json
{
  "workers": [
    {
      "possession_id": 82,
      "daemon": "daedalus",
      "status": "ACTIVE",
      "last_activity": "2026-03-01T00:15:00Z",
      "current_task": "ARC-H-0057"
    }
  ]
}
```

**See:** `.opencode/docs/guides/agent-discovery.md` for complete discovery patterns.

## Best Practices

### Epic Possessions

1. **Start with epic scope** — Director uses `--epic` flag at summon time
2. **Use `task_next`** — more efficient than manual claiming
3. **Don't end between tasks** — keep possession alive for continuity
4. **Update task artifacts** — document progress as you complete each task

### Minion Mode Minions (Admin)

1. **Summon only what you need** — each minion consumes resources
2. **Give clear work assignments** — include task IDs, context, acceptance criteria
3. **Wait for responses** — use `watch_inbox` instead of polling continuously
4. **Dismiss when done** — always call `exorcise_minion` when work is complete

### Coordination

1. **Use worker_status** — check active minions before summoning duplicates
2. **Be specific in messages** — include epic ID, task ID, full context
3. **Escalate when needed** — ask Director if no agents available
4. **Document decisions** — record coordination outcomes in task artifacts

## Tool Reference

| Tool | Purpose | Example |
|------|---------|---------|
| `task_claim` | Claim a specific task | `task_claim({ task_id: "ARC-H-0057" })` |
| `task_close` | Close a task when done | `task_close({ task_id: "ARC-H-0057", status: "COMPLETE" })` |
| `task_next` | Auto-claim next epic task | `task_next()` |
| `summon_minion` | Launch a minion mode minion | `summon_minion({ role: "engineer" })` |
| `worker_message` | Send work to a minion | `worker_message({ to_possession_id: 83, body: "..." })` |
| `worker_status` | Check active minions | `worker_status({ role: "engineer" })` |
| `watch_inbox` | Wait for minion responses | `watch_inbox()` |
| `exorcise_minion` | End a minion's possession | `exorcise_minion({ to_possession_id: 83 })` |

## Troubleshooting

### Can't find other agents

**Problem:** `worker_status` returns no minions for a role.

**Solution:**

- Summon a new minion with `summon_minion`
- Ask Director to investigate if summon fails

### Minion not responding

**Problem:** Sent a message but minion hasn't replied.

**Solution:**

- Send a status ping: `worker_message({ to_possession_id: 83, body: "Status?" })`
- Check `worker_status` for last_activity timestamp
- Dismiss and restart if truly unresponsive

### Minion finished but possession still open

This is normal. Minion mode minions stay alive after finishing a task and wait for the next
assignment. Send them another task or dismiss them when no more work is needed.

## See Also

- **Minion Mode Orchestration**: `.opencode/docs/guides/minion-mode-orchestration.md`
- **Agent Discovery**: `.opencode/docs/guides/agent-discovery.md`
- **ADR-013**: Site-nine as OpenCode Integration Platform
- **ADR-014**: Message-Driven Coordination Architecture
