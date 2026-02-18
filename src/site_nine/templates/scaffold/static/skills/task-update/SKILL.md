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
  [--status STATUS] \
  [--notes "Progress notes"] \
  [--actual-hours X.X] \
  [--category "New category"]
```

**All parameters are optional** - update only what changed.

## Progress Notes

Use `--notes` to document progress:

```bash
s9 task update ENG-H-0037 --notes "Implemented basic rate limiter, writing tests"

s9 task update ENG-H-0037 --notes "All tests passing, need to add Redis backend"

s9 task update ENG-H-0037 --notes "Blocked on Redis configuration decision"
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
--notes "Completed API endpoint implementation. Starting integration tests."
--notes "Refactored auth middleware for better testability. 85% test coverage achieved."
--notes "Discovered performance issue with large datasets. Investigating caching options."
--notes "Met with architect - decided to use Redis instead of in-memory cache."
```

**Avoid:**
- Overly verbose details
- Line-by-line code changes (use git commits for that)
- Too generic ("made progress")

## Time Tracking

Track actual hours spent:

```bash
s9 task update ENG-H-0037 --actual-hours 2.5

# Add more time later
s9 task update ENG-H-0037 --actual-hours 4.0  # Total is now 4.0, not 2.5+4.0
```

**Important:** `--actual-hours` sets the **total time**, not incremental.

### Time Tracking Best Practices

**Do:**
- Track time in reasonable increments (0.5 hour minimum)
- Update total time at end of each work session
- Be honest and accurate
- Include research and debugging time

**Don't:**
- Track every 15 minutes
- Forget to update before closing task
- Round down significantly (gives false velocity metrics)

## Changing Status

Usually status changes via claim/close commands, but you can update manually:

```bash
# Mark as blocked
s9 task update ENG-H-0037 --status BLOCKED --notes "Waiting for design decision"

# Return to progress
s9 task update ENG-H-0037 --status UNDERWAY --notes "Design decision made, resuming"
```

**Valid status values:**
- `TODO` - Not started
- `UNDERWAY` - In progress
- `BLOCKED` - Can't proceed
- `PAUSED` - Temporarily stopped
- `REVIEW` - Awaiting review
- `COMPLETE` - Finished
- `ABORTED` - Cancelled

**Note:** Usually you should use:
- `s9 task claim` to set UNDERWAY
- `s9 task close` to set COMPLETE/PAUSED/BLOCKED/ABORTED

## Changing Category

Update task category if needed:

```bash
s9 task update ENG-H-0037 --category "Performance"
```

## Example: Updating Progress

```bash
# After 2 hours of work
s9 task update ENG-H-0037 \
  --notes "Implemented token bucket algorithm, added configuration" \
  --actual-hours 2.0

# After 2 more hours
s9 task update ENG-H-0037 \
  --notes "Added tests, all passing. Ready for review." \
  --actual-hours 4.0

# Check progress
s9 task show ENG-H-0037
```

## Example: Documenting a Blocker

```bash
s9 task update ENG-H-0037 \
  --status BLOCKED \
  --notes "Blocked on Redis configuration decision. Need architect approval for caching strategy." \
  --actual-hours 3.5
```

## Example: Multiple Updates in Session

```bash
# Start of work session
s9 task update ENG-H-0037 --notes "Starting implementation of rate limiting"

# Mid-session (after 2 hours)
s9 task update ENG-H-0037 \
  --notes "Basic rate limiter working. Writing tests." \
  --actual-hours 2.0

# End of session (after 4 hours total)
s9 task update ENG-H-0037 \
  --notes "All tests passing. Will add Redis backend tomorrow." \
  --actual-hours 4.0
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
5. ✅ Time tracking cumulative total updated

## Tips and Best Practices

### Do
- ✅ Update at least once per session
- ✅ Track time accurately
- ✅ Document blockers immediately
- ✅ Note decisions made
- ✅ Be concise but informative

### Don't
- ❌ Don't skip updates for days
- ❌ Don't write novels (keep notes concise)
- ❌ Don't forget to track time
- ❌ Don't update status manually (use claim/close instead)

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
- Claim it first: `s9 task claim TASK_ID --agent-name "YourName"`

### "Invalid hours value"
- Use decimal format: 2.5 (not "2 hours 30 minutes")
- Must be positive number
- Represents total time, not increment

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
