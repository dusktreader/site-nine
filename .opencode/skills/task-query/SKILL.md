---
name: task-query
description: Query, list, and report on tasks in the s9 database
license: MIT
compatibility: opencode
metadata:
  audience: all-agents
  workflow: task-discovery
---

## What I Do

I provide comprehensive instructions for finding, listing, and reporting on tasks in the s9 task database using the `task_show` and `task_list` tools. Use this skill to discover available work, view task details, and generate reports.

## Tool Overview

This skill uses:
- **`task_show` tool** - Get full details for a specific task
- **`task_list` tool** - List and filter tasks by various criteria
- **`task_report` tool** - Generate formatted reports

All tools return clean JSON results and automatically receive mission context from OpenCode.

## List Available Tasks

### By Status

```python
task_list(status="TODO")
task_list(status="UNDERWAY")
task_list(status="TODO,UNDERWAY")
task_list(status="COMPLETE")
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

```python
task_list(role="Engineer", status="TODO")
task_list(role="Administrator", status="TODO")
task_list(role="Tester")
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

```python
task_list(priority="CRITICAL,HIGH", status="TODO")
task_list(priority="HIGH")
task_list(priority="MEDIUM,LOW")
```

**Priority levels:**
- `CRITICAL` - Immediate action required
- `HIGH` - Important, do soon
- `MEDIUM` - Nice to have
- `LOW` - Do when time permits

### Active Tasks Only

Show only TODO and UNDERWAY tasks:

```python
task_list(active_only=True)
```

This is the most common query for finding work.

### By Agent

See tasks claimed by specific agent:

```python
task_list(agent="Goibniu")
task_list(agent="Ishtar", status="UNDERWAY")
task_list(agent="Ptah", status="COMPLETE")
```

### Combining Filters

Filters can be combined:

```python
# High priority Engineer tasks that are TODO
task_list(role="Engineer", priority="HIGH", status="TODO")

# Active tasks assigned to Goibniu
task_list(agent="Goibniu", active_only=True)

# Completed tasks for a specific role
task_list(role="Tester", status="COMPLETE")
```

## View Task Details

Get full details for a specific task:

```python
task_show(task_id="ENG-H-0037")
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

```json
{
  "task_id": "ENG-H-0037",
  "title": "Implement Rate Limiting Middleware",
  "status": "UNDERWAY",
  "priority": "HIGH",
  "role": "Engineer",
  "category": "Security",
  "agent": "Goibniu",
  "created_at": "2026-02-03T10:00:00+00:00",
  "claimed_at": "2026-02-05T14:00:00+00:00",
  "actual_hours": 4.0,
  "objective": "Add rate limiting to protect API endpoints from abuse",
  "description": "Implement token bucket rate limiting with configurable limits per endpoint",
  "dependencies": [],
  "notes": [
    "Implemented token bucket algorithm, added configuration (2.0 hours)",
    "Added tests, all passing (4.0 hours)"
  ],
  "file_path": ".opencode/work/tasks/ENG-H-0037.md"
}
```

## Generate Reports

### Markdown Report

```python
task_report(format="markdown")
```

Generates markdown-formatted report of all tasks, suitable for documentation.

### Table Format

```python
task_report(format="table")
```

Generates ASCII table suitable for terminal display.

### JSON Format

```python
task_report(format="json")
```

Generates JSON output for programmatic processing.

### Filter Reports

Reports can be filtered by role:

```python
task_report(role="Engineer", format="markdown")
task_report(role="Administrator", format="table")
```

## Finding Work

### Find Available Work for Your Role

```python
# Find TODO tasks for your role
task_list(role="Engineer", status="TODO")

# Find high-priority TODO tasks
task_list(role="Engineer", priority="CRITICAL,HIGH", status="TODO")

# Find any active work
task_list(role="Engineer", active_only=True)
```

### Find Critical/Urgent Work

```python
# Critical tasks across all roles
task_list(priority="CRITICAL", status="TODO")

# High priority tasks needing attention
task_list(priority="HIGH", status="TODO,UNDERWAY")
```

### Find Blocked Tasks

```python
# See what's blocked
task_list(status="BLOCKED")

# Check your blocked tasks
task_list(agent="YourName", status="BLOCKED")
```

### Check Dependencies

Before claiming a task, check if it has dependencies:

```python
result = task_show(task_id="ENG-H-0038")
# Check result["dependencies"]

# Check if dependency is complete
dep_result = task_show(task_id="ENG-H-0037")
# Check dep_result["status"] == "COMPLETE"
```

## Common Query Patterns

### Morning Standup

```python
# What am I working on?
task_list(agent="YourName", status="UNDERWAY")

# What's next to work on?
task_list(role="YourRole", priority="HIGH", status="TODO")

# What's blocked?
task_list(status="BLOCKED")
```

### Finding Next Task

```python
# 1. Check critical tasks first
task_list(priority="CRITICAL", status="TODO")

# 2. Then high priority for your role
task_list(role="YourRole", priority="HIGH", status="TODO")

# 3. Look at medium priority if nothing urgent
task_list(role="YourRole", priority="MEDIUM", status="TODO")
```

#### When to Auto-Claim vs. Ask

**Auto-claim after finding** when the user gives an imperative command:
- "Find the next unclaimed task" → Find AND claim automatically
- "Get the next task" → Find AND claim automatically
- "Claim the next task" → Find AND claim automatically
- "What should I work on next?" → Find AND claim automatically

**Ask before claiming** when the user is inquiring:
- "What tasks are available?" → Show list, then ask if they want to claim
- "Show me unclaimed tasks" → Show list, then ask if they want to claim
- "List tasks for [role]" → Show list, then ask if they want to claim

The key distinction: imperative commands ("find", "get", "claim") indicate the user wants you to take action. Inquiry commands ("what", "show", "list") indicate the user wants information first.

### Progress Check

```python
# How many tasks completed?
task_list(status="COMPLETE")

# How many tasks in progress?
task_list(status="UNDERWAY")

# How much work left?
task_list(status="TODO")
```

### Team Visibility

```python
# What is each agent working on?
task_list(status="UNDERWAY")

# What has been completed?
task_list(status="COMPLETE")

# Generate status report
task_report(format="markdown")
```

## Tips and Best Practices

### Do
- ✅ Use `active_only=True` for quick work discovery
- ✅ Check dependencies before claiming tasks
- ✅ Filter by role and priority to focus
- ✅ Use `task_show` to understand task fully before claiming
- ✅ Generate reports for team status updates
- ✅ Auto-claim when user gives imperative commands ("find next task", "get next task")
- ✅ Distinguish between inquiry ("what tasks?") and action requests ("find next task")

### Don't
- ❌ Don't list all tasks without filters (too much noise)
- ❌ Don't ignore CRITICAL tasks
- ❌ Don't claim tasks without checking dependencies
- ❌ Don't forget to check who's working on what
- ❌ Don't ask "Would you like me to claim this?" after imperative commands
- ❌ Don't auto-claim when user is just browsing tasks

## Output Format

### List Output

Task lists return JSON arrays with key information:

```json
[
  {
    "task_id": "ENG-H-0037",
    "title": "Implement Rate Limiting",
    "status": "UNDERWAY",
    "priority": "HIGH",
    "role": "Engineer",
    "agent": "Goibniu"
  },
  {
    "task_id": "ENG-H-0038",
    "title": "Configure Gateway",
    "status": "TODO",
    "priority": "HIGH",
    "role": "Operator",
    "agent": null
  }
]
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
- Try `task_list()` without filters to see all tasks
- Verify tasks exist for that role/status/priority

### "Task not found"
- Check task ID spelling and case
- Use `task_list()` to find available tasks
- Make sure you're using the full task ID (e.g., ENG-H-0037)

### "Invalid filter value"
- Check spelling of status/priority/role
- See valid values sections above
- Use exact capitalization

## Performance Tips

- Use filters to reduce output
- Use `active_only=True` instead of listing all statuses
- Use `task_show` for single task details
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
