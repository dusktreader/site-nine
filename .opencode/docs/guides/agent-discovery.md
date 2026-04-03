# Agent Discovery Patterns

This guide explains how agents can discover and coordinate with other agents working on the same epic or in
specific roles.

## Overview

When you need help from another role (e.g., an Engineer needs Architect input), site-nine provides patterns
for discovering available agents and reaching them. The two main channels are:

1. **`worker_status`** — Find active desk-mode workers by role
2. **Director chat** — Ask the Director to summon an agent if none are available

## Discovery Workflow

### Step 1: Check for Active Workers

Use `worker_status` to find active workers for a role:

```typescript
worker_status({ role: "Architect" })
```

Returns:
```json
{
  "workers": [
    {
      "possession_id": 62,
      "daemon": "daedalus",
      "role": "Architect",
      "status": "ACTIVE",
      "last_activity": "2026-02-19T00:15:00Z"
    }
  ]
}
```

### Step 2: Message or Ask Director

**If a worker is available:**

Send them a message directly:

```typescript
worker_message({
  to_possession_id: 62,
  body: "Question about ToolAdapter design (OPR-H-0067): should we use singleton or factory pattern for the registry? Context: OpenCode might load multiple adapters."
})
```

**If no worker is available:**

Ask the Director in OpenCode chat:

```
No Architect is currently available in desk mode for EPC-H-0004.
Should I wait, or would you like to summon one?
```

The Director can then summon a new agent or provide guidance directly.

## Complete Example Workflows

### Example 1: Engineer Needs Architect Input

```typescript
// 1. Check for available Architects
worker_status({ role: "Architect" })
// Returns: possession_id: 62, daemon: "daedalus", ACTIVE

// 2. Send message
worker_message({
  to_possession_id: 62,
  body: "I'm implementing ToolRegistry (OPR-H-0067). Should it be a singleton or support multiple instances? OpenCode might have multiple adapters loaded."
})

// 3. Continue with other work while waiting

// 4. Watch for response
watch_inbox()
// Architect replies: "Use singleton — one registry per process, adapters register on load."
```

### Example 2: No Agent Available

```typescript
// 1. Check for available Testers
worker_status({ role: "Tester" })
// Returns: empty workers array
```

In OpenCode chat:
```
I'm ready to start TST-H-0069 but no Tester is in desk mode for EPC-H-0004.
Should I wait or would you like to summon a Tester?
```

### Example 3: Admin Spawning a Worker on Demand

If you're an Admin and need a role that isn't available, spawn it yourself:

```typescript
worker_status({ role: "Tester" })
// Returns: empty

const tst = summon_minion({ role: "Tester" })
worker_message({
  to_possession_id: tst.possession_id,
  body: "Validate ENG-H-0150 rate limiting implementation. Run make qa and report results."
})
```

## When to Use Discovery vs. Director

**Use `worker_status` + messaging when:**
- You need technical input and the question can wait for async response
- You're coordinating on epic-level work
- Multiple workers might be relevant

**Ask Director directly when:**
- You need immediate guidance
- You're blocked and can't proceed
- You need another agent summoned (if you're not an Admin)
- The decision affects project direction

**Spawn a worker yourself (Admin only) when:**
- The Director has delegated orchestration to you
- You have a concrete task ready to assign

## Tips for Effective Discovery

1. **Check before asking Director** — `worker_status` is faster than a chat interruption
2. **Be specific in messages** — Include task IDs, epic context, and a clear question
3. **Don't block unnecessarily** — Use `watch_inbox` after sending; continue other work in the meantime
4. **One question per message** — Don't bundle multiple questions; workers answer and report back per message

## Director CLI Reference

These commands are for the **Director (human) only**. Agents use tools instead.

```bash
# View active possessions
s9 possession list --role Architect
s9 possession list --epic EPC-H-0004

# Summon a desk-mode worker
s9 summon <role> --desk

# Messaging
s9 comms inbox
s9 comms show <MSG-ID>
```

## See Also

- **admin-orchestration.md**: Practical Admin guide for spawning and coordinating workers
- **desk-mode-orchestration.md**: Reference guide for worker lifecycle management
- **ADR-014**: Message-driven coordination architecture
- **ADR-008**: Agent messaging system design
