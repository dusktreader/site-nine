# Complete CLI Reference

Comprehensive alphabetical reference for all s9 commands with full options and examples.

For a categorized overview, see [CLI Overview](overview.md).  
For human-focused workflows, see [For Humans](for-humans.md).  
For agent integration patterns, see [For Agents](for-agents.md).

## Global Options

```bash
s9 --help              # Show help
s9 --version           # Show version (via 'version' command)
```

## Commands

### `s9 version`

Show the installed s9 version.

```bash
s9 version
```

**Output:**
```
s9 version 0.1.0
```

---

### `s9 init`

Initialize `.opencode` structure in the current directory.

```bash
s9 init [OPTIONS]
```

**Options:**
- `--config FILE, -c FILE` - Path to YAML config file
- `--force, -f` - Overwrite existing `.opencode` directory

**Examples:**

Interactive wizard:
```bash
cd my-project
s9 init
```

With config file:
```bash
s9 init --config s9.yaml
```

Force overwrite:
```bash
s9 init --force
```

**What it does:**
1. Creates `.opencode/` directory
2. Initializes SQLite database at `.opencode/data/project.db`
3. Populates 145 daemon names
4. Renders 19+ templates (possessions, docs, procedures, README, config)
5. Creates empty directories (possessions, planning, scripts)

---

### `s9 dashboard`

Show project overview with active personas and task summary.

```bash
s9 dashboard [OPTIONS]
```

**Options:**
- `--epic EPIC_ID, -e EPIC_ID` - Show epic-specific dashboard
- `--role ROLE, -r ROLE` - Filter by role

**Output includes:**
- Quick stats (active personas, total tasks, in progress, completed)
- Active epics (top 5 TODO/UNDERWAY)
- Active missions table
- Task summary by status
- Recent tasks (last 10)

**Examples:**

Full dashboard:
```bash
s9 dashboard
```

Epic-specific view:
```bash
s9 dashboard --epic EPC-H-0001
```

Role-filtered view:
```bash
s9 dashboard --role Engineer
```

**Example output:**
```
╭─────────────────────────────────────────╮
│ s9 Dashboard - my-project          │
╰─────────────────────────────────────────╯

Quick Stats:
  Active personas: 2
  Total tasks: 15
  In progress: 3
  Completed: 10

[Active Missions table]
[Task Summary table]
[Recent Tasks table]
```

---

### `s9 doctor`

Run infrastructure health checks and validate data integrity.

```bash
s9 doctor [OPTIONS]
```

**Options:**
- `--fix` - Apply fixes automatically for safe issues
- `--verbose, -v` - Show detailed output

**What it checks:**

Infrastructure:
- Database file existence
- Database integrity (SQLite PRAGMA integrity_check)
- Gitignore pattern validation
- Backup file detection
- SQLite temporary file detection

Data integrity:
- Invalid foreign key references
- Inconsistent task states
- Possession data issues
- Incorrect usage counters
- Missing files referenced in database
- Orphaned task dependencies
- Abandoned work detection

**Examples:**

Run health checks (report only):
```bash
s9 doctor
```

Run with verbose output:
```bash
s9 doctor --verbose
```

Fix issues automatically:
```bash
s9 doctor --fix
```

---

### `s9 possession list`

List possessions with optional filters.

```bash
s9 possession list [OPTIONS]
```

**Options:**
- `--active-only` - Show only active possessions
- `--role ROLE, -r ROLE` - Filter by role

**Examples:**

List all possessions:
```bash
s9 possession list
```

List active possessions only:
```bash
s9 possession list --active-only
```

Filter by role:
```bash
s9 possession list --role Engineer
```

**Output:**
```
                  Possessions                  
┏━━━━┳━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ ID ┃ Daemon     ┃ Role    ┃ Status      ┃ Start Time ┃
┡━━━━╇━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ 1  │ Azazel     │ Engineer │ ACTIVE      │ 14:30:15   │
│ 2  │ Mephistopheles │ Administrator │ EXORCISED  │ 13:20:00   │
└────┴────────────┴─────────┴─────────────┴────────────┘
```

---

### `s9 possession show`

Show detailed information about a possession.

```bash
s9 possession show <possession-id>
```

**Arguments:**
- `possession-id` - Possession ID (integer)

**Example:**
```bash
s9 possession show 1
```

**Output:**
```
Possession #1
  Daemon: Azazel
  Role: Engineer
  Status: ACTIVE
  Date: 2026-01-30
  Start Time: 14:30:15
  File: .opencode/work/possessions/2026-01-30.14-30-15.engineer.Azazel.md
  Objective: Implement authentication
```

---

### `s9 possession list-opencode-sessions`

List OpenCode TUI sessions for the current project.

```bash
s9 possession list-opencode-sessions
```

**Output:**
```
OpenCode sessions for site-nine:

  ses_3e0a14315ffeEfMd0wqN7EZm84 (quiet-squid) - modified 1h ago
    Review possession-start skill

  ses_3e058ebd6ffebwwd2lKOcGt1iw (hidden-wolf) - modified 3m ago
    Engineer: Azazel - working on auth

  ses_3e0432d71ffeA20XUhe8XxyG8e (hidden-panda) - modified 25s ago
    Administrator: Mephistopheles - task planning

To rename a session, use:
  s9 possession rename-tui <daemon-name> <role> --session-id <session-id>
```

**Use case:**
- Find the correct session ID when you have multiple OpenCode sessions open
- Verify which session corresponds to your current work
- Used before renaming a session to match daemon identity

---

### `s9 possession rename-tui`

Rename the OpenCode TUI session to match daemon identity.

```bash
s9 possession rename-tui <name> <role> [OPTIONS]
```

**Arguments:**
- `name` - Daemon name (e.g., `Calliope`, `Atlas`)
- `role` - Agent role (e.g., `Documentarian`, `Engineer`)

**Options:**
- `--session-id ID, -s ID` - OpenCode session ID (if multiple sessions open)

**Examples:**

Auto-detect and rename current session:
```bash
s9 possession rename-tui Calliope Documentarian
```

Rename specific session:
```bash
s9 possession rename-tui Atlas Engineer --session-id ses_3e058ebd6ffebwwd2lKOcGt1iw
```

**Output:**
```
✓ Renamed OpenCode session to "Operation Nightfall: Calliope - Documentarian"
```

**What it does:**
- Updates the OpenCode TUI session title to `Operation <codename>: <Daemon> - <Role>`
- Makes it easy to identify which agent is working in which session
- Changes take effect immediately (no TUI restart needed)

---

### `s9 task list`

List tasks with optional filters.

```bash
s9 task list [OPTIONS]
```

**Options:**
- `--status STATUS, -s STATUS` - Filter by status
- `--role ROLE, -r ROLE` - Filter by role
- `--daemon NAME, -d NAME` - Filter by daemon name

**Valid Statuses:**
- `TODO`, `UNDERWAY`, `BLOCKED`, `PAUSED`, `REVIEW`, `COMPLETE`, `ABORTED`

**Examples:**

List all tasks:
```bash
s9 task list
```

Filter by status:
```bash
s9 task list --status TODO
```

Filter by role:
```bash
s9 task list --role Engineer
```

Filter by daemon:
```bash
s9 task list --daemon Azazel
```

**Output:**
```
                       Tasks                       
┏━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┓
┃ ID   ┃ Title       ┃ Status ┃ Priority ┃ Daemon   ┃
┡━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━┩
│ T001 │ Auth system │ TODO   │ HIGH     │          │
│ T002 │ Write tests │ UNDER… │ MEDIUM   │ Azazel   │
└──────┴─────────────┴────────┴──────────┴──────────┘
```

---

### `s9 task show`

Show detailed information about a task.

```bash
s9 task show <task-id>
```

**Arguments:**
- `task-id` - Task ID (string, e.g., `ENG-H-0003`, `OPR-M-0009`, or legacy format like `T001`)

**Example:**
```bash
s9 task show T001
```

**Output:**
```
Task T001
  Title: Implement authentication
  Status: TODO
  Priority: HIGH
  Role: Engineer
  Objective: Build user login system
  Description: Implement JWT-based authentication...
  File: .opencode/planning/T001.md
```

---

### `s9 task claim`

Claim a task for a possession.

```bash
s9 task claim <task-id> --possession <id>
```

**Arguments:**
- `task-id` - Task ID (string)

**Options:**
- `--possession ID, -p ID` - Possession ID (required)

**Example:**
```bash
s9 task claim T001 --possession 1
```

**What it does:**
- Sets task status to `UNDERWAY`
- Records possession ID
- Sets `claimed_at` timestamp

**Output:**
```
✓ Task T001 claimed for possession 1
```

---

### `s9 task update`

Update task status and optionally add notes.

```bash
s9 task update <task-id> --status <STATUS> [OPTIONS]
```

**Arguments:**
- `task-id` - Task ID (string)

**Options:**
- `--status STATUS, -s STATUS` - New status (required)
- `--notes TEXT, -n TEXT` - Progress notes

**Valid Statuses:**
- `TODO`, `UNDERWAY`, `BLOCKED`, `PAUSED`, `REVIEW`, `COMPLETE`, `ABORTED`

**Examples:**

Update status only:
```bash
s9 task update T001 --status REVIEW
```

Update with notes:
```bash
s9 task update T001 --status REVIEW --notes "Ready for code review"
```

**Output:**
```
✓ Task T001 updated to REVIEW
```

---

### `s9 task close`

Close a task with COMPLETE or ABORTED status.

```bash
s9 task close <task-id> [OPTIONS]
```

**Arguments:**
- `task-id` - Task ID (string)

**Options:**
- `--status STATUS, -s STATUS` - Close status (default: `COMPLETE`)
- `--notes TEXT, -n TEXT` - Closing notes

**Valid Statuses:**
- `COMPLETE` - Successfully finished (default)
- `ABORTED` - Cancelled

**Examples:**

Close as complete:
```bash
s9 task close T001
```

Close with notes:
```bash
s9 task close T001 --notes "All tests passing"
```

Close as aborted:
```bash
s9 task close T001 --status ABORTED --notes "Requirements changed"
```

**What it does:**
- Sets task status
- Records `closed_at` timestamp
- Saves notes if provided

**Output:**
```
✓ Task T001 closed with status: COMPLETE
```

---

### `s9 task mine`

Show tasks claimed by a specific possession.

```bash
s9 task mine --possession <id>
```

**Options:**
- `--possession ID, -p ID` - Possession ID (required)

**Example:**
```bash
s9 task mine --possession 1
```

**Output:**
```
Tasks claimed by possession 1:

                     Tasks                      
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┓
┃ ID         ┃ Title           ┃ Status  ┃ Priority ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━┩
│ ENG-H-0003 │ Implement auth  │ UNDER…  │ HIGH     │
│ ENG-M-0008 │ Add validation  │ REVIEW  │ MEDIUM   │
└────────────┴─────────────────┴─────────┴──────────┘

Total: 2 tasks (1 in progress, 1 in review)
```

---

### `s9 task report`

Generate task summary report.

```bash
s9 task report [OPTIONS]
```

**Options:**
- `--active-only` - Show only active tasks (excludes COMPLETE, ABORTED)
- `--role ROLE, -r ROLE` - Filter by role

**Examples:**

All tasks summary:
```bash
s9 task report
```

Only active tasks:
```bash
s9 task report --active-only
```

Engineer tasks only:
```bash
s9 task report --role Engineer
```

**Output:**
```
Task Summary Report
═══════════════════

By Status:
  TODO     : 5 tasks
  UNDERWAY : 3 tasks
  REVIEW   : 2 tasks
  COMPLETE : 12 tasks
  ABORTED  : 1 task

By Priority:
  CRITICAL : 1 task
  HIGH     : 7 tasks
  MEDIUM   : 10 tasks
  LOW      : 5 tasks

By Role:
  Engineer      : 9 tasks
  Tester       : 6 tasks
  Operator     : 4 tasks
  Documentarian: 4 tasks
```

---

### `s9 task search`

Search tasks by keyword in title, objective, or description.

```bash
s9 task search <keyword> [OPTIONS]
```

**Arguments:**
- `keyword` - Keyword to search for (required)

**Options:**
- `--active-only` - Show only active tasks
- `--role ROLE, -r ROLE` - Filter by role

**Examples:**

Search for "auth" in all tasks:
```bash
s9 task search auth
```

Search active Engineer tasks:
```bash
s9 task search validation --role Engineer --active-only
```

**Output:**
```
Found 3 tasks matching "auth":

                          Tasks                          
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┓
┃ ID         ┃ Title                ┃ Status  ┃ Priority ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━┩
│ ENG-H-0003 │ Implement JWT auth   │ UNDER…  │ HIGH     │
│ ENG-M-0012 │ Add auth middleware  │ TODO    │ MEDIUM   │
│ TST-H-0002 │ Test auth endpoints  │ REVIEW  │ HIGH     │
└────────────┴──────────────────────┴─────────┴──────────┘
```

---

### `s9 task next`

Suggest next tasks to work on based on priority and dependencies.

```bash
s9 task next [OPTIONS]
```

**Options:**
- `--role ROLE, -r ROLE` - Filter by role
- `--count INTEGER, -c INTEGER` - Number of suggestions (default: 3)

**Examples:**

Get 3 task suggestions:
```bash
s9 task next
```

Suggest Engineer tasks:
```bash
s9 task next --role Engineer --count 5
```

**Output:**
```
Suggested next tasks:

1. ENG-H-0003 (HIGH) - Implement JWT authentication
   No dependencies • Estimated: 4-6 hours

2. TST-H-0005 (HIGH) - Write integration tests
   Depends on: ENG-H-0003 (COMPLETE)

3. OPR-M-0009 (MEDIUM) - Deploy to staging
   No dependencies • Ready to start
```

---

### `s9 task add-dependency`

Add a task dependency (one task depends on another).

```bash
s9 task add-dependency <task-id> <depends-on>
```

**Arguments:**
- `task-id` - Task that has the dependency
- `depends-on` - Task that must be completed first

**Example:**
```bash
s9 task add-dependency ENG-H-0008 ENG-H-0003
```

This means ENG-H-0008 depends on ENG-H-0003 completing first.

**Output:**
```
✓ Added dependency: ENG-H-0008 depends on ENG-H-0003
```

**Use case:**
```bash
# Task ENG-H-0008 (Add auth middleware) depends on ENG-H-0003 (Implement JWT)
s9 task add-dependency ENG-H-0008 ENG-H-0003

# Now ENG-H-0008 should wait until ENG-H-0003 is complete
```

---

### `s9 task sync`

Synchronize task markdown files with database.

```bash
s9 task sync [OPTIONS]
```

**Options:**
- `--task TASK_ID, -t TASK_ID` - Sync specific task (syncs all if not provided)

**Examples:**

Sync all tasks:
```bash
s9 task sync
```

Sync specific task:
```bash
s9 task sync --task ENG-H-0003
```

**What it does:**
- Reads task markdown files from `.opencode/planning/`
- Updates database with any changes from the files
- Creates missing files for tasks that don't have them
- Reports any mismatches or issues

**Output:**
```
Syncing tasks...

✓ ENG-H-0003.md - Up to date
✓ ENG-M-0008.md - Updated from file
⚠ OPR-M-0009.md - Missing file, created from database
✓ TST-H-0002.md - Up to date

Summary: 4 tasks synced (1 updated, 1 created)
```

---

### `s9 task create`

Create a new task with auto-generated ID.

```bash
s9 task create --title <TITLE> --role <ROLE> [OPTIONS]
```

**Options:**
- `--title TEXT, -t TEXT` - Brief task description (required)
- `--role ROLE, -r ROLE` - Agent role responsible for this task (required)
- `--priority PRIORITY, -p PRIORITY` - Task priority (default: `MEDIUM`)
- `--category TEXT, -c TEXT` - Task category (optional)
- `--description TEXT, -d TEXT` - Detailed description (optional)
- `--epic EPIC_ID, -e EPIC_ID` - Link task to an epic (optional)

**Valid Roles:**
- `Administrator`, `Architect`, `Engineer`, `Tester`, `Documentarian`, `Designer`, `Inspector`, `Operator`

**Valid Priorities:**
- `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`

**Examples:**

Create a high-priority task:
```bash
s9 task create --title "Implement JWT authentication" --role Engineer --priority HIGH
```

With category and description:
```bash
s9 task create \
  --title "Add user login API" \
  --role Engineer \
  --priority HIGH \
  --category "Authentication" \
  --description "Build REST endpoint for user authentication with JWT tokens"
```

Create task linked to an epic:
```bash
s9 task create \
  --title "Design auth architecture" \
  --role Architect \
  --priority HIGH \
  --epic EPC-H-0001
```

**Task ID Format:**

Task IDs are auto-generated with format: `{ROLE}-{PRIORITY}-{NUMBER}`

- Role codes: `MGR`, `ARC`, `ENG`, `TST`, `DOC`, `DSN`, `INS`, `OPR`
- Priority codes: `C` (Critical), `H` (High), `M` (Medium), `L` (Low)
- Number: Zero-padded sequence (0001, 0002, etc.)

**Examples:** `ENG-H-0003`, `OPR-M-0009`, `DOC-L-0001`

**Output:**
```
✓ Created task ENG-H-0003: Implement JWT authentication
  File: .opencode/planning/ENG-H-0003.md
```

---

### `s9 epic create`

Create a new epic to group related tasks.

```bash
s9 epic create --title <TITLE> --priority <PRIORITY> [OPTIONS]
```

**Options:**
- `--title TEXT, -t TEXT` - Epic title (required)
- `--priority PRIORITY, -p PRIORITY` - Epic priority (required)
- `--description TEXT, -d TEXT` - Detailed description (optional)

**Valid Priorities:**
- `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`

**Examples:**

Create a high-priority epic:
```bash
s9 epic create --title "User Authentication System" --priority HIGH
```

With description:
```bash
s9 epic create \
  --title "User Authentication System" \
  --priority HIGH \
  --description "Implement complete user authentication including login, registration, and password reset"
```

**Epic ID Format:**

Epic IDs are auto-generated with format: `EPC-{P}-{NNNN}`

- `EPC` - Epic prefix (constant)
- `{P}` - Priority code: `C` (Critical), `H` (High), `M` (Medium), `L` (Low)
- `{NNNN}` - Sequential 4-digit number (padded with zeros)

**Examples:** `EPC-H-0001`, `EPC-C-0015`, `EPC-M-0042`

**Output:**
```
✓ Created epic EPC-H-0001
  Title: User Authentication System
  Priority: HIGH
  Status: TODO
  File: .opencode/work/epics/EPC-H-0001.md
```

---

### `s9 epic list`

List epics with optional filters.

```bash
s9 epic list [OPTIONS]
```

**Options:**
- `--status STATUS, -s STATUS` - Filter by status
- `--priority PRIORITY, -p PRIORITY` - Filter by priority

**Valid Statuses:**
- `TODO`, `UNDERWAY`, `COMPLETE`, `ABORTED`

**Examples:**

List all epics:
```bash
s9 epic list
```

Filter by status:
```bash
s9 epic list --status UNDERWAY
```

Filter by priority:
```bash
s9 epic list --priority HIGH
```

Combine filters:
```bash
s9 epic list --status UNDERWAY --priority HIGH
```

**Output:**
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

---

### `s9 epic show`

Show detailed information about an epic.

```bash
s9 epic show <EPIC_ID>
```

**Arguments:**
- `EPIC_ID` - Epic ID (e.g., `EPC-H-0001`)

**Example:**
```bash
s9 epic show EPC-H-0001
```

**Output:**
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

---

### `s9 epic update`

Update epic metadata.

```bash
s9 epic update <EPIC_ID> [OPTIONS]
```

**Arguments:**
- `EPIC_ID` - Epic ID (e.g., `EPC-H-0001`)

**Options:**
- `--title TEXT, -t TEXT` - New title
- `--description TEXT, -d TEXT` - New description
- `--priority PRIORITY, -p PRIORITY` - New priority

**Examples:**

Update title:
```bash
s9 epic update EPC-H-0001 --title "User Authentication and Authorization"
```

Change priority:
```bash
s9 epic update EPC-H-0001 --priority CRITICAL
```

Update description:
```bash
s9 epic update EPC-H-0001 --description "Extended scope to include role-based access control"
```

**Output:**
```
✓ Updated epic EPC-H-0001
  Title: User Authentication and Authorization
```

---

### `s9 epic abort`

Abort an epic and all its subtasks.

```bash
s9 epic abort <EPIC_ID> --reason <REASON> [OPTIONS]
```

**Arguments:**
- `EPIC_ID` - Epic ID (e.g., `EPC-H-0001`)

**Options:**
- `--reason TEXT, -r TEXT` - Reason for aborting (required)
- `--yes, -y` - Skip confirmation prompt

**Examples:**

Abort with confirmation:
```bash
s9 epic abort EPC-H-0001 --reason "Requirements changed; switching to OAuth instead"
```

Skip confirmation:
```bash
s9 epic abort EPC-H-0001 --reason "Project cancelled" --yes
```

**What it does:**
- Sets epic status to ABORTED
- Cascades ABORTED status to ALL subtasks
- Records abort reason and timestamp
- Protects epic from future auto-updates

**Confirmation prompt:**
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

**Output:**
```
✓ Epic EPC-H-0001 aborted
  Reason: Requirements changed; switching to OAuth instead
  Affected tasks: 5
```

---

### `s9 epic sync`

Synchronize epic markdown files with database.

```bash
s9 epic sync [OPTIONS]
```

**Options:**
- `--epic EPIC_ID, -e EPIC_ID` - Sync specific epic (syncs all if omitted)

**Examples:**

Sync all epics:
```bash
s9 epic sync
```

Sync specific epic:
```bash
s9 epic sync --epic EPC-H-0001
```

**What it does:**
- Regenerates epic markdown files from database
- Updates header with current metadata
- Regenerates progress and subtasks sections
- Preserves user-edited sections (Description, Goals, Success Criteria, Notes)

**Output:**
```
Syncing epics...

✓ EPC-H-0001.md - Regenerated
✓ EPC-H-0002.md - Regenerated
✓ EPC-M-0003.md - Regenerated

Summary: 3 epics synced
```

---

### `s9 task link`

Link an existing task to an epic.

```bash
s9 task link <TASK_ID> <EPIC_ID>
```

**Arguments:**
- `TASK_ID` - Task ID (e.g., `ENG-H-0059`)
- `EPIC_ID` - Epic ID (e.g., `EPC-H-0001`)

**Example:**
```bash
s9 task link ENG-H-0059 EPC-H-0001
```

**Output:**
```
✓ Linked task ENG-H-0059 to epic EPC-H-0001
```

**Note:** A task can only belong to one epic at a time. Linking a task to a new epic will unlink it from its previous
epic.

---

### `s9 task unlink`

Remove a task from its epic.

```bash
s9 task unlink <TASK_ID>
```

**Arguments:**
- `TASK_ID` - Task ID (e.g., `ENG-H-0059`)

**Example:**
```bash
s9 task unlink ENG-H-0059
```

**Output:**
```
✓ Unlinked task ENG-H-0059 from epic EPC-H-0001
```

**Note:** The task becomes standalone after unlinking (not deleted).

---

### `s9 daemon list`

List daemon names with optional filters.

```bash
s9 daemon list [OPTIONS]
```

**Options:**
- `--role ROLE, -r ROLE` - Filter by role
- `--unused-only` - Show only unused names
- `--by-usage` - Sort by usage count

**Examples:**

List all names:
```bash
s9 daemon list
```

List unused Engineer names:
```bash
s9 daemon list --role Engineer --unused-only
```

Sort by most-used:
```bash
s9 daemon list --by-usage
```

**Output:**
```
                     Daemon Names                     
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Name          ┃ Role     ┃ Mythology  ┃ Usage Count ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ Azazel        │ Inspec…  │ Judaism    │ 2           │
│ Calliope      │ Document │ Greek      │ 1           │
│ Atlas         │ Engineer │ Greek      │ 0           │
└───────────────┴──────────┴────────────┴─────────────┘
```

---

### `s9 daemon suggest`

Suggest least-recently-used daemon names for a specific role, using the 3-day LRU algorithm.

```bash
s9 daemon suggest <role> [OPTIONS]
```

**Arguments:**
- `role` - Role to suggest names for (required)

**Options:**
- `--count INTEGER, -c INTEGER` - Number of suggestions (default: 3)

**Examples:**

Get 3 suggestions for Engineer:
```bash
s9 daemon suggest Engineer
```

Get 5 suggestions:
```bash
s9 daemon suggest Documentarian --count 5
```

**Output:**
```
Suggested daemons for Engineer:

1. Hephaestus (Greek) - last used 8 days ago
   Greek god of blacksmiths and craftsmen

2. Goibniu (Celtic) - never used
   Celtic god of smithcraft

3. Vulcan (Roman) - never used
   Roman god of fire and metalworking
```

---

### `s9 daemon usage`

Show usage history for a daemon name.

```bash
s9 daemon usage <name>
```

**Arguments:**
- `name` - Daemon name to check (required)

**Example:**
```bash
s9 daemon usage Atlas
```

**Output:**
```
Daemon: Atlas
  Mythology: Greek
  Primary role: Engineer
  Description: Titan who holds up the sky

Usage history:
  Times used: 2
  Last used: 2026-01-30 14:30:15

Possessions:
  #15 - Atlas    - Engineer (2026-01-30 14:30:15)
  #8  - Atlas    - Engineer (2026-01-29 09:15:00)
```

---

### `s9 daemon add`

Add a new daemon name to the database.

```bash
s9 daemon add <name> --role <ROLE> --mythology <MYTHOLOGY> --description <DESCRIPTION>
```

**Arguments:**
- `name` - Daemon name (required)

**Options:**
- `--role ROLE, -r ROLE` - Primary role for this name (required)
- `--mythology TEXT, -m TEXT` - Mythology origin (required)
- `--description TEXT, -d TEXT` - Brief description (required)

**Example:**
```bash
s9 daemon add Sekhmet \
  --role Tester \
  --mythology Egyptian \
  --description "Lion-headed goddess of war and destruction"
```

**Output:**
```
✓ Added daemon 'Sekhmet'
  Role: Tester
  Mythology: Egyptian
```

---

### `s9 settings`

Manage application settings and configuration.

```bash
s9 settings <subcommand> [OPTIONS]
```

**Subcommands:**

#### `s9 settings show`
Show current application settings.

```bash
s9 settings show
```

**Output:**
```
Current settings:
  default_role: Engineer
  log_level: INFO
  database_path: .opencode/data/project.db
```

#### `s9 settings bind`
Set all settings for the application at once.

```bash
s9 settings bind
```

Interactive prompt to configure all available settings.

#### `s9 settings update`
Update specific settings.

```bash
s9 settings update
```

Interactive prompt to update selected settings.

#### `s9 settings unset`
Remove specific settings (revert to defaults).

```bash
s9 settings unset
```

Interactive prompt to remove settings.

#### `s9 settings reset`
Reset all settings to defaults.

```bash
s9 settings reset
```

**Use cases:**
- Configure default agent roles
- Set logging preferences
- Customize database location
- Adjust CLI output formatting

---

### `s9 cache`

Manage application cache for improved performance.

```bash
s9 cache <subcommand> [OPTIONS]
```

**Subcommands:**

#### `s9 cache show`
Display cache contents or statistics.

```bash
s9 cache show
```

**Output:**
```
Cache statistics:
  Total entries: 42
  Size: 1.2 MB
  Last cleared: 2026-01-30 14:30:15

Recent entries:
  - daemon_names: 145 entries
  - task_templates: 8 entries
  - possessions: 12 entries
```

#### `s9 cache clear`
Remove entries from the cache.

```bash
s9 cache clear
```

Clears all cached data. Useful for troubleshooting or when data seems stale.

**Output:**
```
✓ Cache cleared
  Removed 42 entries (1.2 MB freed)
```

**When to use:**
- After database changes outside of s9
- When experiencing unexpected behavior
- To free up disk space
- After upgrading s9 version

---

### `s9 logs`

Manage application logs for debugging and auditing.

```bash
s9 logs <subcommand> [OPTIONS]
```

**Subcommands:**

#### `s9 logs show`
Display the current log file.

```bash
s9 logs show
```

**Output:**
```
2026-02-02 11:03:39 | INFO  | Started agent session 14: calliope
2026-02-02 11:05:12 | DEBUG | Loading daemon names from database
2026-02-02 11:06:45 | INFO  | Created task ENG-H-0003
2026-02-02 11:08:20 | ERROR | Database connection failed: timeout
```

#### `s9 logs audit`
Show retained log files.

```bash
s9 logs audit
```

**Output:**
```
Log files:
  s9.log           - 2.4 MB (today)
  s9.log.1         - 5.1 MB (yesterday)
  s9.log.2         - 4.8 MB (2 days ago)
  s9.log.3         - 5.2 MB (3 days ago)

Total: 17.5 MB across 4 files
Retention policy: 7 days
```

#### `s9 logs clear`
Clear all log files.

```bash
s9 logs clear
```

**Output:**
```
✓ Cleared all log files
  Freed 17.5 MB
```

**Use cases:**
- Debugging issues with s9 commands
- Auditing agent activities
- Troubleshooting database problems
- Freeing disk space

---

## Exit Codes

- `0` - Success
- `1` - Error (with error message to stderr)

## Configuration File Format

YAML configuration file format for `s9 init --config`:

```yaml
project:
  name: string              # Project name (required)
  type: string              # python|typescript|go|rust|other
  description: string       # Project description

features:
  pm_system: boolean        # Enable task management (default: true)
  possession_tracking: boolean # Enable possession tracking (default: true)
  commit_guidelines: boolean # Include commit guidelines (default: true)
  daemon_naming: boolean    # Use daemon names (default: true)

agent_roles:
  - name: string           # Role name (required)
    enabled: boolean       # Enable this role (default: true)
    description: string    # Custom description (optional)

customization:
  daemon_names: string     # Naming theme (default: "mythology")
  template_dir: string     # Custom template directory (optional)
  variables:               # Custom template variables (optional)
    key: value
```

## Environment Variables

Currently, s9 does not use environment variables for configuration.

## Database Schema

The SQLite database at `.opencode/data/project.db` has the following schema:

### `daemons` Table

Stores 145+ mythology-based daemon names.

| Column | Type | Description |
|--------|------|-------------|
| name | TEXT | Unique daemon name |
| role | TEXT | Default role (CHECK constraint) |
| mythology | TEXT | Source mythology |
| description | TEXT | Name description |
| usage_count | INTEGER | Times used |
| last_used_at | TEXT | Last usage timestamp |

### `possessions` Table

Tracks possessions.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| daemon_name | TEXT | Daemon name (FK to daemons) |
| role | TEXT | Possession role |
| codename | TEXT | Operation codename |
| possession_file | TEXT | Session file path |
| possession_date | TEXT | Date (YYYY-MM-DD) |
| start_time | TEXT | Start time (HH:MM:SS) |
| end_time | TEXT | End time or NULL |
| status | TEXT | Possession status |
| objective | TEXT | Possession objective |
| created_at | TEXT | Creation timestamp |
| updated_at | TEXT | Update timestamp |

### `tasks` Table

Manages tasks.

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | Primary key (e.g., `ENG-H-0003` or legacy `T001`) |
| title | TEXT | Short description |
| status | TEXT | Task status |
| priority | TEXT | Priority level |
| role | TEXT | Required role |
| category | TEXT | Task category |
| daemon_name | TEXT | Assigned daemon |
| possession_id | INTEGER | FK to possessions table |
| claimed_at | TEXT | Claim timestamp |
| closed_at | TEXT | Close timestamp |
| paused_at | TEXT | Pause timestamp |
| actual_hours | REAL | Time spent |
| objective | TEXT | Main objective |
| description | TEXT | Detailed description |
| notes | TEXT | Progress notes |
| file_path | TEXT | Task file path |
| created_at | TEXT | Creation timestamp |
| updated_at | TEXT | Update timestamp |

### `task_dependencies` Table

Tracks task dependencies.

| Column | Type | Description |
|--------|------|-------------|
| task_id | TEXT | Dependent task |
| depends_on_task_id | TEXT | Required task |

**Composite Primary Key:** (task_id, depends_on_task_id)