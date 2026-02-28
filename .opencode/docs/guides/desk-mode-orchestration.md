# Desk Mode Orchestration Guide

This guide is for **Admin/Operator agents** who need to orchestrate background desk mode workers to accomplish complex
multi-agent workflows.

## Overview

Desk mode workers are background agents that run in headless OpenCode sessions and process tasks asynchronously. As an
Admin agent, you can summon, coordinate, and terminate these workers using custom tools.

**Architecture:**

```
Director
  └─ summons → Admin Agent (you, interactive session)
                 ├─ summons → Engineer (desk mode, background)
                 ├─ summons → Architect (desk mode, background)
                 └─ coordinates via messaging system
```

Workers are invisible to the Director - they're infrastructure you manage.

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

## Summoning Workers

### Using worker_summon Tool

Use the `worker_summon` tool to launch background workers:

```typescript
worker_summon({ 
  role: "engineer",
  persona: "hephaestus"  // optional
})
```

This creates a background Python process that:
1. Launches an OpenCode session with the mission-start skill
2. Initializes the worker's mission in desk mode
3. Enters a polling loop, checking for messages
4. Processes each message via `opencode run --session <id> "<message>"`
5. Auto-suspends/resumes between messages to preserve context

**The worker runs headless** - no UI, no Director interaction. It only responds to messages you send.

### Worker Lifecycle

Each worker:
- Starts with a fresh mission
- Retains full conversational context across messages
- Auto-suspends when idle (no active OpenCode session consuming resources)
- Resumes when you send the next message
- Can accumulate context over its lifetime (remembers prior work)
- Ends gracefully when you terminate it

**Note:** Workers don't need heartbeats - the polling process keeps them alive.

## Coordinating Workers

### Sending Work to Workers

Use the `worker_message` tool to send tasks/instructions:

```typescript
worker_message({
  session_id: "<worker-session-id>",
  message: "Implement the ToolAdapter protocol (task ARC-H-0057). See ADR-009 section 4 for the design specification."
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
  session_id: "abc123",
  message: "Claim and complete task ENG-H-0150: Implement task_create tool"
})

// Complex coordination
worker_message({
  session_id: "abc123",
  message: "Implement the ToolRegistry following the design in ADR-009. Run tests when done and report results."
})

// Follow-up work
worker_message({
  session_id: "abc123",
  message: "The tests failed with ModuleNotFoundError. Check the import statements and fix the issue."
})
```

### Checking Worker Status

Use the `worker_status` tool to see active workers for a role:

```typescript
worker_status({ role: "engineer" })
```

Returns:
```json
{
  "workers": [
    {
      "mission_id": 125,
      "session_id": "abc123",
      "persona": "hephaestus",
      "codename": "void-vortex",
      "status": "ACTIVE",
      "last_activity": "2026-02-19T00:15:00Z",
      "current_task": "ENG-H-0150"
    }
  ]
}
```

**Use this to:**
- Track which workers are active
- Get session IDs for sending messages
- Monitor worker progress
- Verify workers haven't stalled

## Message-Driven Workflow

Workers communicate back to you via the messaging system:

### Receiving Worker Responses

Workers can send you messages:

```python
# Worker sends completion notification
comms_send({
  to_session: "<your-session-id>",
  subject: "Task ENG-H-0150 complete",
  body: "Implemented task_create tool with full validation. All tests passing."
})
```

Check your inbox periodically:

```typescript
// Check for worker responses
mission_inbox()
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

**Or:**

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
// Step 1: Summon workers for each role
worker_summon({ role: "architect", persona: "daedalus" })
// Returns: { session_id: "arch-123", mission_id: 82, codename: "swift-forge" }

worker_summon({ role: "engineer", persona: "hephaestus" })
// Returns: { session_id: "eng-456", mission_id: 83, codename: "iron-nexus" }

worker_summon({ role: "tester", persona: "maeve" })
// Returns: { session_id: "test-789", mission_id: 84, codename: "crystal-wind" }

// Step 2: Architect designs the protocol
worker_message({
  session_id: "arch-123",
  message: "Design the ToolAdapter protocol and OpenCodeAdapter implementation (ARC-H-0057). Document in ADR format."
})

// Step 3: Wait for Architect to respond via messaging
// ... Architect sends message: "Design complete, see ADR-009 section 4"

// Step 4: Verify design (you read the ADR yourself)
// ... looks good

// Step 5: Assign implementation to Engineer
worker_message({
  session_id: "eng-456",
  message: "Implement OpenCodeAdapter wrapper per ARC-H-0057 design. See ADR-009 section 4. Claim tasks OPR-H-0066, OPR-H-0067, OPR-H-0068 in sequence."
})

// Step 6: Engineer works async, sends progress updates
// ... "OPR-H-0066 complete"
// ... "OPR-H-0067 complete"
// ... "OPR-H-0068 complete, ready for testing"

// Step 7: Assign testing
worker_message({
  session_id: "test-789",
  message: "Test the ToolAdapter protocol and OpenCodeAdapter (TST-H-0069). Engineer reports implementation complete."
})

// Step 8: Tester runs tests, reports results
// ... "All tests passing, coverage at 95%"

// Step 9: Check status before terminating
worker_status({ role: "architect" })
worker_status({ role: "engineer" })
worker_status({ role: "tester" })

// Step 10: Gracefully terminate workers
worker_terminate({ session_id: "arch-123" })
worker_terminate({ session_id: "eng-456" })
worker_terminate({ session_id: "test-789" })
```

## Terminating Workers

### Graceful Termination

Use the `worker_terminate` tool to end a worker's mission:

```typescript
worker_terminate({ session_id: "abc123" })
```

This:
1. Sends a termination message to the worker's session
2. Worker runs the mission-end skill
3. Worker's mission transitions to COMPLETE
4. Polling process exits cleanly

**Always terminate workers when:**
- Their assigned work is complete
- You're ending your own mission
- Workers are no longer needed
- You need to free up resources

### Force Termination

If a worker becomes unresponsive, you can force-terminate:

```bash
# Director command (you ask Director to run this)
s9 worker kill <session-id>
```

**Use sparingly** - this doesn't run mission-end, leaving the mission in an inconsistent state.

## Best Practices

### Summoning Workers

1. **Summon only what you need** - Each worker consumes resources
2. **Specify personas if important** - Helpful for tracking and identification
3. **Track session IDs** - Store them in your context for easy reference
4. **One worker per role** - Avoid duplicate workers for the same role unless needed

### Messaging Workers

1. **Be explicit** - Workers can't read your mind; provide full context
2. **Reference artifacts** - Point to ADRs, task files, mission logs
3. **Single responsibility** - One message = one task (usually)
4. **Follow up** - Workers may ask questions via messaging
5. **Verify completion** - Check work before assigning next task

### Monitoring Workers

1. **Check status regularly** - Use worker_status to track progress
2. **Monitor your inbox** - Workers will message you
3. **Watch for stalls** - If last_activity is old, investigate
4. **Review work incrementally** - Don't wait until everything's done

### Coordination Patterns

1. **Sequential dependencies:**
   ```
   Architect designs → Engineer implements → Tester validates
   ```

2. **Parallel execution:**
   ```
   Engineer A: task 1
   Engineer B: task 2  } all at once
   Engineer C: task 3
   ```

3. **Iterative refinement:**
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
2. Check mission last_activity (when did it last respond?)
3. Try sending a ping message: "Status check?"
4. If no response in reasonable time, terminate and restart
```

**Tests fail:**
```
Worker → You: "Tests failing with error X"
You → Worker: "Review error and fix root cause"
# Or delegate to another worker:
You → Architect Worker: "Review test failures for task Y"
```

## Orchestration Anti-Patterns

### ❌ Don't: Micromanage

```typescript
// BAD: Too granular
worker_message({ session_id: "abc", message: "Read file X" })
worker_message({ session_id: "abc", message: "Now edit line 42" })
worker_message({ session_id: "abc", message: "Now run tests" })
```

**Instead:** Give complete, self-contained instructions

```typescript
// GOOD: Clear, complete task
worker_message({ 
  session_id: "abc", 
  message: "Implement ToolAdapter protocol (ARC-H-0057). Follow the design in ADR-009, implement the interface, run tests, report results."
})
```

### ❌ Don't: Forget to Terminate

Workers that finish but aren't terminated:
- Waste resources (polling process still running)
- Clutter mission list
- May confuse status tracking

**Always terminate when work is done.**

### ❌ Don't: Overload a Single Worker

```typescript
// BAD: One worker for entire epic
worker_message({ 
  session_id: "abc",
  message: "Implement all 10 tasks in EPC-H-0004"
})
```

**Instead:** Use multiple workers or break into sequential messages

```typescript
// GOOD: Multiple workers
worker_summon({ role: "engineer", persona: "hephaestus" })  // worker 1
worker_summon({ role: "engineer", persona: "goibniu" })     // worker 2

worker_message({ session_id: "worker1", message: "Tasks 1-3" })
worker_message({ session_id: "worker2", message: "Tasks 4-6" })
```

### ❌ Don't: Ignore Worker Messages

Workers may send important updates:
- Completion notifications
- Blocker reports
- Questions needing answers

**Check your inbox regularly.**

## Tools Reference

| Tool | Purpose | Arguments |
|------|---------|-----------|
| `worker_summon` | Launch background worker | `{ role, persona? }` |
| `worker_message` | Send task/instruction to worker | `{ session_id, message }` |
| `worker_status` | Check active workers for role | `{ role }` |
| `worker_terminate` | Gracefully end worker mission | `{ session_id }` |
| `mission_inbox` | Check your inbox for messages | (none) |
| `comms_send` | Send message to worker | `{ to_session, subject, body }` |

## Troubleshooting

### Worker Won't Start

**Symptoms:** worker_summon returns error or worker never becomes ACTIVE

**Solutions:**
1. Check role is valid (Operator, Engineer, Architect, etc.)
2. Verify persona exists (use persona_suggest if needed)
3. Check system resources (too many workers?)
4. Ask Director to investigate

### Worker Not Responding

**Symptoms:** Messages sent but no response, worker_status shows old last_activity

**Solutions:**
1. Send status ping: `worker_message({ session_id: "...", message: "Status?" })`
2. Check worker mission: may be blocked on a question
3. Terminate and restart if truly unresponsive

### Messages Not Received

**Symptoms:** You send messages but worker never gets them

**Solutions:**
1. Verify session_id is correct (check worker_status output)
2. Check message format (must be string)
3. Worker may have ended - check mission status

### Worker Doesn't Terminate

**Symptoms:** worker_terminate called but polling process still running

**Solutions:**
1. Wait 30 seconds (graceful shutdown takes time)
2. Check if worker is stuck on a task
3. Ask Director to force-kill if needed

## Summary

As an Admin/Operator agent, you orchestrate background desk mode workers to accomplish complex multi-agent workflows:

1. **Summon** workers with worker_summon
2. **Coordinate** via worker_message and messaging system
3. **Monitor** with worker_status and your inbox
4. **Terminate** with worker_terminate when done

Workers run headless, process messages asynchronously, and retain context across invocations. You're the orchestrator -
they're the execution layer.

**Remember:** Workers are invisible to the Director. You manage them autonomously.

## See Also

- **AGENTS.md**: General agent guide
- **ADR-013** (lines 410-464): Desk mode worker architecture
- **epic-missions-and-desk-mode.md**: Desk mode for interactive agents
- **agent-discovery.md**: Finding and coordinating with agents
