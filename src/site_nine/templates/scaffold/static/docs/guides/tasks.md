# Task Management Guide

Essential reference information for the s9 task management system.


## What This Guide Covers

This guide contains reference information that applies across all task workflows:

- Task ID format and structure
- Valid status values and when to use them
- Priority levels and guidelines
- Task lifecycle overview

**For specific workflows**, use the focused skills:
- Creating tasks → `task-create` skill
- Finding tasks → `task-query` skill
- Claiming tasks → `task-claim` skill
- Updating tasks → `task-update` skill
- Closing tasks → `task-close` skill
- Overview → `task-management` skill


## Task ID Format

Task IDs are **auto-generated** when you create a task using the format:

```
PREFIX-PRIORITY-NUMBER
```


### Components

**PREFIX** (3 letters)

- Role code identifying which role owns the task
- See Role Values section below for full list


**PRIORITY** (1 letter)

- `C` = Critical
- `H` = High
- `M` = Medium
- `L` = Low


**NUMBER** (4 digits)

- Global sequential counter: 0001-9999
- Increments across ALL roles and priorities
- Ensures every task ID is unique


### Examples

- `ENG-H-0037` - Engineer, High priority, task #37
- `OPR-C-0003` - Operator, Critical priority, task #3
- `DOC-M-0142` - Documentarian, Medium priority, task #142
- `ARC-H-0089` - Architect, High priority, task #89


### How Task IDs Are Generated

When you run:
```bash
s9 task create --role Engineer --priority HIGH --title "..."
```

The system:
1. Maps role → prefix (`Engineer` → `ENG`)
2. Maps priority → letter (`HIGH` → `H`)
3. Gets next available number from database (global counter)
4. Combines into ID: `ENG-H-0037`

You **cannot** specify a custom task ID - the system generates it.


## Status Values

Tasks move through these statuses during their lifecycle:


### TODO

- **Meaning:** Task created but not started
- **When set:** Automatically on task creation
- **Next status:** UNDERWAY (via `s9 task claim`)


### UNDERWAY

- **Meaning:** Someone is actively working on this task
- **When set:** When task is claimed
- **Next status:** COMPLETE, PAUSED, BLOCKED, or ABORTED (via `s9 task close`)


### BLOCKED

- **Meaning:** Cannot proceed due to external dependency
- **When set:** Via `s9 task close --status BLOCKED`
- **Use when:**
  - Waiting for another task to complete
  - Needs decision from stakeholder
  - Technical blocker discovered
  - Missing required resources
- **Next status:** UNDERWAY (when blocker resolved)


### PAUSED

- **Meaning:** Temporarily stopped, will resume later
- **When set:** Via `s9 task close --status PAUSED`
- **Use when:**
  - Paused for higher priority work
  - Waiting for non-blocking dependency
  - Low priority, postponing
- **Next status:** UNDERWAY (when resuming)


### REVIEW

- **Meaning:** Work complete, awaiting review/approval
- **When set:** Via `s9 task update --status REVIEW`
- **Use when:**
  - Code written, PR created
  - Need review before marking complete
- **Next status:** COMPLETE or UNDERWAY (if changes needed)


### COMPLETE

- **Meaning:** Task finished successfully
- **When set:** Via `s9 task close --status COMPLETE`
- **Use when:**
  - All objectives met
  - Tests passing
  - Code reviewed and merged
  - Documentation updated
- **Terminal status** (task is done)


### ABORTED

- **Meaning:** Task cancelled, will not be completed
- **When set:** Via `s9 task close --status ABORTED`
- **Use when:**
  - Requirements changed
  - Task no longer needed
  - Duplicate of another task
  - Approach was wrong
- **Terminal status** (task is done)


## Priority Values


### CRITICAL

**When to use:**

- Security vulnerabilities
- Data corruption risks
- Blocking all other work
- Production outages

**Response time:** Immediate action required

**Examples:**

- Production database is down
- Security breach detected
- Critical bug affecting all users


### HIGH

**When to use:**

- Key features for current milestone
- P1 bugs affecting users
- Technical debt causing problems
- Required for next phase

**Response time:** Important, do soon (within days)

**Examples:**

- Major feature for upcoming release
- Bug affecting significant user base
- Dependency blocking other work


### MEDIUM

**When to use:**

- Enhancement requests
- Minor features
- Code quality improvements
- Non-urgent bugs

**Response time:** Nice to have (within weeks)

**Examples:**

- UI polish
- Minor feature addition
- Refactoring for maintainability


### LOW

**When to use:**

- Polish and refinement
- Documentation updates
- Minor improvements
- Nice-to-have features

**Response time:** Do when time permits

**Examples:**

- Typo fixes
- README improvements
- Minor optimizations


## Role Values

Each task is assigned to a role that will do most of the work:


### Role Prefixes

| Role          | Prefix | Focus Area                                |
|---------------|--------|-------------------------------------------|
| Administrator | `ADM`  | Planning, coordination, prioritization    |
| Architect     | `ARC`  | System design, ADRs, technical direction  |
| Engineer      | `ENG`  | Implementation, coding, integration       |
| Tester        | `TST`  | Test writing, validation, QA              |
| Documentarian | `DOC`  | Documentation, guides, examples           |
| Designer      | `DES`  | UI/UX, visual design                      |
| Inspector     | `INS`  | Security review, code review, audits      |
| Operator      | `OPR`  | Deployment, infrastructure, monitoring    |
| Historian     | `HIS`  | Recording decisions, maintaining history  |

**See `.opencode/docs/roles/README.md` for detailed role descriptions.**


## Task Lifecycle

Tasks move through states based on the actions you take:


### State Transitions

**Creating and claiming work:**
- `s9 task create` → Task starts in **TODO** state
- `s9 task claim` → **TODO** → **UNDERWAY** (start working)

**Working on tasks:**
- `s9 task update` → **UNDERWAY** → **UNDERWAY** (track progress)

**Finishing work (terminal states):**
- `s9 task close --status COMPLETE` → **UNDERWAY** → **COMPLETE** (done successfully)
- `s9 task close --status ABORTED` → **UNDERWAY** → **ABORTED** (cancelled, won't complete)

**Pausing work (non-terminal):**
- `s9 task close --status PAUSED` → **UNDERWAY** → **PAUSED** (temporarily stopped)
- `s9 task claim` → **PAUSED** → **UNDERWAY** (resume paused work)

**Blocking work (non-terminal):**
- `s9 task close --status BLOCKED` → **UNDERWAY** → **BLOCKED** (can't proceed due to blocker)
- `s9 task claim` → **BLOCKED** → **UNDERWAY** (resume after blocker removed)

**Terminal states:** COMPLETE and ABORTED are final - tasks in these states cannot be resumed.


### Typical Flow

**Happy path:**

```
TODO → UNDERWAY → COMPLETE
```

**With review:**

```
TODO → UNDERWAY → REVIEW → COMPLETE
```

**Hit blocker:**

```
TODO → UNDERWAY → BLOCKED → UNDERWAY → COMPLETE
```

**Pause for priority:**

```
TODO → UNDERWAY → PAUSED → UNDERWAY → COMPLETE
```


## Quick Command Reference


### Finding Work

```bash
# Find available work for your role
s9 task list --role YourRole --status TODO

# Find high-priority work
s9 task list --priority CRITICAL,HIGH --status TODO

# See what you're working on
s9 task list --agent "YourName" --status UNDERWAY
```


### Working on Tasks

```bash
# Claim a task
s9 task claim TASK_ID --agent-name "YourName"

# Update progress
s9 task update TASK_ID --notes "Progress made" --actual-hours 2.0

# Close when done
s9 task close TASK_ID --status COMPLETE --notes "Task complete"
```


### Creating Tasks

```bash
# Create new task (ID auto-generated)
s9 task create \
  --title "Task Title" \
  --objective "What it accomplishes" \
  --role Engineer \
  --priority HIGH \
  --category "Category"
```


### Viewing Details

```bash
# Show full task details
s9 task show TASK_ID

# Generate report
s9 task report --format markdown
```


## Database Location

All task data is stored in:

```
.opencode/data/project.db
```

This SQLite database contains:

- Tasks (status, priority, role, times)
- Agents/daemons
- Possessions
- Task relationships

**See `.opencode/data/README.md` for complete database reference.**


## See Also


**Skills (for specific workflows):**

- `task-create` - Creating new tasks
- `task-query` - Finding and listing tasks
- `task-claim` - Claiming tasks to work on
- `task-update` - Tracking progress
- `task-close` - Completing/pausing/blocking tasks
- `task-management` - Overview and quick reference

**Guides:**

- `.opencode/docs/guides/task-sizing.md` - How to break down and size tasks
- `.opencode/docs/roles/README.md` - Detailed role descriptions

**Documentation:**

- `.opencode/data/README.md` - Complete s9 system reference
