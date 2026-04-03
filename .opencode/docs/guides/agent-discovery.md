# Agent Discovery Patterns

This guide explains how agents can discover and coordinate with other agents working on the same epic or in specific roles.

## Overview

When working on tasks, you may need help from another agent role (e.g., an Engineer needs an Architect's input). Site-nine provides patterns for discovering which agents are available and how to reach them.

## Discovery Workflow

### Step 1: Check for Active Agents

Use `s9 mission list` with filters to find agents in a specific role or epic:

```bash
# Find all Architects working on a specific epic
s9 mission list --role Architect --epic EPC-H-0004 --json

# Find all active missions for a role
s9 mission list --role Operator --json

# Find all missions on a specific epic
s9 mission list --epic EPC-H-0005 --json
```

**Why use `--json` flag?**
- Enables programmatic parsing of results
- Contains structured data including `desk_mode_active` status
- Can be processed to make decisions in your workflow

### Step 2: Parse JSON for Desk Mode Status

When you receive JSON output, look for missions with `desk_mode_active: true` or `desk_mode_active: 1`:

```json
{
  "missions": [
    {
      "id": 62,
      "persona": "daedalus",
      "role": "Architect",
      "status": "ACTIVE",
      "desk_mode_active": 1,
      "epic_id": "EPC-H-0004"
    }
  ]
}
```

**Desk mode active = Agent is available for async coordination via messaging**

If `desk_mode_active` is `1` (true), the agent is monitoring their inbox and can respond to messages.

### Step 3: Send a Message or Ask Director

**If you found an agent in desk mode:**

Send them a message directly:

```bash
s9 comms send --to-mission 62 \
  --subject "Question about ToolAdapter design" \
  --body "Should we use singleton or factory pattern for the registry?"
```

**If no agent is available (no desk mode active):**

Ask the Director in the OpenCode chat:

```
No Architect currently available in desk mode for EPC-H-0004. 
Should I wait for a response, or would you like to summon an Architect?
```

The Director can then:
- Summon a new agent: `/summon architect`
- Tell you to wait for an existing agent to enter desk mode
- Provide guidance directly

## Complete Example Workflows

### Example 1: Engineer Needs Architect Input

```bash
# 1. Check for available Architects on the epic
s9 mission list --role Architect --epic EPC-H-0004 --json

# 2. Parse output - found mission #62 with desk_mode_active: 1

# 3. Send message
s9 comms send --to-mission 62 \
  --subject "Registry pattern decision needed" \
  --body "I'm implementing the ToolRegistry (OPR-H-0067). Should this be a singleton or allow multiple instances? Context: OpenCode might have multiple adapters loaded."

# 4. Continue with other work while waiting for response

# 5. Check inbox later
s9 comms inbox

# 6. Read reply when it arrives
s9 comms show MSG-M-0205
```

### Example 2: No Agent Available

```bash
# 1. Check for available Testers
s9 mission list --role Tester --epic EPC-H-0004 --json

# 2. Parse output - no missions found or all have desk_mode_active: 0

# 3. Ask Director in chat
```

**In OpenCode chat:**
```
I'm ready to start testing (TST-H-0069) but no Tester is currently available 
in desk mode for EPC-H-0004. Should I wait or would you like to summon a Tester?
```

### Example 3: Broadcasting to All Agents in a Role

Sometimes you need to ask a question to anyone in a role, not a specific mission:

```bash
# Send to all Operators
s9 comms send --to-role Operator \
  --subject "Best practice question: Error handling in CLI" \
  --body "What's our preferred pattern for error handling in s9 commands? I see both raise and sys.exit patterns in the codebase."
```

**Note:** When sending to a role, all active missions in that role will receive the message in their inbox.

## When to Use Discovery vs. Director

### Use Discovery + Messaging When:
- You need technical input from a specific role
- The question can wait for an async response
- You're coordinating on epic-level work
- Multiple agents might benefit from the discussion

### Ask Director Directly When:
- You need immediate guidance
- You're blocked and can't proceed
- You need another agent summoned
- The decision affects project direction (not just technical details)

## Integration with Messaging

Discovery patterns work with the message-driven coordination system:

- **Worker coordination** - Admin spawns workers and assigns work via messages
- **Discovery + Messaging** - For coordination while both agents are actively working  
- **Director chat** - For immediate needs and summoning

**See:** ADR-014 for complete message-driven coordination architecture.

## Director CLI Reference

These commands are for the **Director (human) only**. Agents use tools instead.

```bash
# Discovery commands
s9 mission list --role <Role> --json
s9 mission list --epic <EPIC-ID> --json
s9 mission list --role <Role> --epic <EPIC-ID> --json

# Messaging commands
s9 comms send --to-mission <ID> --subject "..." --body "..."
s9 comms send --to-role <Role> --subject "..." --body "..."
s9 comms inbox
s9 comms show <MSG-ID>
s9 comms reply <MSG-ID> "..."

# Desk workers (Director spawns headless workers)
s9 summon <role> --desk
```

## Tips for Effective Discovery

1. **Always check before asking Director** - Discovery is more efficient for finding existing help
2. **Use --json for parsing** - Enables automated decision-making in your workflow
3. **Check desk_mode_active** - Only message agents who are actively monitoring
4. **Be specific in messages** - Include context, epic ID, task ID, and clear questions
5. **Follow up** - Check your inbox periodically if you're expecting a response

## See Also

- **ADR-009** (lines 238-250, 503-531): Agent coordination patterns and discovery workflow
- **ADR-014**: Message-Driven Coordination Architecture
- **Communication Channels**: See mission-start skill Step 7.5 for channel usage patterns
- **Messaging System**: See ADR-008 for complete messaging system design
- **Desk Mode**: `.opencode/docs/guides/desk-mode-orchestration.md`
