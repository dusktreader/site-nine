# Desk Mode Orchestration Guide

This guide is for **Admin agents** who need to orchestrate background desk mode workers to accomplish complex
multi-agent workflows.

## Overview

Desk mode workers are background agents that run in headless OpenCode sessions and process tasks asynchronously.
As an Admin agent, you spawn, coordinate, and terminate these workers using custom tools.

**Architecture:**

```
Director
  └─ summons → Admin Agent (you, interactive session)
                 ├─ spawns → Engineer (desk mode, background)
                 ├─ spawns → Architect (desk mode, background)
                 └─ coordinates via messaging system
```

Workers are invisible to the Director — they're infrastructure you manage.

## When to Use Desk Mode Workers

**Use desk mode workers when:**
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

## Spawning Workers

Use the `summon_minion` tool to launch background workers:

```typescript
summon_minion({
  role: "Engineer",
  daemon: "hephaestus"  // optional — omit to auto-select
})
```

This creates a background Python process that:
1. Launches an OpenCode session with the possession-start skill
2. Initializes the worker's possession in desk mode
3. Enters a polling loop, checking for messages
4. Processes each message via `opencode run --session <id> "<message>"`
5. Auto-suspends/resumes between messages to preserve context

**The worker runs headless** — no UI, no Director interaction. It only responds to messages you send.

### Worker Lifecycle

Each worker:
- Starts with a fresh possession
- Retains full conversational context across messages
- Auto-suspends when idle (no active OpenCode session consuming resources)
- Resumes when you send the next message
- Can accumulate context over its lifetime (remembers prior work)
- Ends gracefully when you terminate it

**Note:** Workers don't need heartbeats — the polling process keeps them alive.

## Coordinating Workers

### Sending Work to Workers

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
- **Use tools:** Tell workers to use tools (not CLI commands)

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

### Checking Worker Status

Use the `worker_status` tool to see active workers for a role:

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
      "last_activity": "2026-02-19T00:15:00Z"
    }
  ]
}
```

**Use this to:**
- Track which workers are active
- Get possession IDs for sending messages
- Monitor worker progress
- Verify workers haven't stalled

## Message-Driven Workflow

Workers communicate back to you via the messaging system.

### Receiving Worker Responses

Workers send you messages when they have something to report:

```typescript
// Worker sends completion notification
worker_message({
  to_possession_id: <your-possession-id>,
  body: "Task ENG-H-0150 complete. Implemented task_create tool with full validation. All tests passing."
})
```

Wait for worker responses with `watch_inbox`:

```typescript
// Block until a worker sends a message
watch_inbox()
```

### Two-Way Coordination

Typical workflow:

```
1. You → Worker: "Implement task ENG-H-0150"
2. Worker works asynchronously
3. Worker → You: "Task complete, tests passing"
4. You verify work
5. You → Worker: "Good work. Now implement ENG-H-0151"
```

Or with cross-worker coordination:

```
1. You → Worker: "Implement feature X"
2. Worker → You: "Need Architect input on design pattern"
3. You → Architect Worker: "Review design for feature X"
4. Architect Worker → You: "Recommended singleton pattern"
5. You → Engineer Worker: "Use singleton pattern per Architect feedback"
6. Engineer Worker → You: "Implementation complete"
```

## Complete Orchestration Example

### Scenario: Implement Epic EPC-H-0004

You're orchestrating the Multi-Tool Adapter System epic with multiple roles.

```typescript
// Step 1: Spawn workers for each role
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

// Step 3: Wait for Architect to respond
watch_inbox()
// ... Architect sends message: "Design complete, see ADR-009 section 4"

// Step 4: Verify design (you read the ADR yourself)
// ... looks good

// Step 5: Assign implementation to Engineer
worker_message({
  to_possession_id: 83,
  body: "Implement OpenCodeAdapter wrapper per ARC-H-0057 design. See ADR-009 section 4. Claim tasks OPR-H-0066, OPR-H-0067, OPR-H-0068 in sequence."
})

// Step 6: Engineer works async, sends progress updates
watch_inbox()  // blocks until Engineer reports
// ... "OPR-H-0066 complete"
watch_inbox()
// ... "OPR-H-0067 complete"
watch_inbox()
// ... "OPR-H-0068 complete, ready for testing"

// Step 7: Assign testing
worker_message({
  to_possession_id: 84,
  body: "Test the ToolAdapter protocol and OpenCodeAdapter (TST-H-0069). Engineer reports implementation complete."
})

// Step 8: Tester runs tests, reports results
watch_inbox()
// ... "All tests passing, coverage at 95%"

// Step 9: Check status before terminating
worker_status({ role: "Architect" })
worker_status({ role: "Engineer" })
worker_status({ role: "Tester" })

// Step 10: Gracefully terminate workers
exorcise_minion({ to_possession_id: 82 })
exorcise_minion({ to_possession_id: 83 })
exorcise_minion({ to_possession_id: 84 })
```

## Terminating Workers

Use the `exorcise_minion` tool to end a worker's possession gracefully:

```typescript
exorcise_minion({ to_possession_id: 83 })
```

This:
1. Sends a termination message to the worker's session
2. Worker runs the possession-end skill
3. Worker's possession transitions to EXORCISED
4. Polling process exits cleanly

**Always terminate workers when:**
- Their assigned work is complete
- You're ending your own possession
- Workers are no longer needed
- You need to free up resources

## Best Practices

### Spawning Workers

1. **Spawn only what you need** — Each worker consumes resources
2. **Specify daemons if important** — Helpful for tracking and identification
3. **Track possession IDs** — Store them in your context for easy reference
4. **One worker per role** — Avoid duplicate workers for the same role unless needed

### Messaging Workers

1. **Be explicit** — Workers can't read your mind; provide full context
2. **Reference artifacts** — Point to ADRs, task files, and related docs
3. **Single responsibility** — One message = one task (usually)
4. **Follow up** — Workers may ask questions via messaging
5. **Verify completion** — Check work before assigning next task

### Monitoring Workers

1. **Check status regularly** — Use `worker_status` to track progress
2. **Monitor your inbox** — Workers will message you
3. **Watch for stalls** — If `last_activity` is old, investigate
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
You → Worker: "Implement X"
Worker → You: "Done, but needs review"
You verify, provide feedback
You → Worker: "Fix issue Y"
Worker → You: "Fixed"
```

### Error Handling

**Worker reports blocker:**
```
Worker → You: "Blocked on missing dependency"
You investigate
You → Worker: "Dependency fixed, proceed"
```

**Worker becomes unresponsive:**
```
1. Check worker_status (is it still ACTIVE?)
2. Check last_activity timestamp
3. Send a ping: worker_message({ ..., body: "Status?" })
4. If no response after reasonable wait, exorcise and restart
```

**Tests fail:**
```
Worker → You: "Tests failing with error X"
You → Worker: "Review error and fix root cause"
# Or route to Architect:
You → Architect Worker: "Review test failures for task Y"
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

### Don't: Forget to Terminate

Workers that finish but aren't terminated waste resources and clutter the possession list.

**Always terminate when work is done.**

### Don't: Overload a Single Worker

```typescript
// BAD: One worker for entire epic
worker_message({
  to_possession_id: 83,
  body: "Implement all 10 tasks in EPC-H-0004"
})
```

Instead, use multiple workers or break into sequential messages:

```typescript
// GOOD: Multiple workers
summon_minion({ role: "Engineer", daemon: "hephaestus" })  // Returns: { possession_id: 83 }
summon_minion({ role: "Engineer", daemon: "goibniu" })     // Returns: { possession_id: 84 }

worker_message({ to_possession_id: 83, body: "Tasks 1-3" })
worker_message({ to_possession_id: 84, body: "Tasks 4-6" })
```

### Don't: Ignore Worker Messages

Workers send important updates: completion notifications, blocker reports, questions. Check your inbox.

## Tools Reference

| Tool              | Purpose                               | Arguments                          |
|-------------------|---------------------------------------|------------------------------------|
| `summon_minion`   | Launch background worker              | `{ role, daemon? }`                |
| `worker_message`  | Send task/instruction to worker       | `{ to_possession_id, body }`       |
| `worker_status`   | Check active workers for role         | `{ role }`                         |
| `exorcise_minion` | Gracefully end worker possession      | `{ to_possession_id }`             |
| `watch_inbox`     | Block until a worker message arrives  | `{ timeout? }`                     |

## Troubleshooting

### Worker Won't Start

**Symptoms:** `summon_minion` returns error or worker never becomes ACTIVE

**Solutions:**
1. Check role is valid (Engineer, Architect, Tester, etc.)
2. Verify daemon exists (use `daemon_suggest` if needed)
3. Check system resources (too many workers?)
4. Ask Director to investigate

### Worker Not Responding

**Symptoms:** Messages sent but no response; `worker_status` shows old `last_activity`

**Solutions:**
1. Send status ping: `worker_message({ to_possession_id: 83, body: "Status?" })`
2. Check worker possession — may be blocked on a question
3. Exorcise and restart if truly unresponsive

### Messages Not Received

**Symptoms:** You send messages but worker never acknowledges them

**Solutions:**
1. Verify possession ID is correct (check `worker_status` output)
2. Check message format (must be a string in `body`)
3. Worker may have ended — check possession status

### Worker Doesn't Terminate

**Symptoms:** `exorcise_minion` called but polling process still running

**Solutions:**
1. Wait 30 seconds (graceful shutdown takes time)
2. Check if worker is stuck on a task
3. Ask Director to force-kill if needed

## Summary

As an Admin agent, you orchestrate background desk mode workers to accomplish complex multi-agent workflows:

1. **Spawn** workers with `summon_minion`
2. **Coordinate** via `worker_message` and `watch_inbox`
3. **Monitor** with `worker_status`
4. **Terminate** with `exorcise_minion` when done

Workers run headless, process messages asynchronously, and retain context across invocations. You're the
orchestrator; they're the execution layer.

**Remember:** Workers are invisible to the Director. You manage them autonomously.

## See Also

- **AGENTS.md**: General agent guide and tool reference
- **ADR-013**: Site-nine as OpenCode Integration Platform
- **ADR-014**: Message-driven worker coordination architecture
- **agent-discovery.md**: Finding and coordinating with agents
- **roles/administrator.md**: Administrator role workflows and QA tiers
