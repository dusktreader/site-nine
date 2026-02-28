# Epic Mission Workflows and Desk Mode

This guide explains how to work on epic-scoped missions and use desk mode for agent coordination.

## Overview

**Epic missions** are long-running missions where an agent works through multiple tasks within a single epic. Instead of ending the mission after each task, the agent continues claiming tasks until the epic is complete or they choose to end the mission.

**Desk mode** is a state where your mission actively monitors for incoming messages from other agents, enabling async coordination while you work.

## Epic Mission Workflow

### Starting an Epic Mission

When starting a mission for epic work, use the `--epic` flag:

```bash
s9 mission start <persona-name> --role <Role> --epic <EPIC-ID>
```

**Example:**
```bash
s9 mission start daedalus --role Architect --epic EPC-H-0004
```

This scopes your mission to the epic and enables:
- Using `s9 task next` to auto-claim the next task in the epic
- Desk mode coordination with other agents on the same epic
- Mission continuity across multiple related tasks

### Working Through Epic Tasks

#### Option 1: Manual Task Claiming

Claim specific tasks one at a time:

```bash
# Claim first task
s9 task claim ARC-H-0057

# Work on task...

# Close task when done
s9 task close ARC-H-0057 --status COMPLETE

# Claim next task manually
s9 task claim ARC-H-0058
```

#### Option 2: Using `s9 task next` (Recommended)

Let the system auto-claim the next TODO task for your role in your epic:

```bash
# Claim first task
s9 task claim ARC-H-0057

# Work and complete...
s9 task close ARC-H-0057 --status COMPLETE

# Auto-claim next task in the epic
s9 task next
# This finds the next TODO task matching:
# - mission.epic_id (your epic)
# - mission.role (your role)
# - status = TODO
```

**Benefits of `s9 task next`:**
- No need to look up task IDs
- Automatically prioritizes tasks
- Ensures you stay within your epic scope
- Faster workflow for sequential work

### When to End an Epic Mission

End your epic mission when:

1. **Epic is complete** - All tasks for your role in the epic are done
2. **Context switch needed** - You need to work on a different epic
3. **Extended break** - You're stopping work for an extended period
4. **Handoff required** - You need to hand off remaining work to another agent

**To end the mission:**
```bash
s9 mission end <mission-id>
```

**Important:** Don't end the mission between every task! Epic missions are designed for continuity.

## Desk Mode Usage

### What is Desk Mode?

Desk mode is a state where your mission:
- Actively monitors for incoming messages
- Displays periodic "Checking comms..." status updates
- Allows other agents to discover you're available
- Enables async coordination without blocking your work

**Think of it as:** "I'm at my desk and available to answer questions while I work"

### When to Use Desk Mode

**Use desk mode when:**
- Working on an epic with multiple agents
- Available to answer questions from other roles
- Expecting coordination or input from other agents
- Working asynchronously and can respond to messages periodically

**Don't use desk mode when:**
- Doing focused, heads-down work requiring no interruption
- Working on a standalone task with no coordination needs
- About to end your mission
- Stepping away for an extended break

### Starting Desk Mode

**For epic-scoped missions (recommended):**
```bash
# Your mission is already scoped to an epic
s9 comms desk start
```

The system automatically infers the epic from your mission's `epic_id`.

**For general availability (all epics):**
```bash
# Mission not scoped to an epic
s9 comms desk start
```

This makes you discoverable for questions from any epic.

**Explicit epic specification:**
```bash
# Optional: explicitly specify epic (must match mission.epic_id)
s9 comms desk start --epic EPC-H-0004
```

### What Happens in Desk Mode

When you start desk mode, you'll see periodic status updates:

```
Desk mode active. Press Ctrl+C to exit.
Checking comms... Found 2 new message(s)!

From: Mission #85 (hephaestus - Engineer)
Subject: Question about ToolAdapter registry
Preview: Should we use singleton or factory pattern for...
ID: MSG-M-0341

From: Mission #92 (athena - Operator)  
Subject: Implementation question
Preview: I'm implementing the OpenCodeAdapter wrapper...
ID: MSG-M-0342

[Agent can respond to Director or work between checks]

[30s later]
Checking comms... No new messages. (0 unread)

[30s later]
Checking comms... No new messages. (0 unread)
```

**Key features:**
- Runs in foreground with 30-second check intervals
- Shows you're actively monitoring (visible to Director)
- You can still chat with Director between checks
- Exit with `s9 comms desk stop` or Ctrl+C
- Automatically disables when mission ends

### Responding to Messages in Desk Mode

When you see new messages, you can:

1. **Read the full message:**
   ```bash
   s9 comms show MSG-M-0341
   ```

2. **Reply directly:**
   ```bash
   s9 comms reply MSG-M-0341 "Use singleton pattern for thread safety. The registry should be a global instance accessible from any adapter."
   ```

3. **Continue desk mode:**
   - Desk mode continues running in the background
   - Or restart it: `s9 comms desk start`

### Stopping Desk Mode

**Option 1: Ctrl+C** (graceful exit)
```
^C
Desk mode stopped.
```

**Option 2: Stop command**
```bash
s9 comms desk stop
```

**Automatic stop:**
- Desk mode automatically disables when you end your mission
- No need to manually stop before `s9 mission end`

## Complete Epic Mission Example

Here's a complete workflow showing epic missions + desk mode:

```bash
# 1. Start epic-scoped mission
s9 mission start daedalus --role Architect --epic EPC-H-0004

# 2. Enable desk mode for coordination
s9 comms desk start

# 3. Claim first task
s9 task claim ARC-H-0057

# 4. Work on task while monitoring messages
#    (desk mode runs, shows "Checking comms..." every 30s)

# 5. See a message, temporarily stop desk mode to respond
^C
s9 comms show MSG-M-0341
s9 comms reply MSG-M-0341 "Use singleton pattern..."

# 6. Resume desk mode
s9 comms desk start

# 7. Complete first task
s9 task close ARC-H-0057 --status COMPLETE

# 8. Auto-claim next task
s9 task next
# Claimed: ARC-H-0058

# 9. Continue working through tasks...

# 10. When epic work is complete
^C  # Stop desk mode
s9 mission end <mission-id>
```

## Discovery: Finding Agents in Desk Mode

Other agents can discover you're available using:

```bash
# Find all Architects on your epic
s9 mission list --role Architect --epic EPC-H-0004 --json
```

**JSON output includes:**
```json
{
  "missions": [
    {
      "id": 62,
      "persona": "daedalus",
      "role": "Architect",
      "desk_mode_active": 1,
      "epic_id": "EPC-H-0004"
    }
  ]
}
```

Agents look for `desk_mode_active: 1` to know you're monitoring messages.

**See:** `agent-discovery.md` for complete discovery patterns.

## Best Practices

### Epic Missions

1. **Start with epic scope** - Use `--epic` flag from the beginning
2. **Use `s9 task next`** - More efficient than manual claiming
3. **Don't end between tasks** - Keep mission alive for continuity
4. **Update mission file** - Document progress as you complete each task
5. **Send heartbeats** - Run `s9 mission heartbeat` periodically

### Desk Mode

1. **Enable early** - Start desk mode at beginning of epic work
2. **Keep it running** - Let it monitor while you work
3. **Respond promptly** - Check messages when you see notifications
4. **Use Ctrl+C liberally** - Easy to stop/restart as needed
5. **Don't forget to stop** - Use Ctrl+C when taking breaks

### Coordination

1. **Check for agents first** - Use discovery before asking Director
2. **Be specific in messages** - Include epic ID, task ID, context
3. **Thread conversations** - Reply to messages to maintain context
4. **Escalate when needed** - Ask Director if no agents available
5. **Document decisions** - Record coordination outcomes in mission file

## Command Reference

### Epic Mission Commands

```bash
# Start epic-scoped mission
s9 mission start <persona> --role <Role> --epic <EPIC-ID>

# Auto-claim next task in epic
s9 task next

# End mission
s9 mission end <mission-id>
```

### Desk Mode Commands

```bash
# Start desk mode (epic inferred from mission)
s9 comms desk start

# Start with explicit epic
s9 comms desk start --epic <EPIC-ID>

# Stop desk mode
s9 comms desk stop
# Or: Ctrl+C
```

### Discovery Commands

```bash
# Find agents by role and epic
s9 mission list --role <Role> --epic <EPIC-ID> --json

# Check inbox
s9 comms inbox

# Read message
s9 comms show <MSG-ID>

# Reply to message
s9 comms reply <MSG-ID> "response text"
```

## Troubleshooting

### "Mission not scoped to epic" error

**Problem:** You tried `s9 comms desk --epic EPC-H-0004` but your mission isn't epic-scoped.

**Solution:** 
- Either use `s9 comms desk` without `--epic` (general availability)
- Or end mission and restart with `--epic` flag

### Can't find other agents

**Problem:** `s9 mission list --role X --epic Y` returns no results.

**Solution:**
- Check if agents are active: `s9 mission list --role X`
- Ask Director to summon an agent if needed
- Verify epic ID is correct

### Desk mode not showing messages

**Problem:** Other agents sent messages but you don't see them.

**Solution:**
- Check `s9 comms inbox` manually
- Verify desk mode is actually running (should see "Checking comms..." output)
- Restart desk mode: Ctrl+C then `s9 comms desk start`

## See Also

- **ADR-009** (lines 99-115, 165-180, 533-554): Epic missions and desk mode design
- **Agent Discovery**: `agent-discovery.md` for finding available agents
- **Communication Channels**: session-start skill Step 7.5
- **Messaging System**: ADR-008 for complete messaging design
