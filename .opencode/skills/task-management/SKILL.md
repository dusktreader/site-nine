---
name: task-management
description: Complete guide for creating, claiming, updating, and closing tasks in the SQLite task database
license: MIT
compatibility: opencode
metadata:
  audience: all-agents
  workflow: task-lifecycle
---

## Important: CLI Tool Usage

**CRITICAL:** This project uses the `s9` CLI executable throughout these instructions.
- **CLI executable:** `s9` (use in bash commands)
- **Python module:** `site_nine` (use in Python imports: `from site_nine import ...`)

All commands in this skill use the `s9` executable via bash. You should NOT attempt to import an `s9` module in Python code.

## What I Do

I provide comprehensive instructions for managing tasks in the s9 task database. This skill covers the complete task lifecycle:

- **Creating tasks** - Add new work items to the database
- **Finding tasks** - Query for available work
- **Claiming tasks** - Take ownership of a task
- **Updating tasks** - Track progress and time
- **Closing tasks** - Mark tasks complete, paused, or blocked

## Task Management Systems

**Unified PM System (Use This)**

The `pm` script provides unified management of tasks, agent sessions, and daemon names:

```bash

# Task commands
s9 task create --title "..." --objective "..." --role Builder --priority HIGH  # Task ID auto-generated
s9 task list --role Builder --active-only
s9 task claim TASK_ID --agent-name "YourName" --agent-id YOUR_ID
s9 task update TASK_ID --notes "..." --actual-hours X.X
s9 task close TASK_ID --status COMPLETE --notes "..."

# See also: mission and name commands
s9 mission start <name> --role <Role> --session-file "..." --task-summary "..."
s9 name suggest <Role>
```

**Documentation:**
- Quick start: `.opencode/scripts/README.md`
- Complete reference: `.opencode/data/README.md`
- Database: `.opencode/data/project.db`

**Legacy System (Preserved for Reference)**

The original task system has been migrated to the new PM system:

```bash
s9 task <command> [options]
```

**Database:** `.opencode/tasks/tasks.db` (SQLite, data migrated to project.db)  
**Artifacts:** `.opencode/tasks/artifacts/*.md` (Markdown files)

> **Note:** All 72 tasks have been migrated to the new PM system. Use `pm` commands for all task operations going forward. The instructions below have been updated to use the new PM system.

---

## Creating Tasks

**When to create tasks:**
- Administrator role adding new work items
- Inspector creating follow-up tasks from reviews
- Architect creating implementation tasks from design

**Command:**
```bash
s9 task create \
  --title "Brief task title" \
  --objective "What this task accomplishes" \
  --role {Administrator|Architect|Builder|Tester|Documentarian|Designer|Inspector|Operator|Historian} \
  --priority {CRITICAL|HIGH|MEDIUM|LOW} \
  [--category "Category name"] \
  [--description "Detailed description"]
```

**Note:** Task IDs are **auto-generated** based on role and priority. You do not need to provide a task ID.

### Task ID Format

**Task IDs are auto-generated** using the format: `PREFIX-PRIORITY-NUMBER`

- **PREFIX**: 3-letter role code (e.g., OPR for Operator, BLD for Builder)
- **PRIORITY**: Single letter (C=Critical, H=High, M=Medium, L=Low)
- **NUMBER**: 4-digit global sequential counter (0001-9999)

**Role Prefixes:**
- `MAN` - Administrator
- `ARC` - Architect  
- `BLD` - Builder
- `TST` - Tester
- `DOC` - Documentarian
- `DES` - Designer
- `INS` - Inspector
- `OPR` - Operator
- `HIS` - Historian

**Examples:**
- `OPR-H-0001` - First high-priority Operator task
- `BLD-C-0005` - Critical Builder task (fifth task overall)
- `DOC-M-0042` - Medium-priority Documentarian task (42nd task overall)

The number increments globally across all roles and priorities, ensuring each task has a unique ID.

### Priority Guidelines

**CRITICAL** - Immediate action required:
- Security vulnerabilities
- Data corruption risks
- Blocking all other work
- Production outages

**HIGH** - Important, do soon:
- Key features for current milestone
- P1 bugs affecting users
- Technical debt causing problems
- Required for next phase

**MEDIUM** - Nice to have:
- Enhancement requests
- Minor features
- Code quality improvements
- Non-urgent bugs

**LOW** - Do when time permits:
- Polish and refinement
- Documentation updates
- Minor improvements
- Nice-to-have features

### Role Assignment

Assign to the role that will do most of the work:

- **Administrator** - Planning, coordination, prioritization
- **Architect** - System design, ADRs, technical direction
- **Builder** - Implementation, coding, integration
- **Tester** - Test writing, validation, QA
- **Documentarian** - Documentation, guides, examples
- **Designer** - UI/UX, visual design
- **Inspector** - Security review, code review, audits
- **Operator** - Deployment, infrastructure, monitoring

### Category Examples

Common categories:
- `Architecture` - System design work
- `Testing` - Test creation and QA
- `Documentation` - Docs and guides
- `Security` - Security reviews and fixes
- `Performance` - Optimization work
- `Bug Fix` - Fixing defects
- `Feature` - New functionality
- `Refactoring` - Code improvement
- `Infrastructure` - Deployment and tooling

### Dependencies

Use `--depends-on` when a task cannot start until another completes:

```bash
# H038 depends on H037
s9 task create H038 \
  --title "Configure Gateway" \
  --priority HIGH \
  --role Operator \
  --objective "Deploy gateway to staging" \
  --depends-on H037
```

**When to use dependencies:**
- Implementation depends on design approval
- Integration depends on component completion
- Deployment depends on code changes
- Testing depends on feature implementation

### Example: Creating a Task

```bash
# Create a high-priority Builder task (ID will be auto-generated)
s9 task create \
  --title "Implement Rate Limiting Middleware" \
  --objective "Add rate limiting to protect API endpoints from abuse" \
  --role Builder \
  --priority HIGH \
  --category "Security" \
  --description "Implement token bucket rate limiting with configurable limits per endpoint"

# Output: ✓ Created task BLD-H-0007: Implement Rate Limiting Middleware
```

**What happens:**
1. ✅ Task ID auto-generated (e.g., BLD-H-0007)
2. ✅ Database entry created in `project.db`
3. ✅ Markdown file created at `.opencode/work/planning/BLD-H-0007.md` with template
4. ✅ Status set to `TODO`

### Validation

The CLI validates:
- ✅ Priority is valid value (CRITICAL, HIGH, MEDIUM, LOW)
- ✅ Role is valid value
- ✅ Task ID is auto-generated correctly
- ✅ All required fields are provided

### After Creating

Verify task was created:
```bash
# Use the auto-generated task ID from the create command output
s9 task show BLD-H-0007
```

---

## Finding Tasks

### List Available Tasks

**By status:**
```bash
s9 task list --status TODO
s9 task list --status UNDERWAY
s9 task list --status TODO,UNDERWAY
```

**By role:**
```bash
s9 task list --role Builder --status TODO
s9 task list --role Administrator --status TODO
```

**By priority:**
```bash
s9 task list --priority CRITICAL,HIGH --status TODO
s9 task list --priority HIGH
```

**Active tasks only:**
```bash
s9 task list --active-only
# Shows TODO and UNDERWAY tasks
```

**By agent:**
```bash
s9 task list --agent "Goibniu"
s9 task list --agent "Ishtar" --status UNDERWAY
```

### View Task Details

```bash
s9 task show H037
```

Shows:
- Full metadata (status, priority, role, category)
- Agent assignment (if claimed)
- Timestamps (created, claimed, closed)
- Time tracking
- Objective and description
- Dependencies
- File path to markdown artifact

### Generate Reports

```bash
# Markdown report
s9 task report --format markdown

# Table format
s9 task report --format table

# JSON for scripts
s9 task report --format json

# Filter by role
s9 task report --role Builder --format markdown
```

---

## Claiming Tasks

**Who claims tasks:**
- Any agent taking ownership of work
- Typically done at start of session

**Command:**
```bash
s9 task claim TASK_ID --agent-name "YourName"
```

### What Happens When You Claim

1. ✅ Status changes: `TODO` → `UNDERWAY`
2. ✅ `agent_name` set to your name
3. ✅ `claimed_at` timestamp recorded
4. ✅ Markdown file header updated

### Agent Name

Use your daemon name from the session:
- ✅ "Goibniu", "Ishtar", "Thoth-iii"
- ❌ Not "Builder" or "Administrator" (that's your role, not name)

### Example: Claiming a Task

```bash

# Find available tasks for your role
s9 task list --role Builder --status TODO

# Output shows H037 is available
# H037 | Implement Rate Limiting Middleware | TODO | HIGH | Builder

# Claim it
s9 task claim H037 --agent-name "Goibniu"

# Verify
s9 task show H037
# Status: UNDERWAY
# Agent: Goibniu
# Claimed: 2026-01-29T22:00:00+00:00
```

### Concurrency Protection

The database prevents race conditions:
- ✅ Only one agent can claim a specific task
- ✅ If two agents try simultaneously, only one succeeds
- ✅ WAL mode allows concurrent reads

### Already Claimed

If task is already claimed:
```bash
s9 task claim H037 --agent-name "Ishtar"
# Error: Task H037 is already claimed by Goibniu
```

Check who claimed it:
```bash
s9 task show H037
```

### Claiming Multiple Tasks

Claim one at a time:
```bash
s9 task claim H037 --agent-name "Goibniu"
s9 task claim H038 --agent-name "Goibniu"
```

**Best practice:** Focus on one task at a time. Only claim multiple if they're small and related.

---

## Updating Tasks

**When to update:**
- Made progress on the task
- Tracked time spent
- Encountered issues
- Changed approach
- At end of work session

**Command:**
```bash
s9 task update TASK_ID \
  [--status STATUS] \
  [--notes "Progress notes"] \
  [--actual-hours X.X] \
  [--category "New category"]
```

### Progress Notes

Use `--notes` to document progress:

```bash
s9 task update H037 --notes "Implemented basic rate limiter, writing tests"

s9 task update H037 --notes "All tests passing, need to add Redis backend"

s9 task update H037 --notes "Blocked on Redis configuration decision"
```

**Notes are appended** to the task's notes field, not replaced.

### Time Tracking

Track actual hours spent:

```bash
s9 task update H037 --actual-hours 2.5

# Add more time later
s9 task update H037 --actual-hours 4.0  # Total is now 4.0, not 2.5+4.0
```

**Note:** `--actual-hours` sets the total, not incremental.

### Changing Status

Usually status changes via claim/close, but you can update manually:

```bash
# Mark as blocked (but keep it UNDERWAY)
s9 task update H037 --status BLOCKED --notes "Waiting for design decision"

# Return to regular progress
s9 task update H037 --status UNDERWAY --notes "Design decision made, resuming"
```

### Example: Updating Progress

```bash

# After 2 hours of work
s9 task update H037 \
  --notes "Implemented token bucket algorithm, added configuration" \
  --actual-hours 2.0

# After 2 more hours
s9 task update H037 \
  --notes "Added tests, all passing" \
  --actual-hours 4.0

# Check progress
s9 task show H037
```

### Update Frequency

**Good practice:**
- Update at least once per work session
- Update when switching tasks
- Update before closing task
- Update when encountering blockers

**Don't overdo it:**
- Not every 15 minutes
- Not for trivial progress

---

## Closing Tasks

**When to close:**
- Task is complete
- Pausing work for later
- Blocked and can't proceed
- Task is cancelled/obsolete

**Command:**
```bash
s9 task close TASK_ID \
  --status {COMPLETE|PAUSED|BLOCKED|ABORTED} \
  --notes "Final summary"
```

### Status Options

**COMPLETE** - Task finished successfully:
- All objectives met
- Tests passing
- Code reviewed and merged
- Documentation updated

**PAUSED** - Temporarily stopped:
- Will resume later
- Low priority, paused for higher priority work
- Waiting for non-blocking dependency

**BLOCKED** - Can't proceed:
- Waiting for external dependency
- Needs decision from stakeholder
- Technical blocker discovered
- Waiting for another task to complete

**ABORTED** - Cancelled:
- Requirements changed
- Task no longer needed
- Duplicate of another task
- Approach was wrong

### Closing Timestamp

When you close a task:
- ✅ `closed_at` timestamp recorded
- ✅ `status` updated
- ✅ Final notes added
- ✅ Markdown file header updated

### Example: Closing Complete Task

```bash

s9 task close H037 \
  --status COMPLETE \
  --notes "Rate limiting implemented and tested. All tests passing. Documentation updated."

# Verify
s9 task show H037
# Status: COMPLETE
# Closed: 2026-01-29T23:30:00+00:00
```

### Example: Closing Blocked Task

```bash
s9 task close H038 \
  --status BLOCKED \
  --notes "Blocked by H037. Can't deploy gateway until rate limiting is complete."
```

### Example: Pausing Task

```bash
s9 task close M019 \
  --status PAUSED \
  --notes "Pausing to work on critical security issue C003. Will resume after."
```

### Example: Aborting Task

```bash
s9 task close L012 \
  --status ABORTED \
  --notes "Task obsolete after architecture change in H029. No longer needed."
```

### Resuming Paused/Blocked Tasks

To resume a paused or blocked task:

1. **Claim it again** (if not already yours):
   ```bash
   s9 task claim H038 --agent-name "YourName"
   ```

2. **Update status** back to UNDERWAY:
   ```bash
   s9 task update H038 --status UNDERWAY --notes "Blocker resolved, resuming work"
   ```

---

## Task Lifecycle Summary

```
TODO (created)
  ↓
  claim → UNDERWAY (working)
  ↓                    ↓
  update progress      update → BLOCKED (temp)
  ↓                    ↓
  close → COMPLETE     update → UNDERWAY (resume)
          PAUSED               ↓
          BLOCKED              close → COMPLETE
          ABORTED
```

---

## Common Workflows

### Workflow 1: Complete a Task End-to-End

```bash

# 1. Find work
s9 task list --role Builder --status TODO

# 2. Claim task
s9 task claim H037 --agent-name "Goibniu"

# 3. Work on it (update periodically)
s9 task update H037 --notes "Made progress on X" --actual-hours 2.0

# 4. Close when done
s9 task close H037 --status COMPLETE --notes "All tests passing, code reviewed"
```

### Workflow 2: Pause for Higher Priority

```bash
# Working on M019
s9 task update M019 --notes "50% complete"

# Critical issue appears
s9 task close M019 --status PAUSED --notes "Pausing for C003"

# Work on C003
s9 task claim C003 --agent-name "Goibniu"
s9 task close C003 --status COMPLETE --notes "Security issue fixed"

# Resume M019
s9 task update M019 --status UNDERWAY --notes "Resuming after C003"
```

### Workflow 3: Hit a Blocker

```bash
# Working on H038
s9 task update H038 --notes "Need H037 to be complete first"

# Mark as blocked
s9 task close H038 --status BLOCKED --notes "Blocked by H037"

# Work on something else

# When H037 is complete
s9 task update H038 --status UNDERWAY --notes "H037 complete, resuming"
```

### Workflow 4: Create Multiple Related Tasks

```bash
# Create design task
s9 task create --title "Design Gateway" --objective "Design gateway architecture" --role Architect --priority HIGH

# Create implementation task
s9 task create --title "Implement Gateway" --objective "Implement gateway" --role Builder --priority HIGH

# Create testing task  
s9 task create --title "Test Gateway" --objective "Test gateway" --role Tester --priority HIGH
```

---

## Tips and Best Practices

### Creating Tasks

- ✅ Use clear, action-oriented titles
- ✅ Write specific objectives (not "fix stuff")
- ✅ Assign appropriate priority
- ✅ Set dependencies when they exist
- ✅ Check for next available ID in priority range
- ❌ Don't create tasks for trivial work (<1 hour)
- ❌ Don't create duplicate tasks

### Claiming Tasks

- ✅ Claim one task at a time (stay focused)
- ✅ Check dependencies before claiming
- ✅ Use your daemon name, not role name
- ❌ Don't claim tasks you can't start immediately
- ❌ Don't claim tasks outside your role (usually)

### Updating Tasks

- ✅ Update at least once per session
- ✅ Track time accurately
- ✅ Document blockers immediately
- ✅ Note decisions made
- ❌ Don't skip updates for days
- ❌ Don't write novels (keep notes concise)

### Closing Tasks

- ✅ Use correct status (COMPLETE vs PAUSED vs BLOCKED)
- ✅ Write clear closing notes
- ✅ Close tasks before ending session
- ✅ Update actual hours before closing
- ❌ Don't leave tasks UNDERWAY forever
- ❌ Don't mark incomplete work as COMPLETE

---

## Troubleshooting

### "Task not found"
- Check task ID spelling and case
- Verify task exists: `s9 task list | grep TASK_ID`

### "Task already claimed"
- Someone else is working on it
- Check: `s9 task show TASK_ID`
- Choose a different task or coordinate

### "Database is locked"
- Another process is writing (rare with WAL mode)
- Wait a moment and retry
- Check for stuck processes: `ps aux | grep tasks.py`

### "CHECK constraint failed"
- You used invalid status/priority/role value
- See valid values in this skill
- Check your command syntax

### "Dependency not found"
- Task ID in `--depends-on` doesn't exist
- Check task IDs: `s9 task list`
- Fix the dependency task ID

### Can't find tasks.py
- Ensure you're in `.opencode/tasks/` directory
- Check file exists: `ls tasks.py`
- Make it executable: `chmod +x tasks.py`

---

## Valid Values Reference

### Status Values
- `TODO` - Not started
- `UNDERWAY` - In progress
- `BLOCKED` - Can't proceed
- `PAUSED` - Temporarily stopped
- `REVIEW` - Awaiting review
- `COMPLETE` - Finished
- `ABORTED` - Cancelled

### Priority Values
- `CRITICAL` - Immediate action required
- `HIGH` - Important, do soon
- `MEDIUM` - Nice to have
- `LOW` - Do when time permits

### Role Values
- `Administrator` - Planning, coordination
- `Architect` - Design, ADRs
- `Builder` - Implementation
- `Tester` - Testing, QA
- `Documentarian` - Documentation
- `Designer` - UI/UX design
- `Inspector` - Reviews, audits
- `Operator` - Deployment, infrastructure

---

## See Also

**New PM System:**
- `.opencode/scripts/README.md` - Quick start guide for unified PM system
- `.opencode/data/README.md` - Complete PM system reference

**Legacy Task System:**
- `.opencode/tasks/README.md` - Overview of original task system (technical details)
- `.opencode/tasks/schema.sql` - Original database schema
- `.opencode/tasks/artifacts/` - Task markdown files

**Related Commands:**
- `/dismiss` command - Automatically closes tasks at session end
