# CLI Commands for Agents

This page covers commands primarily used by AI agents during automated workflows.

## Possession Lifecycle

Agent possessions are managed through OpenCode skills, not CLI commands. The `possession-start` skill handles initialization atomically when a new session begins, and `possession-end` handles cleanup. See [OpenCode Integration](../opencode-integration.md) for the full lifecycle description.

The `s9` CLI provides read-only inspection of possessions for reference:

```bash
s9 possession list                    # List all possessions
s9 possession list --active-only      # Only active possessions
s9 possession show <possession-id>    # View possession details
```

## Session Management

The `possession-start` skill renames the OpenCode TUI session automatically as part of initialization. If you need to rename manually:

```bash
s9 possession rename-tui <daemon-name> <Role> --session-id <session-id>
```

To find the correct session ID when multiple sessions are open:

```bash
s9 possession list-opencode-sessions
```

## Task Execution

### Claiming Tasks

```bash
s9 task claim <task-id>
```

Example:

```bash
s9 task claim OPR-H-0065
```

Claims the task for the current active possession.

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

This claims the associated task for the active possession.

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

## Daemon Management

Daemon selection and biography are managed through OpenCode tools, not CLI commands. Use the `daemon_suggest` tool to find available daemon names and `daemon_set_bio` to record a daemon's biography. These are invoked automatically by the `possession-start` skill.

To inspect daemon usage history from the CLI:

```bash
s9 daemon list                        # List all daemons
s9 daemon list --role Engineer        # Filter by role
s9 daemon usage <daemon-name>         # Show usage history for a daemon
```

## Information & Inspection

These shared commands are useful for agents to check status:

```bash
s9 possession show <possession-id>  # View possession details
s9 task show <task-id>              # View task details
s9 task list                        # List all tasks
s9 task list --role Operator        # List tasks for specific role
s9 task mine                        # Show tasks claimed by active possession
s9 handoff list --role Operator --status pending  # Check for pending handoffs
s9 review show <review-id>          # View review details
```

## JSON Output

All commands support `--json` output for programmatic parsing:

```bash
s9 possession show 77 --json
s9 task list --json
s9 handoff list --json
```

## Common Patterns

### Session Start Workflow

Possession initialization is handled atomically by the `possession-start` skill. It runs automatically when `s9 summon <role>` opens a new OpenCode session. The skill:

1. Calls `possession_init` to create a ROLE_PENDING possession
2. Calls `possession_role_record` to set the role
3. Calls `possession_daemon_record` to claim or invent a daemon name (3-day LRU)
4. Calls `possession_rename_session` to rename the TUI session
5. Checks for pending handoffs

You generally do not need to invoke these steps manually.

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
