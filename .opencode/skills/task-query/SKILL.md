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

I provide comprehensive instructions for finding, listing, and reporting on tasks in the s9
task database using the `task_show` tool. Use this skill to discover available work, view task
details, and generate reports.

## Tool Overview

This skill uses the **`task_show` tool**, which queries tasks with optional filters:

- `task_id` — returns full details for a single task
- `role`, `status`, `priority` — filter the task list
- `possession_id` — returns tasks owned by a specific possession
- `report=True` — generates a full summary report (large output; avoid for routine queries)

All calls return clean JSON and automatically receive possession context from OpenCode.

## The Authoritative Rule

**Never re-categorize or re-list tasks.** The `status` field returned by `task_show` is an
enum value backed by the database. It is authoritative. If the tool says a task is `COMPLETE`,
it is complete. Do not move it to a different grouping because you expected it to be `TODO`.

Running `task_show(report=True)` over a large dataset and then mentally filtering the output
is the most common source of task status errors. Use targeted queries instead.

## List Available Tasks

### By Status

```python
task_show(status="TODO")
task_show(status="UNDERWAY")
task_show(status="COMPLETE")
```

**Available statuses:**
- `TODO` - Not started
- `UNDERWAY` - In progress
- `BLOCKED` - Can't proceed
- `REVIEW` - Awaiting review
- `COMPLETE` - Finished
- `ABORTED` - Cancelled

### By Role

```python
task_show(role="Engineer", status="TODO")
task_show(role="Administrator", status="TODO")
task_show(role="Tester", status="TODO")
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

### Combining Filters

```python
# High priority Engineer tasks that are TODO
task_show(role="Engineer", priority="HIGH", status="TODO")

# Tasks owned by a specific possession
task_show(possession_id=42, status="UNDERWAY")

# Completed tasks for a specific role
task_show(role="Tester", status="COMPLETE")
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

## Finding Work

### The Canonical Available-Work Query

**This is the only correct way to find available work for a role.** Do not use
`report=True` for this purpose — it returns everything and requires mental filtering,
which is the primary cause of task-status errors.

```python
# Canonical pattern — use this at possession start and whenever looking for next work
task_show(role="Engineer", status="TODO")

# Narrow by priority if the list is long
task_show(role="Engineer", status="TODO", priority="HIGH")
```

This returns a database-filtered list of tasks that are genuinely available. The
`status` values come directly from the database and require no post-processing.
Report them as-is.

**Do not use `report=True` for role-scoped queries.** The report output is large and
must be mentally filtered, which introduces categorization errors. Reserve it for
Director-level overviews only.

### Find Critical/Urgent Work

```python
# Critical tasks across all roles
task_show(priority="CRITICAL", status="TODO")

# High priority tasks needing attention
task_show(priority="HIGH", status="TODO")
```

### Find Blocked Tasks

```python
task_show(status="BLOCKED")
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
task_show(possession_id=<your-id>, status="UNDERWAY")

# What's next to work on?
task_show(role="YourRole", status="TODO")

# What's blocked?
task_show(status="BLOCKED")
```

### Finding Next Task

```python
# 1. Check critical tasks first
task_show(priority="CRITICAL", status="TODO")

# 2. Then tasks for your role
task_show(role="YourRole", status="TODO")
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

The key distinction: imperative commands ("find", "get", "claim") indicate the user wants you
to take action. Inquiry commands ("what", "show", "list") indicate the user wants information
first.

### Progress Check

```python
# Active tasks for your role
task_show(role="YourRole", status="UNDERWAY")

# Work remaining
task_show(role="YourRole", status="TODO")
```

### Team Visibility

```python
# What is each agent working on?
task_show(status="UNDERWAY")

# What has been completed?
task_show(status="COMPLETE")

# Full report (large output — Director or one-off summaries only; never for finding available work)
task_show(report=True)
```

## Tips and Best Practices

### Do
- ✅ Use `task_show(role=..., status="TODO")` to find available work
- ✅ Report the `status` field verbatim from tool results — it is authoritative
- ✅ Check dependencies before claiming tasks
- ✅ Filter by role and status to get an accurate, scoped result
- ✅ Use `task_show(task_id=...)` to understand a task fully before claiming
- ✅ Auto-claim when user gives imperative commands ("find next task", "get next task")
- ✅ Distinguish between inquiry ("what tasks?") and action requests ("find next task")

### Don't
- ❌ Don't run `task_show(report=True)` and then mentally re-filter the output
- ❌ Don't re-categorize tasks from a broad result — the status enum is authoritative
- ❌ Don't construct secondary task lists that contradict what the tool returned
- ❌ Don't ignore CRITICAL tasks
- ❌ Don't claim tasks without checking dependencies
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
- Try `task_show(role="YourRole")` without a status filter to see all tasks for the role
- Verify tasks exist for that role/status/priority

### "Task not found"
- Check task ID spelling and case
- Use `task_show(role="YourRole", status="TODO")` to find available tasks
- Make sure you're using the full task ID (e.g., ENG-H-0037)

### "Invalid filter value"
- Check spelling of status/priority/role
- See valid values sections above
- Use exact capitalization

## See Also

**Related Skills:**
- `task-create` - Creating new tasks
- `task-claim` - Claiming tasks found through queries
- `task-update` - Updating tasks after claiming
- `task-close` - Closing tasks when complete

**Documentation:**
- `.opencode/data/README.md` - Complete s9 system reference
