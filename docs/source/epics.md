# Epics

Epics are organizational containers for grouping related tasks under larger initiatives. They help you manage complex
projects by breaking them down into manageable subtasks while maintaining visibility of overall progress.


## What are epics?

An **epic** represents a high-level project or initiative composed of multiple subtasks. For example, "User
Authentication System" might be an epic containing tasks for architecture design, API implementation, frontend
integration, testing, and documentation.

**Key characteristics:**

- **Purely organizational** - Epics group tasks but aren't assigned to agents or sessions
- **One task, one epic** - Tasks belong to at most one epic (or remain standalone)
- **Auto-computed status** - Epic status updates automatically based on subtask states
- **Database-driven** - Database is the source of truth; markdown files are generated artifacts
- **Progress tracking** - Epics show completion percentage and task counts


## Epic lifecycle

### Creating an epic

Create a new epic with a title and priority:

```bash
s9 epic create --title "User Authentication System" --priority HIGH
```

Add a description for context:

```bash
s9 epic create \
  --title "User Authentication System" \
  --priority HIGH \
  --description "Implement complete user authentication including login, registration, and password reset"
```

**Output:**
```
✓ Created epic EPC-H-0001
  Title: User Authentication System
  Priority: HIGH
  Status: TODO
  File: .opencode/work/epics/EPC-H-0001.md
```


### Adding tasks to an epic

**Create new tasks linked to an epic:**

```bash
s9 task create \
  --title "Design authentication architecture" \
  --role Architect \
  --priority HIGH \
  --epic EPC-H-0001
```

**Link existing tasks:**

```bash
s9 task link ARC-H-0015 EPC-H-0001
```

**Unlink tasks:**

```bash
s9 task unlink ARC-H-0015
```


### Tracking progress

View epic details and progress:

```bash
s9 epic show EPC-H-0001
```

**Example output:**
```
Epic EPC-H-0001: User Authentication System

Status: 🚧 UNDERWAY
Priority: HIGH
Created: 2026-02-04 10:30:00
Updated: 2026-02-04 15:45:00

Progress: 3/5 tasks complete (60%)
[████████████████████░░░░░░░░░░] 60%

Subtasks:
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Task ID    ┃ Title                          ┃ Status     ┃ Role         ┃ Priority ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ ARC-H-0015 │ Design auth architecture       │ ✅ COMPLETE│ Architect    │ HIGH     │
│ ENG-H-0016 │ Implement login endpoint       │ ✅ COMPLETE│ Engineer      │ HIGH     │
│ ENG-H-0017 │ Implement registration         │ 🔵 UNDERWAY│ Engineer      │ HIGH     │
│ TST-M-0018 │ Write auth tests               │ ⬜ TODO    │ Tester       │ MEDIUM   │
│ DOC-M-0019 │ Document auth API              │ ⬜ TODO    │ Documentarian│ MEDIUM   │
└────────────┴────────────────────────────────┴────────────┴──────────────┴──────────┘

Description:
Implement complete user authentication including login, registration, and password reset
```


### Updating epics

Update epic metadata:

```bash
s9 epic update EPC-H-0001 --title "User Authentication and Authorization"
s9 epic update EPC-H-0001 --priority CRITICAL
s9 epic update EPC-H-0001 --description "Extended scope to include role-based access control"
```


### Completing epics

Epics automatically transition to COMPLETE status when all subtasks reach COMPLETE status. No manual completion is
needed!

When the last task is completed:
```
✓ Task ENG-H-0017 closed with status: COMPLETE

📋 Epic EPC-H-0001 status changed: UNDERWAY → COMPLETE
```


### Aborting epics

If an epic becomes obsolete or requirements change, abort it:

```bash
s9 epic abort EPC-H-0001 --reason "Requirements changed; switching to OAuth instead"
```

**This operation:**

- Sets epic status to ABORTED
- Cascades to ALL subtasks (sets them to ABORTED)
- Requires confirmation unless you use `--yes`
- Records the abort reason
- Prevents future auto-updates to the epic

**Example confirmation prompt:**
```
⚠️  WARNING: Aborting epic will also abort ALL 5 subtasks

Epic: EPC-H-0001 - User Authentication System
Subtasks that will be aborted:
  • ARC-H-0015 - Design auth architecture
  • ENG-H-0016 - Implement login endpoint
  • ENG-H-0017 - Implement registration
  • TST-M-0018 - Write auth tests
  • DOC-M-0019 - Document auth API

Abort reason: Requirements changed; switching to OAuth instead

Continue? [y/N]:
```


## Epic statuses

Epics have four possible statuses that auto-update based on subtask states:

### TODO (📋)

All subtasks are TODO or ABORTED. No active work has started.

**Transition to UNDERWAY:** When any subtask changes to UNDERWAY, BLOCKED, REVIEW, or PAUSED.

### UNDERWAY (🚧)

At least one subtask is actively being worked on (UNDERWAY, BLOCKED, REVIEW, or PAUSED status).

**Transition to COMPLETE:** When all subtasks reach COMPLETE status.

**Transition back to TODO:** When all active tasks are completed or aborted, leaving only TODO tasks.

### COMPLETE (✅)

All subtasks have been completed. The `completed_at` timestamp is automatically set.

**This is a terminal state** - completed epics don't transition to other statuses.

### ABORTED (❌)

Manually aborted via `s9 epic abort`. All subtasks are also aborted.

**This is a protected terminal state** - aborted epics never auto-update, even if subtask statuses change.


## Epic IDs

Epics use a structured ID format that encodes priority:

**Format:** `EPC-[P]-[NNNN]`

**Components:**

- `EPC` - Epic prefix (constant)
- `[P]` - Priority code (single letter)
    - `C` = CRITICAL
    - `H` = HIGH
    - `M` = MEDIUM
    - `L` = LOW
- `[NNNN]` - Sequential 4-digit number (padded with zeros)

**Examples:**

- `EPC-H-0001` - First HIGH priority epic
- `EPC-C-0015` - Epic #15 (CRITICAL priority)
- `EPC-M-0042` - Epic #42 (MEDIUM priority)

The priority prefix makes it easy to identify critical work at a glance.


## Working with epics

### Listing epics

View all epics:

```bash
s9 epic list
```

Filter by status:

```bash
s9 epic list --status TODO
s9 epic list --status UNDERWAY
s9 epic list --status COMPLETE
```

Filter by priority:

```bash
s9 epic list --priority HIGH
s9 epic list --priority CRITICAL
```

Combine filters:

```bash
s9 epic list --status UNDERWAY --priority HIGH
```

**Example output:**
```
                                    Epics
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┓
┃ ID         ┃ Title                      ┃ Status     ┃ Priority ┃ Progress ┃ Created            ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━┩
│ EPC-H-0001 │ User Authentication System │ 🚧 UNDERWAY│ HIGH     │ 3/5 (60%)│ 2026-02-04 10:30:00│
│ EPC-H-0002 │ API Documentation          │ 📋 TODO    │ HIGH     │ 0/3 (0%) │ 2026-02-04 11:15:00│
│ EPC-M-0003 │ UI Refactoring             │ 🚧 UNDERWAY│ MEDIUM   │ 2/8 (25%)│ 2026-02-04 12:00:00│
└────────────┴────────────────────────────┴────────────┴──────────┴──────────┴────────────────────┘
```


### Dashboard integration

The main dashboard shows active epics:

```bash
s9 dashboard
```

View epic-specific dashboard:

```bash
s9 dashboard --epic EPC-H-0001
```

**Epic dashboard output:**
```
📦 Epic: EPC-H-0001 - User Authentication System
Status: 🚧 UNDERWAY | Priority: HIGH | Progress: 3/5 (60%)
[████████████████████░░░░░░░░░░] 60%

Subtasks:
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Task ID    ┃ Title                          ┃ Status     ┃ Role         ┃ Priority ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ ARC-H-0015 │ Design auth architecture       │ ✅ COMPLETE│ Architect    │ HIGH     │
│ ENG-H-0016 │ Implement login endpoint       │ ✅ COMPLETE│ Engineer      │ HIGH     │
│ ENG-H-0017 │ Implement registration         │ 🔵 UNDERWAY│ Engineer      │ HIGH     │
│ TST-M-0018 │ Write auth tests               │ ⬜ TODO    │ Tester       │ MEDIUM   │
│ DOC-M-0019 │ Document auth API              │ ⬜ TODO    │ Documentarian│ MEDIUM   │
└────────────┴────────────────────────────────┴────────────┴──────────────┴──────────┘
```


### Epic markdown files

Each epic has a markdown file at `.opencode/work/epics/{EPIC_ID}.md`. These files are automatically generated and
updated.

**File structure:**

```markdown
# Epic EPC-H-0001: User Authentication System

**Status:** 🚧 UNDERWAY
**Priority:** HIGH
**Created:** 2026-02-04 10:30:00
**Updated:** 2026-02-04 15:45:00

## Progress

**Tasks:** 3/5 complete (60%)
[████████████████████░░░░░░░░░░] 60%

## Subtasks

| Task ID | Title | Status | Role | Priority |
|---------|-------|--------|------|----------|
| ARC-H-0015 | Design auth architecture | ✅ COMPLETE | Architect | HIGH |
| ENG-H-0016 | Implement login endpoint | ✅ COMPLETE | Engineer | HIGH |
| ENG-H-0017 | Implement registration | 🔵 UNDERWAY | Engineer | HIGH |
| TST-M-0018 | Write auth tests | ⬜ TODO | Tester | MEDIUM |
| DOC-M-0019 | Document auth API | ⬜ TODO | Documentarian | MEDIUM |

## Description

Implement complete user authentication including login, registration, and password reset

## Goals

- Secure user authentication with JWT tokens
- Password reset flow via email
- Account registration with email verification
- Session management

## Success Criteria

- All auth endpoints fully implemented and tested
- Security audit passed
- Documentation complete
- Integration tests passing

## Notes

[Epic-level notes, decisions, blockers, and context]
```

**You can edit these sections manually:**

- Description
- Goals
- Success Criteria
- Notes

**These sections are auto-generated (your edits will be overwritten):**

- Header (status, priority, timestamps)
- Progress
- Subtasks table


### Syncing epic files

Epic markdown files automatically sync on most operations, but you can manually regenerate them:

```bash
# Sync all epics
s9 epic sync

# Sync specific epic
s9 epic sync --epic EPC-H-0001
```


## Best practices

### When to use epics

**Good use cases:**

- Features requiring multiple roles (architect → engineer → tester → documentarian)
- Projects spanning multiple weeks
- Work requiring coordination across 3+ tasks
- Initiatives with clear milestones and deliverables

**Not necessary for:**

- Single-task work items
- Quick fixes or small changes
- Tasks that naturally complete in isolation

### Epic naming

Use clear, descriptive titles that convey the business value:

**Good names:**

- "User Authentication System"
- "Database Migration to PostgreSQL"
- "API Rate Limiting Implementation"
- "Customer Dashboard Redesign"

**Less helpful:**

- "Sprint 3 Work"
- "Backend Tasks"
- "Improvements"

### Breaking down epics

Aim for 3-10 tasks per epic. If you have more than 10 tasks, consider:

- Splitting into multiple epics
- Grouping very small tasks together
- Creating sub-epics (though this isn't directly supported, you can create separate epics with related names)

### Priority alignment

Epic priority doesn't automatically determine subtask priority. You can have:

- HIGH priority epic with mix of HIGH and MEDIUM tasks
- CRITICAL epic with LOW priority documentation tasks

Set task priorities based on when they need to be completed, not just the epic's overall priority.


## Common workflows

### Planning a new feature

1. Create the epic:
   ```bash
   s9 epic create --title "User Dashboard" --priority HIGH
   ```

2. Break down into tasks:
   ```bash
   s9 task create --title "Design dashboard wireframes" --role Designer --priority HIGH --epic EPC-H-0001
   s9 task create --title "Implement dashboard backend" --role Engineer --priority HIGH --epic EPC-H-0001
   s9 task create --title "Implement dashboard frontend" --role Engineer --priority HIGH --epic EPC-H-0001
   s9 task create --title "Write dashboard tests" --role Tester --priority MEDIUM --epic EPC-H-0001
   s9 task create --title "Document dashboard features" --role Documentarian --priority MEDIUM --epic EPC-H-0001
   ```

3. Set up dependencies if needed:
   ```bash
   s9 task add-dependency ENG-H-0016 ARC-H-0015  # Backend depends on architecture
   ```

4. Monitor progress:
   ```bash
   s9 dashboard --epic EPC-H-0001
   ```

### Converting standalone tasks to epic

If you realize related tasks should be grouped:

1. Create the epic:
   ```bash
   s9 epic create --title "Payment Integration" --priority HIGH
   ```

2. Link existing tasks:
   ```bash
   s9 task link ENG-H-0023 EPC-H-0002
   s9 task link TST-M-0024 EPC-H-0002
   s9 task link DOC-M-0025 EPC-H-0002
   ```

### Reorganizing work

Move task from one epic to another:

```bash
# Unlink from old epic
s9 task unlink ENG-H-0023

# Link to new epic
s9 task link ENG-H-0023 EPC-H-0003
```


## Technical details

### Database structure

Epics are stored in the `epics` table with these fields:

- `id` - Epic ID (EPC-[P]-[NNNN])
- `title` - Epic title
- `description` - Optional description
- `status` - TODO, UNDERWAY, COMPLETE, or ABORTED
- `priority` - CRITICAL, HIGH, MEDIUM, or LOW
- `aborted_reason` - Reason if manually aborted
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp
- `completed_at` - Completion timestamp (auto-set)
- `aborted_at` - Abort timestamp
- `file_path` - Path to markdown file

Tasks link to epics via the `epic_id` foreign key field.

### Auto-status computation

Epic status is computed from subtask states via database triggers:

**Status logic:**

- **All subtasks COMPLETE** → Epic becomes COMPLETE
- **Any subtask is UNDERWAY/BLOCKED/REVIEW/PAUSED** → Epic becomes UNDERWAY
- **All subtasks TODO or ABORTED** → Epic stays/returns to TODO
- **Manually aborted** → Status locked to ABORTED (no auto-updates)

**Triggers fire on:**

- Task status changes
- Tasks added to epic
- Tasks removed from epic

This ensures epic status always reflects the current state of work without manual updates.

### Cascade operations

Aborting an epic cascades to all subtasks:

```sql
-- When epic is aborted
UPDATE tasks 
SET status = 'ABORTED', 
    aborted_at = datetime('now'),
    updated_at = datetime('now')
WHERE epic_id = 'EPC-H-0001';
```

This ensures organizational consistency - if an epic is cancelled, all its work items reflect that decision.


## CLI reference

Quick reference of all epic commands:

```bash
# Create
s9 epic create --title "NAME" --priority PRIORITY [--description DESC]

# List
s9 epic list [--status STATUS] [--priority PRIORITY]

# Show
s9 epic show EPIC_ID

# Update
s9 epic update EPIC_ID [--title TITLE] [--description DESC] [--priority PRIORITY]

# Abort
s9 epic abort EPIC_ID --reason REASON [--yes]

# Sync
s9 epic sync [--epic EPIC_ID]

# Task linking
s9 task create --epic EPIC_ID [other options...]
s9 task link TASK_ID EPIC_ID
s9 task unlink TASK_ID

# Dashboard
s9 dashboard --epic EPIC_ID
```

See the [CLI Reference](cli/overview.md) for detailed parameter descriptions and examples.
