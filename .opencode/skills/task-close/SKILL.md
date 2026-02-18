---
name: task-close
description: Close tasks in the s9 database when complete, paused, blocked, or aborted
license: MIT
compatibility: opencode
metadata:
  audience: all-agents
  workflow: task-completion
---

## Important: CLI Tool Usage

**CRITICAL:** This project uses the `s9` CLI executable throughout these instructions.
- **CLI executable:** `s9` (use in bash commands)
- **Python module:** `site_nine` (use in Python imports: `from site_nine import ...`)

All commands in this skill use the `s9` executable via bash. You should NOT attempt to import an `s9` module in Python code.

## What I Do

I provide comprehensive instructions for closing tasks in the s9 task database. Use this skill when a task is complete, needs to be paused, is blocked, or should be cancelled.

## When to Close

- Task is **complete** - all objectives met
- **Pausing** work to focus on higher priority
- **Blocked** and can't proceed
- Task is **cancelled** or obsolete

## Command Syntax

```bash
s9 task close TASK_ID \
  --status {COMPLETE|ABORTED} \
  [--notes "Final summary"]
```

**Required:**
- `TASK_ID` - The task to close

**Optional:**
- `--status` or `-s` - Closing status (default: COMPLETE)
- `--notes` or `-n` - Summary of why closing with this status

## Status Options

### COMPLETE - Task Finished Successfully

Use when:
- All objectives met
- Tests passing
- Code reviewed and merged
- Documentation updated
- Ready for production

**Example:**
```bash
s9 task close ENG-H-0037 \
  --status COMPLETE \
  --notes "Rate limiting implemented and tested. All tests passing. Documentation updated."
```

### ABORTED - Cancelled

Use when:
- Requirements changed
- Task no longer needed
- Duplicate of another task
- Approach was wrong
- Obsolete due to architecture change

**Example:**
```bash
s9 task close DOC-L-0012 \
  --status ABORTED \
  --notes "Task obsolete after architecture change in ARC-H-0029. No longer needed."
```

## What Happens When You Close

When you close a task:

1. ✅ `closed_at` timestamp recorded
2. ✅ `status` updated to specified value
3. ✅ Final notes added (appended to existing notes)
4. ✅ Markdown file header updated in `.opencode/work/tasks/`
5. ✅ Task removed from active work queue

## Example Workflows

### Completing a Task

```bash
# Update final time and status
s9 task update ENG-H-0037 --actual-hours 6.5

# Close as complete
s9 task close ENG-H-0037 \
  --status COMPLETE \
  --notes "Rate limiting implemented and tested. All tests passing. Documentation updated. PR #123 merged."

# Verify
s9 task show ENG-H-0037
# Status: COMPLETE
# Closed: 2026-02-05T23:30:00+00:00
```

### Pausing for Higher Priority

```bash
# Document what's done
s9 task update DOC-M-0019 --notes "50% complete - intro and setup sections done"

# Pause it
s9 task close DOC-M-0019 \
  --status PAUSED \
  --notes "Pausing to handle critical security documentation for ENG-C-0003. Will resume after."
```

### Blocking on Dependency

```bash
# Document the blocker
s9 task close OPR-H-0038 \
  --status BLOCKED \
  --notes "Blocked by ENG-H-0037. Need rate limiting middleware complete before deploying gateway. Estimated unblock: 2026-02-06."
```

### Aborting Obsolete Task

```bash
s9 task close DOC-L-0012 \
  --status ABORTED \
  --notes "Task obsolete after architecture change in ARC-H-0029. New approach documented in ARC-H-0030 instead."
```

## Resuming Paused/Blocked Tasks

To resume a paused or blocked task:

### If Still Your Task

```bash
# Update status back to UNDERWAY
s9 task update ENG-H-0038 --status UNDERWAY --notes "Blocker resolved, resuming work"
```

### If Not Your Task

```bash
# Claim it again (using your mission ID and role)
s9 task claim ENG-H-0038 --mission MISSION_ID --role Engineer

# Update status and add notes
s9 task update ENG-H-0038 --status UNDERWAY --notes "Blocker resolved, starting implementation"
```

## Before Closing

### Checklist for COMPLETE

- ✅ All objectives met
- ✅ Tests written and passing
- ✅ Code reviewed
- ✅ Documentation updated
- ✅ Progress notes updated
- ✅ Final notes written

### Checklist for PAUSED

- ✅ Current progress documented
- ✅ Clear reason for pausing
- ✅ Time tracked up to pause point
- ✅ Note when you'll resume (if known)

### Checklist for BLOCKED

- ✅ Blocker clearly identified
- ✅ Blocking task ID noted (if applicable)
- ✅ Estimated unblock time (if known)
- ✅ Coordinated with blocking party

### Checklist for ABORTED

- ✅ Clear reason for cancellation
- ✅ Alternative approach noted (if any)
- ✅ Related tasks updated
- ✅ Stakeholders informed

## Tips and Best Practices

### Do
- ✅ Use correct status (COMPLETE vs PAUSED vs BLOCKED)
- ✅ Write clear closing notes
- ✅ Close tasks before ending session
- ✅ Update actual hours before closing
- ✅ Reference related tasks in notes
- ✅ Be specific about blockers

### Don't
- ❌ Don't leave tasks UNDERWAY forever
- ❌ Don't mark incomplete work as COMPLETE
- ❌ Don't use PAUSED for permanent stops (use ABORTED)
- ❌ Don't use BLOCKED for soft dependencies (use PAUSED)
- ❌ Don't forget to write closing notes

## Troubleshooting

### "Task not found"
- Check task ID spelling and case
- Verify task exists: `s9 task list | grep TASK_ID`

### "Invalid status value"
- Must be: COMPLETE, PAUSED, BLOCKED, or ABORTED
- Check spelling and case
- See status options above

### "Task not claimed"
- You can only close tasks you've claimed
- Claim it first: `s9 task claim TASK_ID --mission MISSION_ID --role ROLE`

### "Missing required notes"
- `--notes` is required when closing
- Provide meaningful summary of closure reason

## After Closing

Verify task was closed:
```bash
s9 task show ENG-H-0037
```

Check status and closing timestamp are correct.

## Common Workflows

### Complete a Task End-to-End

```bash
# 1. Claim it (assuming mission ID 42)
s9 task claim ENG-H-0037 --mission 42 --role Engineer

# 2. Work on it, update progress
s9 task update ENG-H-0037 --status UNDERWAY --notes "Implemented core functionality"

# 3. Close when done
s9 task close ENG-H-0037 \
  --status COMPLETE \
  --notes "All tests passing, code reviewed, documentation complete"
```

### Pause for Higher Priority

```bash
# Working on medium priority task
s9 task update DOC-M-0019 --status UNDERWAY --notes "50% complete"

# Critical issue appears
s9 task close DOC-M-0019 --status PAUSED --notes "Pausing for ENG-C-0003"

# Work on critical issue (assuming mission ID 42)
s9 task claim ENG-C-0003 --mission 42 --role Engineer
s9 task close ENG-C-0003 --status COMPLETE --notes "Security issue fixed"

# Resume paused task
s9 task update DOC-M-0019 --status UNDERWAY --notes "Resuming after ENG-C-0003"
```

### Hit a Blocker

```bash
# Working on task
s9 task update OPR-H-0038 --notes "Need ENG-H-0037 to be complete first"

# Mark as blocked
s9 task close OPR-H-0038 \
  --status BLOCKED \
  --notes "Blocked by ENG-H-0037. Will resume when rate limiting is deployed."

# When blocker is resolved
s9 task update OPR-H-0038 --status UNDERWAY --notes "ENG-H-0037 complete, resuming"
```

## See Also

**Related Skills:**
- `task-update` - Updating progress before closing
- `task-claim` - Claiming tasks to resume paused/blocked work
- `task-query` - Viewing closed tasks and completion history
- `task-management` - Overview of task system

**Documentation:**
- `.opencode/data/README.md` - Complete s9 system reference
