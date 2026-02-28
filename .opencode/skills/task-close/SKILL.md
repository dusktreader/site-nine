---
name: task-close
description: Close tasks when complete or aborted using OpenCode tools
license: MIT
compatibility: opencode
metadata:
  audience: all-agents
  workflow: task-completion
---

## What I Do

I provide comprehensive instructions for closing tasks using the OpenCode `task_close` tool. Use this skill when a task is complete or should be cancelled.

## When to Close

- Task is **complete** - all objectives met
- Task is **cancelled** or obsolete

## Tool Syntax

Use the `task_close` tool to close a task:

```
task_close(
  task_id="TASK-ID",
  status="COMPLETE",  # or "ABORTED"
  notes="Final summary"
)
```

**Required:**
- `task_id` - The task to close (e.g., "ENG-H-0037")
- `status` - Closing status: "COMPLETE" or "ABORTED"
- `notes` - Summary of why closing with this status

The tool automatically:
- Looks up your current mission from the OpenCode session context
- Records the `closed_at` timestamp
- Updates the task status
- Appends final notes to the task
- Updates the markdown file in `.opencode/work/tasks/`
- Removes the task from your active work queue

## Status Options

### COMPLETE - Task Finished Successfully

Use when:
- All objectives met
- Tests passing
- Code reviewed and merged
- Documentation updated
- Ready for production

**Example:**
```
task_close(
  task_id="ENG-H-0037",
  status="COMPLETE",
  notes="Rate limiting implemented and tested. All tests passing. Documentation updated."
)
```

### ABORTED - Cancelled

Use when:
- Requirements changed
- Task no longer needed
- Duplicate of another task
- Approach was wrong
- Obsolete due to architecture change

**Example:**
```
task_close(
  task_id="DOC-L-0012",
  status="ABORTED",
  notes="Task obsolete after architecture change in ARC-H-0029. No longer needed."
)
```

## What Happens When You Close

When you call the `task_close` tool:

1. ✅ `closed_at` timestamp recorded
2. ✅ `status` updated to COMPLETE or ABORTED
3. ✅ Final notes appended (not replaced)
4. ✅ Markdown file header updated in `.opencode/work/tasks/`
5. ✅ Task removed from active work queue
6. ✅ Mission association maintained via session context

## Example Workflows

### Completing a Task

```
# Close as complete
task_close(
  task_id="ENG-H-0037",
  status="COMPLETE",
  notes="Rate limiting implemented and tested. All tests passing. Documentation updated. PR #123 merged."
)

# Verify with task_show tool
task_show(task_id="ENG-H-0037")
# Status: COMPLETE
# Closed: 2026-02-05T23:30:00+00:00
```

### Aborting Obsolete Task

```
task_close(
  task_id="DOC-L-0012",
  status="ABORTED",
  notes="Task obsolete after architecture change in ARC-H-0029. New approach documented in ARC-H-0030 instead."
)
```

## Before Closing

### Checklist for COMPLETE

- ✅ All objectives met
- ✅ Tests written and passing
- ✅ Code reviewed
- ✅ Documentation updated
- ✅ Progress notes updated
- ✅ Final notes written

### Checklist for ABORTED

- ✅ Clear reason for cancellation
- ✅ Alternative approach noted (if any)
- ✅ Related tasks updated
- ✅ Stakeholders informed

## Tips and Best Practices

### Do
- ✅ Use correct status (COMPLETE vs ABORTED)
- ✅ Write clear closing notes
- ✅ Close tasks before ending session
- ✅ Reference related tasks in notes
- ✅ Update progress with `task_update` tool before closing

### Don't
- ❌ Don't leave tasks UNDERWAY forever
- ❌ Don't mark incomplete work as COMPLETE
- ❌ Don't forget to write closing notes
- ❌ Don't use vague or generic notes

## Troubleshooting

### "Task not found"
- Check task ID spelling and case
- Verify task exists with the `task_show` tool

### "Invalid status value"
- Must be: COMPLETE or ABORTED
- Check spelling and case
- See status options above

### "Task not claimed"
- You can only close tasks you've claimed
- Claim it first with the `task_claim` tool

### "Missing required notes"
- `notes` parameter is required when closing
- Provide meaningful summary of closure reason

## After Closing

Verify task was closed with the `task_show` tool:
```
task_show(task_id="ENG-H-0037")
```

Check status and closing timestamp are correct.

## Common Workflows

### Complete a Task End-to-End

```
# 1. Claim it with task_claim tool
task_claim(task_id="ENG-H-0037")

# 2. Work on it, update progress
task_update(
  task_id="ENG-H-0037",
  status="UNDERWAY",
  notes="Implemented core functionality"
)

# 3. Close when done
task_close(
  task_id="ENG-H-0037",
  status="COMPLETE",
  notes="All tests passing, code reviewed, documentation complete"
)
```

### Switch to Higher Priority Task

```
# Working on medium priority task
task_update(
  task_id="DOC-M-0019",
  status="UNDERWAY",
  notes="50% complete - intro and setup sections done"
)

# Critical issue appears - close current task as ABORTED or COMPLETE depending on state
# If you want to resume later, just leave it UNDERWAY and use task_release to hand it off
# Otherwise, close it:
task_close(
  task_id="DOC-M-0019",
  status="ABORTED",
  notes="Stopping work to handle critical security issue ENG-C-0003"
)

# Work on critical issue
task_claim(task_id="ENG-C-0003")
task_close(
  task_id="ENG-C-0003",
  status="COMPLETE",
  notes="Security issue fixed"
)
```

## See Also

**Related Skills:**
- `task-update` - Updating progress before closing
- `task-claim` - Claiming tasks to resume paused/blocked work
- `task-query` - Viewing closed tasks and completion history
- `task-management` - Overview of task system

**Documentation:**
- `.opencode/data/README.md` - Complete s9 system reference
