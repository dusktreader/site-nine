---
name: task-update
description: Update task progress, notes, and time tracking in the s9 database
license: MIT
compatibility: opencode
metadata:
  audience: all-agents
  workflow: task-progress
---

## Important: CLI Tool Usage

**CRITICAL:** This project uses the `s9` CLI executable throughout these instructions.
- **CLI executable:** `s9` (use in bash commands)
- **Python module:** `site_nine` (use in Python imports: `from site_nine import ...`)

All commands in this skill use the `s9` executable via bash. You should NOT attempt to import an `s9` module in Python code.

## What I Do

I provide comprehensive instructions for updating task progress in the s9 task database. Use this skill to track your work, document progress, and record time spent on tasks.

## When to Update

- Made progress on the task
- Tracked time spent
- Encountered issues or blockers
- Changed approach or strategy
- At end of work session
- Before switching to another task
- Before closing the task

## Command Syntax

```bash
s9 task update TASK_ID \
  --status STATUS \
  [--notes "Progress notes"]
```

**Required:**
- `TASK_ID` - The task to update
- `--status` or `-s` - New status for the task

**Optional:**
- `--notes` or `-n` - Progress notes to append

## Progress Notes

Use `--notes` to document progress:

```bash
s9 task update ENG-H-0037 --status UNDERWAY --notes "Implemented basic rate limiter, writing tests"

s9 task update ENG-H-0037 --status UNDERWAY --notes "All tests passing, need to add Redis backend"

s9 task update ENG-H-0037 --status UNDERWAY --notes "Waiting on Redis configuration decision"
```

**Important:** Notes are **appended** to the task's notes field, not replaced.

### What to Include in Notes

**Good notes:**
- What you accomplished
- What you're working on next
- Blockers encountered
- Key decisions made
- Changes to approach

**Examples:**
```bash
--status UNDERWAY --notes "Completed API endpoint implementation. Starting integration tests."
--status UNDERWAY --notes "Refactored auth middleware for better testability. 85% test coverage achieved."
--status UNDERWAY --notes "Discovered performance issue with large datasets. Investigating caching options."
--status UNDERWAY --notes "Met with architect - decided to use Redis instead of in-memory cache."
```

**Avoid:**
- Overly verbose details
- Line-by-line code changes (use git commits for that)
- Too generic ("made progress")

## Changing Status

Usually status changes via claim/close commands, but you can update manually:

```bash
# Resume work after being away
s9 task update ENG-H-0037 --status UNDERWAY --notes "Resuming work after meeting"

# Mark as complete (though usually you use s9 task close)
s9 task update ENG-H-0037 --status COMPLETE --notes "Work finished"
```

**Valid status values:**
- `TODO` - Not started
- `UNDERWAY` - In progress
- `COMPLETE` - Finished
- `ABORTED` - Cancelled

**Note:** Usually you should use:
- `s9 task claim` to set UNDERWAY
- `s9 task close` to set COMPLETE or ABORTED

## Example: Updating Progress

```bash
# After making progress
s9 task update ENG-H-0037 \
  --status UNDERWAY \
  --notes "Implemented token bucket algorithm, added configuration"

# After more progress
s9 task update ENG-H-0037 \
  --status UNDERWAY \
  --notes "Added tests, all passing. Ready for review."

# Check progress
s9 task show ENG-H-0037
```

## Example: Documenting a Note

```bash
s9 task update ENG-H-0037 \
  --status UNDERWAY \
  --notes "Waiting on Redis configuration decision. Need architect approval for caching strategy."
```

## Example: Multiple Updates in Session

```bash
# Start of work session
s9 task update ENG-H-0037 --status UNDERWAY --notes "Starting implementation of rate limiting"

# Mid-session
s9 task update ENG-H-0037 \
  --status UNDERWAY \
  --notes "Basic rate limiter working. Writing tests."

# End of session
s9 task update ENG-H-0037 \
  --status UNDERWAY \
  --notes "All tests passing. Will add Redis backend tomorrow."
```

## Update Frequency

### Good Practice
- Update at least once per work session
- Update when switching tasks
- Update before closing task
- Update when encountering blockers
- Update after significant milestones

### Don't Overdo It
- Not every 15 minutes
- Not for trivial progress
- Don't create noise in the notes

## What Gets Updated

When you run `s9 task update`:

1. ✅ Database updated immediately
2. ✅ Markdown file updated in `.opencode/work/tasks/`
3. ✅ Timestamp recorded for update
4. ✅ Notes appended (not replaced)

## Tips and Best Practices

### Do
- ✅ Update at least once per session
- ✅ Document blockers immediately
- ✅ Note decisions made
- ✅ Be concise but informative
- ✅ Always provide status when updating

### Don't
- ❌ Don't skip updates for days
- ❌ Don't write novels (keep notes concise)
- ❌ Don't update status manually (prefer claim/close commands)

## Troubleshooting

### "Task not found"
- Check task ID spelling and case
- Verify task exists: `s9 task list | grep TASK_ID`

### "Invalid status value"
- Check spelling and case
- See valid status values above
- Consider using claim/close commands instead

### "Task not claimed"
- You can only update tasks you've claimed
- Claim it first: `s9 task claim TASK_ID --mission MISSION_ID --role ROLE`

### "Status is required"
- The `--status` parameter is required
- Provide a valid status value (see valid statuses above)

## After Updating

Verify your update:
```bash
s9 task show ENG-H-0037
```

Check notes were appended and time updated correctly.

## See Also

**Related Skills:**
- `task-claim` - Claiming tasks before you can update them
- `task-close` - Completing tasks after updates
- `task-query` - Viewing task progress and history
- `task-management` - Overview of task system

**Documentation:**
- `.opencode/data/README.md` - Complete s9 system reference
