---
name: task-update
description: Update task progress, notes, and time tracking using OpenCode tools
license: MIT
compatibility: opencode
metadata:
  audience: all-agents
  workflow: task-progress
---

## What I Do

I provide comprehensive instructions for updating task progress using the OpenCode `task_update` tool. Use this skill to track your work, document progress, and record time spent on tasks.

## When to Update

- Made progress on the task
- Tracked time spent
- Encountered issues or blockers
- Changed approach or strategy
- At end of work session
- Before switching to another task
- Before closing the task

## Tool Syntax

Use the `task_update` tool to update task progress:

```
task_update(
  task_id="TASK-ID",
  status="STATUS",
  notes="Progress notes"  # Optional
)
```

**Required:**
- `task_id` - The task to update (e.g., "ENG-H-0037")
- `status` - New status for the task

**Optional:**
- `notes` - Progress notes to append

The tool automatically:
- Looks up your current mission from the OpenCode session context
- Updates the task in the database
- Updates the markdown file in `.opencode/work/tasks/`
- Records timestamp for the update
- Appends notes (doesn't replace existing notes)

## Progress Notes

Use the `notes` parameter to document progress:

```
task_update(
  task_id="ENG-H-0037",
  status="UNDERWAY",
  notes="Implemented basic rate limiter, writing tests"
)

task_update(
  task_id="ENG-H-0037",
  status="UNDERWAY",
  notes="All tests passing, need to add Redis backend"
)

task_update(
  task_id="ENG-H-0037",
  status="UNDERWAY",
  notes="Waiting on Redis configuration decision"
)
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
```
task_update(task_id="ENG-H-0037", status="UNDERWAY", notes="Completed API endpoint implementation. Starting integration tests.")

task_update(task_id="ENG-H-0037", status="UNDERWAY", notes="Refactored auth middleware for better testability. 85% test coverage achieved.")

task_update(task_id="ENG-H-0037", status="UNDERWAY", notes="Discovered performance issue with large datasets. Investigating caching options.")

task_update(task_id="ENG-H-0037", status="UNDERWAY", notes="Met with architect - decided to use Redis instead of in-memory cache.")
```

**Avoid:**
- Overly verbose details
- Line-by-line code changes (use git commits for that)
- Too generic ("made progress")

## Changing Status

Usually status changes via claim/close tools, but you can update manually:

```
# Resume work after being away
task_update(
  task_id="ENG-H-0037",
  status="UNDERWAY",
  notes="Resuming work after meeting"
)

# Mark as complete (though usually you use task_close tool)
task_update(
  task_id="ENG-H-0037",
  status="COMPLETE",
  notes="Work finished"
)
```

**Valid status values:**
- `TODO` - Not started
- `UNDERWAY` - In progress
- `COMPLETE` - Finished
- `ABORTED` - Cancelled

**Note:** Usually you should use:
- `task_claim` tool to set UNDERWAY
- `task_close` tool to set COMPLETE or ABORTED

## Example: Updating Progress

```
# After making progress
task_update(
  task_id="ENG-H-0037",
  status="UNDERWAY",
  notes="Implemented token bucket algorithm, added configuration"
)

# After more progress
task_update(
  task_id="ENG-H-0037",
  status="UNDERWAY",
  notes="Added tests, all passing. Ready for review."
)

# Check progress with task_show tool
task_show(task_id="ENG-H-0037")
```

## Example: Documenting a Blocker

```
task_update(
  task_id="ENG-H-0037",
  status="UNDERWAY",
  notes="Waiting on Redis configuration decision. Need architect approval for caching strategy."
)
```

## Example: Multiple Updates in Session

```
# Start of work session
task_update(
  task_id="ENG-H-0037",
  status="UNDERWAY",
  notes="Starting implementation of rate limiting"
)

# Mid-session
task_update(
  task_id="ENG-H-0037",
  status="UNDERWAY",
  notes="Basic rate limiter working. Writing tests."
)

# End of session
task_update(
  task_id="ENG-H-0037",
  status="UNDERWAY",
  notes="All tests passing. Will add Redis backend tomorrow."
)
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

When you call the `task_update` tool:

1. ✅ Database updated immediately
2. ✅ Markdown file updated in `.opencode/work/tasks/`
3. ✅ Timestamp recorded for update
4. ✅ Notes appended (not replaced)
5. ✅ Mission association maintained automatically via session context

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
- ❌ Don't update status manually (prefer task_claim/task_close tools)

## Troubleshooting

### "Task not found"
- Check task ID spelling and case
- Verify task exists with the `task_show` tool

### "Invalid status value"
- Check spelling and case
- See valid status values above
- Consider using task_claim/task_close tools instead

### "Task not claimed"
- You can only update tasks you've claimed
- Claim it first with the `task_claim` tool

### "Status is required"
- The `status` parameter is required
- Provide a valid status value (see valid statuses above)

## After Updating

Verify your update with the `task_show` tool:
```
task_show(task_id="ENG-H-0037")
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
