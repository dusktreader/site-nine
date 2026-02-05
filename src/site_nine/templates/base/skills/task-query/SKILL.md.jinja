---
name: task-query
description: Query, list, and report on tasks in the s9 database
license: MIT
compatibility: opencode
metadata:
  audience: all-agents
  workflow: task-discovery
---

## Important: CLI Tool Usage

**CRITICAL:** This project uses the `s9` CLI executable throughout these instructions.
- **CLI executable:** `s9` (use in bash commands)
- **Python module:** `site_nine` (use in Python imports: `from site_nine import ...`)

All commands in this skill use the `s9` executable via bash. You should NOT attempt to import an `s9` module in Python code.

## What I Do

I provide comprehensive instructions for finding, listing, and reporting on tasks in the s9 task database. Use this skill to discover available work, view task details, and generate reports.

## List Available Tasks

### By Status

```bash
s9 task list --status TODO
s9 task list --status UNDERWAY
s9 task list --status TODO,UNDERWAY
s9 task list --status COMPLETE
```

**Available statuses:**
- `TODO` - Not started
- `UNDERWAY` - In progress
- `BLOCKED` - Can't proceed
- `PAUSED` - Temporarily stopped
- `REVIEW` - Awaiting review
- `COMPLETE` - Finished
- `ABORTED` - Cancelled

### By Role

```bash
s9 task list --role Engineer --status TODO
s9 task list --role Administrator --status TODO
s9 task list --role Tester
```

**Available roles:**
- Administrator
- Architect
- Engineer
- Tester
- Documentarian
- Designer
- Inspector
- Operator
- Historian

### By Priority

```bash
s9 task list --priority CRITICAL,HIGH --status TODO
s9 task list --priority HIGH
s9 task list --priority MEDIUM,LOW
```

**Priority levels:**
- `CRITICAL` - Immediate action required
- `HIGH` - Important, do soon
- `MEDIUM` - Nice to have
- `LOW` - Do when time permits

### Active Tasks Only

Show only TODO and UNDERWAY tasks:

```bash
s9 task list --active-only
```

This is the most common query for finding work.

### By Agent

See tasks claimed by specific agent:

```bash
s9 task list --agent "Goibniu"
s9 task list --agent "Ishtar" --status UNDERWAY
s9 task list --agent "Ptah" --status COMPLETE
```

### Combining Filters

Filters can be combined:

```bash
# High priority Engineer tasks that are TODO
s9 task list --role Engineer --priority HIGH --status TODO

# Active tasks assigned to Goibniu
s9 task list --agent "Goibniu" --active-only

# Completed tasks for a specific role
s9 task list --role Tester --status COMPLETE
```

## View Task Details

Get full details for a specific task:

```bash
s9 task show BLD-H-0037
```

**Shows:**
- Task ID, title, objective
- Full metadata (status, priority, role, category)
- Agent assignment (if claimed)
- Timestamps (created, claimed, closed)
- Time tracking (actual hours)
- Objective and description
- Dependencies
- Progress notes
- File path to markdown artifact

### Example Output

```
Task: BLD-H-0037
Title: Implement Rate Limiting Middleware
Status: UNDERWAY
Priority: HIGH
Role: Engineer
Category: Security
Agent: Goibniu
Created: 2026-02-03T10:00:00+00:00
Claimed: 2026-02-05T14:00:00+00:00
Actual Hours: 4.0

Objective:
Add rate limiting to protect API endpoints from abuse

Description:
Implement token bucket rate limiting with configurable limits per endpoint

Dependencies: None

Notes:
- Implemented token bucket algorithm, added configuration (2.0 hours)
- Added tests, all passing (4.0 hours)

File: .opencode/work/tasks/BLD-H-0037.md
```

## Generate Reports

### Markdown Report

```bash
s9 task report --format markdown
```

Generates markdown-formatted report of all tasks, suitable for documentation.

### Table Format

```bash
s9 task report --format table
```

Generates ASCII table suitable for terminal display.

### JSON Format

```bash
s9 task report --format json
```

Generates JSON output for programmatic processing.

### Filter Reports

Reports can be filtered by role:

```bash
s9 task report --role Engineer --format markdown
s9 task report --role Administrator --format table
```

## Finding Work

### Find Available Work for Your Role

```bash
# Find TODO tasks for your role
s9 task list --role Engineer --status TODO

# Find high-priority TODO tasks
s9 task list --role Engineer --priority CRITICAL,HIGH --status TODO

# Find any active work
s9 task list --role Engineer --active-only
```

### Find Critical/Urgent Work

```bash
# Critical tasks across all roles
s9 task list --priority CRITICAL --status TODO

# High priority tasks needing attention
s9 task list --priority HIGH --status TODO,UNDERWAY
```

### Find Blocked Tasks

```bash
# See what's blocked
s9 task list --status BLOCKED

# Check your blocked tasks
s9 task list --agent "YourName" --status BLOCKED
```

### Check Dependencies

Before claiming a task, check if it has dependencies:

```bash
s9 task show BLD-H-0038
# Depends on: BLD-H-0037

# Check if dependency is complete
s9 task show BLD-H-0037
# Status: COMPLETE ✅
```

## Common Query Patterns

### Morning Standup

```bash
# What am I working on?
s9 task list --agent "YourName" --status UNDERWAY

# What's next to work on?
s9 task list --role YourRole --priority HIGH --status TODO

# What's blocked?
s9 task list --status BLOCKED
```

### Finding Next Task

```bash
# 1. Check critical tasks first
s9 task list --priority CRITICAL --status TODO

# 2. Then high priority for your role
s9 task list --role YourRole --priority HIGH --status TODO

# 3. Look at medium priority if nothing urgent
s9 task list --role YourRole --priority MEDIUM --status TODO
```

### Progress Check

```bash
# How many tasks completed?
s9 task list --status COMPLETE

# How many tasks in progress?
s9 task list --status UNDERWAY

# How much work left?
s9 task list --status TODO
```

### Team Visibility

```bash
# What is each agent working on?
s9 task list --status UNDERWAY

# What has been completed?
s9 task list --status COMPLETE

# Generate status report
s9 task report --format markdown
```

## Tips and Best Practices

### Do
- ✅ Use `--active-only` for quick work discovery
- ✅ Check dependencies before claiming tasks
- ✅ Filter by role and priority to focus
- ✅ Use `task show` to understand task fully before claiming
- ✅ Generate reports for team status updates

### Don't
- ❌ Don't list all tasks without filters (too much noise)
- ❌ Don't ignore CRITICAL tasks
- ❌ Don't claim tasks without checking dependencies
- ❌ Don't forget to check who's working on what

## Output Format

### List Output

Task lists show key information in columns:

```
TASK_ID | TITLE | STATUS | PRIORITY | ROLE | AGENT
BLD-H-0037 | Implement Rate Limiting | UNDERWAY | HIGH | Engineer | Goibniu
BLD-H-0038 | Configure Gateway | TODO | HIGH | Operator | -
DOC-M-0019 | Update Documentation | PAUSED | MEDIUM | Documentarian | Ishtar
```

### Show Output

Full task details including:
- All metadata
- Full objective and description
- Complete notes history
- Time tracking
- Timestamps
- File path

## Troubleshooting

### "No tasks found"
- Check your filters aren't too restrictive
- Try `s9 task list` without filters to see all tasks
- Verify tasks exist for that role/status/priority

### "Task not found"
- Check task ID spelling and case
- Use `s9 task list | grep TASK_ID` to find it
- Make sure you're using the full task ID (e.g., BLD-H-0037)

### "Invalid filter value"
- Check spelling of status/priority/role
- See valid values sections above
- Use exact capitalization

## Performance Tips

- Use filters to reduce output
- Use `--active-only` instead of listing all statuses
- Use `task show` for single task details
- Generate reports periodically, not constantly

## See Also

**Related Skills:**
- `task-create` - Creating new tasks
- `task-claim` - Claiming tasks found through queries
- `task-update` - Updating tasks after claiming
- `task-close` - Closing tasks when complete
- `task-management` - Overview of task system

**Documentation:**
- `.opencode/data/README.md` - Complete s9 system reference
