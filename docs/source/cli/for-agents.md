# CLI Commands for Agents

This page covers commands primarily used by AI agents during automated workflows.

## Mission Lifecycle

### Starting a Mission

```bash
s9 mission start <persona-name> --role <Role> --task "<objective>"
```

Example:

```bash
s9 mission start cronos --role Operator --task "System maintenance and improvements"
```

### Displaying Available Roles

```bash
s9 mission roles
```

Shows formatted list of all available agent roles and their responsibilities. Used during session initialization.

### Updating Mission Metadata

```bash
s9 mission update <mission-id> --task "<new-objective>"
s9 mission update <mission-id> --role <NewRole>
```

Example:

```bash
s9 mission update 77 --task "Focus on database optimization"
```

### Ending a Mission

```bash
s9 mission end <mission-id>
```

Example:

```bash
s9 mission end 77
```

## Session Management

### Generate Session UUID

```bash
s9 mission generate-session-uuid
```

Outputs a UUID that OpenCode captures in session data. This allows reliable session detection when multiple sessions are active.

Usage pattern:
1. Agent calls `s9 mission generate-session-uuid`
2. OpenCode captures the UUID in this session's data
3. Agent captures the UUID from output
4. Agent calls `s9 mission rename-tui` with the UUID

### Rename OpenCode Session

```bash
s9 mission rename-tui <persona-name> <Role> --uuid-marker <uuid>
```

Example:

```bash
s9 mission rename-tui cronos Operator --uuid-marker session-marker-abc123
```

This renames the current OpenCode TUI session to match the agent's identity.

## Task Execution

### Claiming Tasks

```bash
s9 task claim <task-id>
```

Example:

```bash
s9 task claim OPR-H-0065
```

Claims the task for the current active mission.

### Updating Task Status

```bash
s9 task update <task-id> --status <STATUS>
s9 task update <task-id> --status <STATUS> --notes "<progress-notes>"
```

Valid statuses: TODO, UNDERWAY, PAUSED, BLOCKED, REVIEW, COMPLETE, ABORTED

Example:

```bash
s9 task update OPR-H-0065 --status UNDERWAY
s9 task update OPR-H-0065 --status REVIEW --notes "Ready for code review"
```

### Closing Tasks

```bash
s9 task close <task-id>
s9 task close <task-id> --status <STATUS> --notes "<closing-notes>"
```

Example:

```bash
s9 task close OPR-H-0065 --status COMPLETE --notes "Implemented rate limiting with Redis backend"
```

## Collaboration

### Creating Handoffs

```bash
s9 handoff create \
  --task <task-id> \
  --to-role <Role> \
  --reason "<handoff-reason>"
```

Example:

```bash
s9 handoff create \
  --task ARC-H-0057 \
  --to-role Operator \
  --reason "Design complete, ready for implementation"
```

### Accepting Handoffs

```bash
s9 handoff accept <handoff-id>
```

Example:

```bash
s9 handoff accept 3
```

This claims the associated task for the active mission.

### Completing Handoffs

```bash
s9 handoff complete <handoff-id>
```

Example:

```bash
s9 handoff complete 3
```

Marks the handoff as complete.

## Review Workflow

### Creating Review Requests

```bash
s9 review create \
  --task <task-id> \
  --title "<review-title>" \
  --type <review-type>
```

Valid review types: code, design, security, documentation

Example:

```bash
s9 review create \
  --task OPR-H-0065 \
  --title "Review rate limiting implementation" \
  --type code
```

The task's status is automatically changed to REVIEW.

## Persona Management

### Suggesting Persona Names

```bash
s9 name suggest <Role> --count <number>
```

Example:

```bash
s9 name suggest Operator --count 3
```

Returns unused persona names for the specified role.

### Setting Persona Biography

```bash
s9 name set-bio <persona-name> "<biography-text>"
```

Example:

```bash
s9 name set-bio cronos "I am Cronos, the Titan of time itself..."
```

## Information & Inspection

These shared commands are useful for agents to check status:

```bash
s9 mission show <mission-id>    # View mission details
s9 task show <task-id>          # View task details
s9 task list                    # List all tasks
s9 task list --role Operator    # List tasks for specific role
s9 task mine                    # Show tasks claimed by active mission
s9 handoff list --role Operator --status pending  # Check for pending handoffs
s9 review show <review-id>      # View review details
```

## JSON Output

All commands support `--json` output for programmatic parsing:

```bash
s9 mission show 77 --json
s9 task list --json
s9 handoff list --json
```

## Common Patterns

### Session Start Workflow

```bash
# 1. Get role suggestions
s9 mission roles

# 2. Get persona suggestion
s9 name suggest Operator --count 3

# 3. Start mission
s9 mission start cronos --role Operator --task "System improvements"

# 4. Generate session UUID
s9 mission generate-session-uuid

# 5. Rename OpenCode session
s9 mission rename-tui cronos Operator --uuid-marker <captured-uuid>

# 6. Check for pending handoffs
s9 handoff list --role Operator --status pending
```

### Task Execution Workflow

```bash
# 1. Claim task
s9 task claim OPR-H-0065

# 2. Update to in-progress
s9 task update OPR-H-0065 --status UNDERWAY

# 3. Work on task...

# 4. Update with progress
s9 task update OPR-H-0065 --status UNDERWAY --notes "Implemented Redis connection pool"

# 5. Close when complete
s9 task close OPR-H-0065 --status COMPLETE --notes "Rate limiting fully implemented"
```

### Handoff Workflow

```bash
# When work needs to be passed to another role:
s9 handoff create \
  --task ARC-H-0057 \
  --to-role Operator \
  --reason "Architecture design complete, ready for implementation"

# Close your task
s9 task close ARC-H-0057 --status COMPLETE
```

## Next Steps

- See [CLI Overview](overview.md) for command categorization
- See [Complete Reference](complete.md) for detailed command documentation
- See [Working with Agents](../agents/overview.md) for agent concepts
