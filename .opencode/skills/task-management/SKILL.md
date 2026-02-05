---
name: task-management
description: Overview and quick reference for the s9 task management system
license: MIT
compatibility: opencode
metadata:
  audience: all-agents
  workflow: task-overview
---

## Important: CLI Tool Usage

**CRITICAL:** This project uses the `s9` CLI executable throughout these instructions.
- **CLI executable:** `s9` (use in bash commands)
- **Python module:** `site_nine` (use in Python imports: `from site_nine import ...`)

All commands in this skill use the `s9` executable via bash. You should NOT attempt to import an `s9` module in Python code.

## What I Do

I provide an overview of the s9 task management system and quick reference to specialized skills for specific workflows. Use this skill to understand the task lifecycle and find the right skill for your needs.

## Task Management System

The `s9` CLI provides unified management of tasks, agent sessions, and daemon names:

```bash
# Task commands
s9 task create --title "..." --objective "..." --role Engineer --priority HIGH
s9 task list --role Engineer --active-only
s9 task claim TASK_ID --agent-name "YourName"
s9 task update TASK_ID --notes "..." --actual-hours X.X
s9 task close TASK_ID --status COMPLETE --notes "..."
s9 task show TASK_ID
s9 task report --format markdown

# See also: mission and persona commands
s9 mission start <name> --role <Role>
s9 persona suggest <Role>
```

**Database:** `.opencode/data/project.db`

## Specialized Skills

Use these focused skills for specific task workflows:

### task-create
**Use when:** Creating new tasks  
**Covers:** Task creation, ID format, priorities, roles, categories, dependencies  
**Load with:** `skill task-create`

### task-query
**Use when:** Finding work, listing tasks, generating reports  
**Covers:** Filtering by status/role/priority, viewing details, reports  
**Load with:** `skill task-query`

### task-claim
**Use when:** Taking ownership of a task  
**Covers:** Claiming tasks, agent names, concurrency protection  
**Load with:** `skill task-claim`

### task-update
**Use when:** Tracking progress on a task  
**Covers:** Progress notes, time tracking, status changes  
**Load with:** `skill task-update`

### task-close
**Use when:** Completing, pausing, or blocking tasks  
**Covers:** COMPLETE, PAUSED, BLOCKED, ABORTED statuses, resuming tasks  
**Load with:** `skill task-close`

## Task Lifecycle

```
TODO (created)
  ↓
  [task-query: find work]
  ↓
  [task-claim: take ownership] → UNDERWAY
  ↓
  [task-update: track progress]
  ↓
  [task-close] → COMPLETE
                 PAUSED
                 BLOCKED
                 ABORTED
```

## Quick Reference Commands

### Finding Work
```bash
# Find available work for your role
s9 task list --role YourRole --status TODO

# Find high-priority work
s9 task list --priority CRITICAL,HIGH --status TODO

# See what you're working on
s9 task list --agent "YourName" --status UNDERWAY
```

### Working on Tasks
```bash
# Claim a task
s9 task claim TASK_ID --agent-name "YourName"

# Update progress
s9 task update TASK_ID --notes "Progress made" --actual-hours 2.0

# Close when done
s9 task close TASK_ID --status COMPLETE --notes "Task complete"
```

### Creating Tasks
```bash
# Create new task (ID auto-generated)
s9 task create \
  --title "Task Title" \
  --objective "What it accomplishes" \
  --role Engineer \
  --priority HIGH \
  --category "Category"
```

### Viewing Details
```bash
# Show full task details
s9 task show TASK_ID

# Generate report
s9 task report --format markdown
```

## Common Workflows

### Workflow 1: Complete a Task End-to-End

```bash
# 1. Find work
s9 task list --role Engineer --status TODO

# 2. Claim task
s9 task claim BLD-H-0037 --agent-name "Goibniu"

# 3. Work on it (update periodically)
s9 task update BLD-H-0037 --notes "Made progress on X" --actual-hours 2.0

# 4. Close when done
s9 task close BLD-H-0037 --status COMPLETE --notes "All tests passing, code reviewed"
```

### Workflow 2: Pause for Higher Priority

```bash
# Working on DOC-M-0019
s9 task update DOC-M-0019 --notes "50% complete"

# Critical issue appears
s9 task close DOC-M-0019 --status PAUSED --notes "Pausing for BLD-C-0003"

# Work on BLD-C-0003
s9 task claim BLD-C-0003 --agent-name "Goibniu"
s9 task close BLD-C-0003 --status COMPLETE --notes "Security issue fixed"

# Resume DOC-M-0019
s9 task update DOC-M-0019 --status UNDERWAY --notes "Resuming after BLD-C-0003"
```

### Workflow 3: Hit a Blocker

```bash
# Working on OPR-H-0038
s9 task update OPR-H-0038 --notes "Need BLD-H-0037 to be complete first"

# Mark as blocked
s9 task close OPR-H-0038 --status BLOCKED --notes "Blocked by BLD-H-0037"

# When BLD-H-0037 is complete
s9 task update OPR-H-0038 --status UNDERWAY --notes "BLD-H-0037 complete, resuming"
```

## Reference Information

For detailed reference information, see **`.opencode/docs/guides/tasks.md`**:
- Task ID format and structure
- Valid status values and when to use them
- Priority levels and guidelines  
- Role prefixes
- Task lifecycle diagrams

## See Also

**Guides:**
- `.opencode/docs/guides/tasks.md` - Task system reference (statuses, priorities, ID format)
- `.opencode/docs/guides/task-sizing.md` - Task sizing guidelines
- `.opencode/docs/roles/README.md` - Detailed role descriptions

**Documentation:**
- `.opencode/data/README.md` - Complete s9 system reference
- `.opencode/docs/guides/task-sizing.md` - Task sizing guidelines

**Related Commands:**
- `s9 mission start` - Start a new agent session
- `s9 persona suggest` - Get daemon name suggestions
