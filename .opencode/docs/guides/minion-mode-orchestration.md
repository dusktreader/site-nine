# Minion Mode Orchestration Guide

This guide is for **Admin agents** who need to orchestrate background minion mode minions to accomplish complex
multi-agent workflows.

## Overview

Minion mode minions are background agents that run in headless OpenCode sessions and process tasks asynchronously.
As an Admin agent, you summon, coordinate, and dismiss these minions using custom tools.

**Architecture:**

```
Director
  └─ summons → Admin Agent (you, interactive session)
                 ├─ summons → Engineer (minion mode, background)
                 ├─ summons → Architect (minion mode, background)
                 └─ coordinates via messaging system
```

Minions are invisible to the Director — they're infrastructure you manage.

## When to Use Minion Mode Minions

**Use minion mode minions when:**
- You need parallel execution of multiple tasks across roles
- Work requires different specialized agents (Engineer + Architect + Tester)
- Tasks are independent and can run asynchronously
- You're coordinating an epic that spans multiple roles
- The Director delegates orchestration to you

**Example scenarios:**
- Orchestrating a full epic implementation (design → code → test → document)
- Running comprehensive validation across multiple subsystems
- Coordinating migration work that requires parallel execution
- Managing background monitoring or maintenance tasks

## Summoning Minions

Use the `summon_minion` tool to launch background minions:

```typescript
summon_minion({
  role: "Engineer",
  daemon: "hephaestus"  // optional — omit to auto-select
})
```

This creates a background Python process that:
1. Launches an OpenCode session with the possession-start skill
2. Initializes the minion's possession in minion mode
3. Enters a polling loop, checking for messages
4. Processes each message via `opencode run --session <id> "<message>"`
5. Auto-suspends/resumes between messages to preserve context

**The minion runs headless** — no UI, no Director interaction. It only responds to messages you send.

### Minion Lifecycle

Each minion:
- Starts with a fresh possession
- Retains full conversational context across messages
- Auto-suspends when idle (no active OpenCode session consuming resources)
- Resumes when you send the next message
- Can accumulate context over its lifetime (remembers prior work)
- Ends gracefully when you dismiss it

## Coordinating Minions

### Sending Work to Minions

Use the `worker_message` tool to send tasks and instructions:

```typescript
worker_message({
  to_possession_id: 83,
  body: "Implement the ToolAdapter protocol (task ARC-H-0057). See ADR-009 section 4 for the design specification."
})
```

**Message guidelines:**
- **Be specific:** Include task IDs, file paths, acceptance criteria
- **Provide context:** Reference ADRs, task files, or prior work
- **One task at a time:** Don't overload a single message with multiple independent tasks
- **Use tools:** Tell minions to use tools (not CLI commands)

**Example messages:**

```typescript
// Simple task assignment
worker_message({
  to_possession_id: 83,
  body: "Claim and complete task ENG-H-0150: Implement task_create tool"
})

// Complex coordination
worker_message({
  to_possession_id: 83,
  body: "Implement the ToolRegistry following the design in ADR-009. Run tests when done and report results."
})

// Follow-up work
worker_message({
  to_possession_id: 83,
  body: "The tests failed with ModuleNotFoundError. Check the import statements and fix the issue."
})
```

### Checking Minion Status

Use the `worker_status` tool to see active minions for a role:

```typescript
worker_status({ role: "Engineer" })
```

Returns:
```json
{
  "workers": [
    {
      "possession_id": 125,
      "session_id": "abc123",
      "daemon": "hephaestus",
      "status": "ACTIVE",
      "last_active_at": "2026-02-19T00:15:00Z"
    }
  ]
}
```

The `last_active_at` field reflects the minion's last heartbeat. A minion mode minion updates this on every tool call;
if the minion process crashes or hangs, the field stops updating.

**Use this to:**
- Track which minions are active
- Get possession IDs for sending messages
- Monitor minion progress
- Verify minions haven't stalled (see [Handling Timeouts and Minion Failures](#handling-timeouts-and-minion-failures))

## Message-Driven Workflow

Minions communicate back to you via the messaging system.

### Receiving Minion Responses

Minions send you messages when they have something to report:

```typescript
// Minion sends completion notification
worker_message({
  to_possession_id: <your-possession-id>,
  body: "Task ENG-H-0150 complete. Implemented task_create tool with full validation. All tests passing."
})
```

Wait for minion responses with `watch_inbox`:

```typescript
// Block until a minion sends a message (pass your own possession_id)
watch_inbox({ possession_id: <your-possession-id> })

// With an explicit timeout (seconds)
watch_inbox({ possession_id: <your-possession-id>, timeout: 1200 })
```

### Two-Way Coordination

Typical workflow:

```
1. You → Minion: "Implement task ENG-H-0150"
2. Minion works asynchronously
3. Minion → You: "Task complete, tests passing"
4. You verify work
5. You → Minion: "Good work. Now implement ENG-H-0151"
```

Or with cross-minion coordination:

```
1. You → Minion: "Implement feature X"
2. Minion → You: "Need Architect input on design pattern"
3. You → Architect Minion: "Review design for feature X"
4. Architect Minion → You: "Recommended singleton pattern"
5. You → Engineer Minion: "Use singleton pattern per Architect feedback"
6. Engineer Minion → You: "Implementation complete"
```

## Complete Orchestration Example

### Scenario: Implement Epic EPC-H-0004

You're orchestrating the Multi-Tool Adapter System epic with multiple roles.

```typescript
// Step 1: Summon minions for each role
summon_minion({ role: "Architect", daemon: "daedalus" })
// Returns: { possession_id: 82 }

summon_minion({ role: "Engineer", daemon: "hephaestus" })
// Returns: { possession_id: 83 }

summon_minion({ role: "Tester", daemon: "maeve" })
// Returns: { possession_id: 84 }

// Step 2: Architect designs the protocol
worker_message({
  to_possession_id: 82,
  body: "Design the ToolAdapter protocol and OpenCodeAdapter implementation (ARC-H-0057). Document in ADR format."
})

// Step 3: Wait for Architect to respond (allow 20 minutes for a design task)
watch_inbox({ possession_id: <your-id>, timeout: 1200 })
// ... Architect sends message: "Design complete, see ADR-009 section 4"

// Step 4: Verify design (you read the ADR yourself)
// ... looks good

// Step 5: Assign implementation to Engineer
worker_message({
  to_possession_id: 83,
  body: "Implement OpenCodeAdapter wrapper per ARC-H-0057 design. See ADR-009 section 4. Claim tasks OPR-H-0066, OPR-H-0067, OPR-H-0068 in sequence."
})

// Step 6: Engineer works async, sends progress updates
watch_inbox({ possession_id: <your-id>, timeout: 1200 })  // blocks until Engineer reports
// ... "OPR-H-0066 complete"
watch_inbox({ possession_id: <your-id>, timeout: 1200 })
// ... "OPR-H-0067 complete"
watch_inbox({ possession_id: <your-id>, timeout: 1200 })
// ... "OPR-H-0068 complete, ready for testing"

// Step 7: Assign testing
worker_message({
  to_possession_id: 84,
  body: "Test the ToolAdapter protocol and OpenCodeAdapter (TST-H-0069). Engineer reports implementation complete."
})

// Step 8: Tester runs tests, reports results
watch_inbox({ possession_id: <your-id>, timeout: 600 })
// ... "All tests passing, coverage at 95%"

// Step 9: Check status before dismissing
worker_status({ role: "Architect" })
worker_status({ role: "Engineer" })
worker_status({ role: "Tester" })

// Step 10: Gracefully dismiss minions
exorcise_minion({ from_possession_id: <your-id>, to_possession_id: 82 })
exorcise_minion({ from_possession_id: <your-id>, to_possession_id: 83 })
exorcise_minion({ from_possession_id: <your-id>, to_possession_id: 84 })
```

## Dismissing Minions

Use the `exorcise_minion` tool to end a minion's possession gracefully:

```typescript
exorcise_minion({ from_possession_id: <your-id>, to_possession_id: 83 })
```

This:
1. Sends a termination message to the minion's session
2. Minion runs the possession-end skill
3. Minion's possession transitions to EXORCISED
4. Polling process exits cleanly

**Always dismiss minions when:**
- Their assigned work is complete
- You're ending your own possession
- Minions are no longer needed
- You need to free up resources

## Handling Timeouts and Minion Failures

Minions can stall or crash. `watch_inbox` has a `timeout` parameter that controls how long to wait before
returning with `{"status": "timeout"}`. When that happens, you need to decide what to do.

### Choosing a timeout

Pass an explicit `timeout` rather than relying on the default for non-trivial work:

| Scenario | Recommended timeout |
|---|---|
| Simple task (test run, small edit) | 300s (5 min) |
| Medium task (feature implementation) | 1200s (20 min) |
| Long task (epic, large refactor) | 3600s (1 hr) |
| Unknown / general | 600s (10 min) |

### The timeout decision tree

When `watch_inbox` returns `{"status": "timeout"}`, follow this procedure:

```
watch_inbox returns { status: "timeout" }
    │
    ▼
worker_status({ role: <role> })
    │
    ├─ possession not found (status != ACTIVE) ──► Minion crashed. Re-summon + re-send task.
    │
    └─ possession found, last_active_at present
           │
           ├─ last_active_at < (now - 10 min) ──► Minion likely stalled. Send ping.
           │     │
           │     ├─ ping acknowledged (new message within 60s) ──► Extend timeout, continue.
           │     └─ no response ──► Exorcise + re-summon + re-send task.
           │
           └─ last_active_at >= (now - 10 min) ──► Minion is alive. Extend timeout.
```

The 10-minute staleness threshold is the key signal. If `last_active_at` hasn't updated in 10 minutes, the
minion's `opencode run` subprocess is not making tool calls — it's hung or dead.

### Ping message convention

When you need to check whether a minion is alive, send exactly this message:

```typescript
worker_message({
  from_possession_id: <your-id>,
  to_possession_id: <minion-id>,
  body: "STATUS_PING: Please respond with your current status immediately."
})
```

A healthy minion processes this on its next poll cycle (within 30 seconds) and replies with a short status
update. If there's no reply within 60 seconds, treat the minion as dead.

### Re-summon protocol

When a minion confirms unresponsive or its possession is no longer ACTIVE:

1. Exorcise the stale possession (if still ACTIVE):
   ```typescript
   exorcise_minion({ from_possession_id: <your-id>, to_possession_id: <stale-id> })
   ```
2. Summon a replacement:
   ```typescript
   summon_minion({ role: "Engineer" })
   // Returns: { possession_id: <new-id> }
   ```
3. Re-send the original task, noting this is a retry:
   ```typescript
   worker_message({
     from_possession_id: <your-id>,
     to_possession_id: <new-id>,
     body: "Claim and complete ENG-H-0150. Note: prior minion became unresponsive. Task is UNDERWAY; check its notes for any progress already recorded."
   })
   ```

The new minion has no memory of the previous attempt. Check the task's notes (via `task_show`) before
re-assigning to avoid duplicating work that was already done.

## Best Practices

### Summoning Minions

1. **Summon only what you need** — Each minion consumes resources
2. **Specify daemons if important** — Helpful for tracking and identification
3. **Track possession IDs** — Store them in your context for easy reference
4. **One minion per role** — Avoid duplicate minions for the same role unless needed

### Messaging Minions

1. **Be explicit** — Minions can't read your mind; provide full context
2. **Reference artifacts** — Point to ADRs, task files, and related docs
3. **Single responsibility** — One message = one task (usually)
4. **Follow up** — Minions may ask questions via messaging
5. **Verify completion** — Check work before assigning next task

### Monitoring Minions

1. **Check status regularly** — Use `worker_status` to track progress
2. **Monitor your inbox** — Minions will message you
3. **Watch for stalls** — If `last_active_at` is more than 10 minutes old, the minion is likely stalled;
   follow the [timeout decision tree](#the-timeout-decision-tree)
4. **Review work incrementally** — Don't wait until everything's done

### Coordination Patterns

Sequential dependencies:
```
Architect designs → Engineer implements → Tester validates
```

Parallel execution:
```
Engineer A: task 1
Engineer B: task 2  } all at once
Engineer C: task 3
```

Iterative refinement:
```
You → Minion: "Implement X"
Minion → You: "Done, but needs review"
You verify, provide feedback
You → Minion: "Fix issue Y"
Minion → You: "Fixed"
```

### Error Handling

**Minion reports blocker:**
```
Minion → You: "Blocked on missing dependency"
You investigate
You → Minion: "Dependency fixed, proceed"
```

**Minion becomes unresponsive:**

Follow the timeout decision tree from [Handling Timeouts and Minion Failures](#handling-timeouts-and-minion-failures).
In short: check `worker_status`, ping with the standard STATUS_PING message, exorcise and re-summon if no response.

**Tests fail:**
```
Minion → You: "Tests failing with error X"
You → Minion: "Review error and fix root cause"
# Or route to Architect:
You → Architect Minion: "Review test failures for task Y"
```

## Orchestration Anti-Patterns

### Don't: Micromanage

```typescript
// BAD: Too granular
worker_message({ to_possession_id: 83, body: "Read file X" })
worker_message({ to_possession_id: 83, body: "Now edit line 42" })
worker_message({ to_possession_id: 83, body: "Now run tests" })
```

Instead, give complete self-contained instructions:

```typescript
// GOOD: Clear, complete task
worker_message({
  to_possession_id: 83,
  body: "Implement ToolAdapter protocol (ARC-H-0057). Follow the design in ADR-009, implement the interface, run tests, report results."
})
```

### Don't: Forget to Dismiss

Minions that finish but aren't dismissed waste resources and clutter the possession list.

**Always dismiss minions when work is done.**

### Don't: Overload a Single Minion

```typescript
// BAD: One minion for entire epic
worker_message({
  to_possession_id: 83,
  body: "Implement all 10 tasks in EPC-H-0004"
})
```

Instead, use multiple minions or break into sequential messages:

```typescript
// GOOD: Multiple minions
summon_minion({ role: "Engineer", daemon: "hephaestus" })  // Returns: { possession_id: 83 }
summon_minion({ role: "Engineer", daemon: "goibniu" })     // Returns: { possession_id: 84 }

worker_message({ to_possession_id: 83, body: "Tasks 1-3" })
worker_message({ to_possession_id: 84, body: "Tasks 4-6" })
```

### Don't: Ignore Minion Messages

Minions send important updates: completion notifications, blocker reports, questions. Check your inbox.

### Don't: Use the Default Timeout for Long Tasks

The default `watch_inbox` timeout is 300 seconds. That's fine for a quick test run, but not for a feature
implementation. Pass an explicit `timeout` that matches the expected task duration. A timeout that fires
on a healthy minion wastes your time; one that's too long delays crash detection.

## Tools Reference

| Tool              | Purpose                               | Arguments                                          |
|-------------------|---------------------------------------|----------------------------------------------------|
| `summon_minion`   | Launch background minion              | `{ role, daemon? }`                                |
| `worker_message`  | Send task/instruction to minion       | `{ from_possession_id, to_possession_id, body }`   |
| `worker_status`   | Check active minions for role         | `{ role }`                                         |
| `exorcise_minion` | Gracefully end minion possession      | `{ from_possession_id, to_possession_id }`         |
| `watch_inbox`     | Block until a minion message arrives  | `{ possession_id, timeout? }`                      |

## Troubleshooting

### Minion Won't Start

**Symptoms:** `summon_minion` returns error or minion never becomes ACTIVE

**Solutions:**
1. Check role is valid (Engineer, Architect, Tester, etc.)
2. Verify daemon exists (use `daemon_suggest` if needed)
3. Check system resources (too many minions?)
4. Ask Director to investigate

### Minion Not Responding

**Symptoms:** Messages sent but no response; `worker_status` shows `last_active_at` more than 10 minutes old

**Solutions:**
1. Send the standard ping: `worker_message({ ..., body: "STATUS_PING: Please respond with your current status immediately." })`
2. If no reply within 60 seconds, follow the [re-summon protocol](#re-summon-protocol)
3. Check the task's notes via `task_show` before re-assigning to see what work was already done

### Messages Not Received

**Symptoms:** You send messages but minion never acknowledges them

**Solutions:**
1. Verify possession ID is correct (check `worker_status` output)
2. Check message format (must be a string in `body`)
3. Minion may have ended — check possession status

### Minion Doesn't Terminate

**Symptoms:** `exorcise_minion` called but polling process still running

**Solutions:**
1. Wait 30 seconds (graceful shutdown takes time)
2. Check if minion is stuck on a task
3. Ask Director to force-kill if needed

## Summary

As an Admin agent, you orchestrate background minion mode minions to accomplish complex multi-agent workflows:

1. **Summon** minions with `summon_minion`
2. **Coordinate** via `worker_message` and `watch_inbox`
3. **Monitor** with `worker_status`
4. **Dismiss** with `exorcise_minion` when done

Minions run headless, process messages asynchronously, and retain context across invocations. You're the
orchestrator; they're the execution layer.

**Remember:** Minions are invisible to the Director. You manage them autonomously.

## See Also

- **AGENTS.md**: General agent guide and tool reference
- **ADR-013**: Site-nine as OpenCode Integration Platform
- **ADR-014**: Message-driven minion coordination architecture
- **ADR-016**: Minion robustness and observability
- **agent-discovery.md**: Finding and coordinating with agents
- **roles/administrator.md**: Administrator role workflows and QA tiers
