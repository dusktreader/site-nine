---
name: tasks-report
description: Display task queue report with current status and priorities
license: MIT
compatibility: opencode
metadata:
  audience: all-agents
  workflow: task-viewing
---

## What I Do

I generate and display a comprehensive task report using the `task_report` and `task_list` tools, showing:
- Total task count
- Tasks by priority (CRITICAL, HIGH, MEDIUM, LOW)
- Task status (TODO, UNDERWAY, COMPLETE, ABORTED)
- Agent assignments
- Creation dates
- Quick summary of active work

This gives you a bird's-eye view of all project work.

## Tool Overview

This skill uses:
- **`task_report` tool** - Generate formatted reports
- **`task_list` tool** - List and filter tasks
- **`task_show` tool** - View individual task details

All tools return clean JSON results and automatically receive mission context from OpenCode.

## When to Use Me

Use this skill when:
- ✅ User types `/tasks`
- ✅ Director asks "what tasks are available?"
- ✅ Director asks "show me the task queue"
- ✅ Starting a session and want to see available work
- ✅ Planning work and need to understand current state

Don't use when:
- ❌ Director wants to claim/update a specific task (use task_claim or task_update tools)
- ❌ Director wants to create a new task (use task_create tool)
- ❌ Director wants a single task's details (use task_show tool)

## Step-by-Step Instructions

### Step 1: Generate the Report

Generate an active-only report using the tool:

```python
result = task_report(active_only=True)
```

**What this does:**
- Queries the database for active tasks only
- Excludes COMPLETE and ABORTED tasks
- Groups tasks by priority (CRITICAL, HIGH, MEDIUM, LOW)
- Returns JSON with status, role, title, agent, and creation date
- Includes total active task count

**Expected output:**
JSON array of tasks grouped by priority showing:
- TODO tasks (available to claim)
- UNDERWAY tasks (currently being worked on)

**Note:** If the Director explicitly wants to see all tasks including completed ones:
```python
result = task_report(active_only=False)
```

### Step 2: Parse and Summarize

After displaying the report, provide a quick summary for the Director.

**Count tasks by status:**
- Count TODO tasks (available work)
- Count UNDERWAY tasks (in progress)
- Count BLOCKED tasks (need attention)
- Count COMPLETE tasks (done)

**Identify key information:**
- How many tasks for the Director's current role?
- What's the highest priority TODO task?
- Are there any BLOCKED tasks that need unblocking?
- Are there CRITICAL tasks that need immediate attention?

### Step 3: Display to User

Show the full report followed by a summary:

```
[Full markdown report here]

---

**Summary:**
- **Total tasks:** 59
- **TODO (available):** 5 tasks
- **UNDERWAY (active):** 2 tasks
- **BLOCKED:** 1 task (H001 needs attention)
- **COMPLETE:** 51 tasks

**For your role ([Role]):**
- 3 TODO tasks available
- Highest priority: H036 - Security Review of Gateway Authentication

**Critical attention needed:**
- H001 (BLOCKED) - Create Slack Bot Setup Guide - blocked by external dependency

**Recommendations:**
- Consider claiming H036 (HIGH priority, Inspector role)
- Review H001 blocker and determine if it can be unblocked
```

### Step 4: Offer Next Actions

Based on the report, suggest what the Director might want to do:

**If TODO tasks exist for their role:**
```
Would you like to:
1. Claim one of these tasks? (I can use task_claim tool)
2. See details on a specific task? (I can use task_show tool)
3. Filter tasks? (I can show just TODO, just HIGH priority, etc.)
```

**If no TODO tasks for their role:**
```
No TODO tasks for [Role] right now. You could:
1. Check other roles for work that needs doing
2. Create new tasks if you identify work (I can use task_create tool)
```

**If CRITICAL tasks exist:**
```
⚠️ Attention needed:
- CRITICAL task C004 requires immediate action

Would you like me to show details on this task?
```

### Step 5: Filter Options (Optional)

If the Director wants to filter the report, use these tool calls:

**Filter by status:**
```python
task_list(status="TODO")
task_list(status="UNDERWAY")
```

**Filter by role:**
```python
task_list(role="Engineer")
task_list(role="Tester")
```

**Filter by priority:**
```python
task_list(priority="CRITICAL")
task_list(priority="HIGH")
```

**Combine filters:**
```python
task_list(status="TODO", role="Engineer", priority="HIGH")
```

Show the filtered results and ask if they want to see more or claim a task.

## Important Notes

### About the Report

- **Live data** - Report shows current database state
- **Active tasks only** - By default excludes COMPLETE and ABORTED tasks
- **Sorted by priority** - CRITICAL first, then HIGH, MEDIUM, LOW
- **JSON format** - Clean structured data from tools
- **Timestamps** - Created dates help understand task age
- **All tasks option** - Use `active_only=False` to see completed tasks too

### About Task Status

**Active statuses:**
- `TODO` - Available to claim
- `UNDERWAY` - Currently being worked on

**Terminal statuses:**
- `COMPLETE` - Successfully finished
- `ABORTED` - Cancelled or obsolete

**Note:** Per ADR-013, only COMPLETE and ABORTED are supported for closing tasks. BLOCKED, PAUSED, and REVIEW are legacy statuses.

### About Priority Levels

**CRITICAL (C###):**
- Blocking issues
- Security vulnerabilities
- P0 bugs
- Immediate action required

**HIGH (H###):**
- Important features
- P1 bugs
- Should be done within sprint

**MEDIUM (M###):**
- Nice-to-have features
- Improvements
- Next sprint priority

**LOW (L###):**
- Polish
- Documentation
- Minor issues
- Backlog

### About Agent Assignment

- `-` means unclaimed (available)
- Agent name means claimed/in progress
- Multiple agents means work was handed off

### When to Use Related Tools

**After viewing report:**
- `task_claim` - Claim a TODO task you see
- `task_update` - Update a task you're working on
- `task_close` - Close a task when done
- `task_create` - Create new task if work is missing

**For specific task details:**
```python
task_show(task_id="TASK_ID")
```

This shows full details including description, notes, dependencies.

## Examples

### Example 1: Starting a Session

**User:** `/tasks`

**Agent:**
```
Generating task report...

[Task data from task_report tool]

---

**Summary:**
- **Total active tasks:** 7
- **TODO (available):** 3 tasks
- **UNDERWAY (active):** 1 task

**For your role (Tester):**
- 1 TODO task: H003 - Validate Rate Limiting Functionality
- 1 UNDERWAY: H035 - Full Stack Integration Testing (claimed by themis)

**Recommendations:**
You could claim H003 if you're ready to work on rate limiting validation.

Would you like to:
1. See details on H003? (I can use task_show)
2. Claim H003? (I can use task_claim)
```

### Example 2: Checking for Critical Tasks

**User:** `/tasks` 

**Agent:** 
```
[Full report from task_report...]

---

**Summary:**
- **Total active tasks:** 7
- **CRITICAL:** 1 task ⚠️

**Attention needed:**
- C001 (TODO) - Fix Security Vulnerability in Auth System
  - Role: Engineer
  - Priority: CRITICAL
  
This critical task needs immediate attention.

Would you like me to show details or help you claim it?
```

### Example 3: Filtered View

**User:** `/tasks` then "Show me just TODO high priority tasks"

**Agent:**
```python
task_list(status="TODO", priority="HIGH")
```

Result:
```
TODO HIGH Priority Tasks:

H003 - Validate Rate Limiting Functionality (Tester)
H036 - Security Review of Gateway Authentication (Inspector)

These are the available high-priority tasks ready to be claimed.

Would you like details on either of these?
```

## Troubleshooting

### "Database not found"
- Database should exist at `project.db`
- Contact system administrator if missing

### "No tasks shown"
- Database might be empty
- Check: `task_list()` to see all tasks
- If truly empty, tasks need to be created using `task_create`

### Report is very long
- With `active_only=True`, should only show active work (much shorter)
- If still too long, offer more specific filters
- Use `task_list(status="TODO")` to see only available tasks
- Focus summary on actionable work

## Quick Reference

**Full report:**
```python
# Active tasks only (default - recommended)
task_report(active_only=True)

# All tasks including completed (if explicitly requested)
task_report(active_only=False)
```

**Filtered reports:**
```python
# Active tasks only (TODO, UNDERWAY)
task_list(active_only=True)

# By status
task_list(status="TODO")
task_list(status="UNDERWAY")

# By role
task_list(role="Engineer")
task_list(role="Tester")

# By priority  
task_list(priority="HIGH")
task_list(priority="CRITICAL")

# Combined filters
task_list(status="TODO", role="Engineer", priority="HIGH")
```

**Task details:**
```python
task_show(task_id="TASK_ID")
```

## See Also

**Related Skills:**
- `task-create` - Creating new tasks
- `task-query` - Querying and listing tasks
- `task-claim` - Claiming tasks to work on
- `task-update` - Updating task progress
- `task-close` - Closing completed tasks

**Documentation:**
- `.opencode/data/README.md` - Complete s9 system reference
- `ADR-013` - Site-nine as OpenCode Integration Platform (tool-based architecture)
