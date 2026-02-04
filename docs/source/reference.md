# CLI Reference

Complete reference for all s9 commands.

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
3. Populates 145 persona names
4. Renders 19+ templates (missions, guides, procedures, README, config)
5. Creates empty directories (missions, planning, scripts)

---

### `s9 dashboard`

Show project overview with active personas and task summary.

```bash
s9 dashboard
```

**Output includes:**
- Quick stats (active personas, total tasks, in progress, completed)
- Active missions table
- Task summary by status
- Recent tasks (last 10)

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

### `s9 changelog`

Generate changelog from completed tasks.

```bash
s9 changelog [OPTIONS]
```

**Options:**
- `--since DATE` - Only include tasks closed since this date (YYYY-MM-DD)
- `--format TEXT` - Output format: `markdown` or `json` (default: `markdown`)
- `--output PATH, -o PATH` - Write to file instead of stdout

**Examples:**

Generate changelog for all completed tasks:
```bash
s9 changelog
```

Only recent tasks since a specific date:
```bash
s9 changelog --since 2026-01-01
```

Output to file:
```bash
s9 changelog --output CHANGELOG.md
```

JSON format for processing:
```bash
s9 changelog --format json --output changelog.json
```

**Output (markdown format):**
```markdown
# Changelog

## 2026-01-30

### Builder
- BLD-H-0003: Implement JWT authentication
- BLD-M-0008: Add input validation to API endpoints

### Tester
- TST-H-0002: Write integration tests for auth flow

## 2026-01-29

### Operator
- OPR-H-0005: Consolidate .opencode directory structure
```

---

### `s9 doctor`

Run health checks and validate data integrity.

```bash
s9 doctor [OPTIONS]
```

**Options:**
- `--fix` - Apply fixes automatically for safe issues
- `--verbose, -v` - Show detailed output

**What it checks:**
- Invalid foreign key references
- Inconsistent task states
- Mission data issues
- Incorrect usage counters
- Missing files referenced in database
- Orphaned task dependencies

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

**Output:**
```
Running health checks...

✓ Foreign key integrity: OK
✓ Task state consistency: OK
⚠ Found 2 issues with missions:
  - Mission #5 has NULL end_time but status is 'completed'
  - Mission #12 file not found: .opencode/missions/2026-01-28...
✓ Persona name usage counters: OK

Summary: 2 issues found (0 critical, 2 warnings)

Run with --fix to automatically repair safe issues.
```

---

### `s9 mission start`

Start a new mission.

```bash
s9 mission start <name> --role <ROLE> [OPTIONS]
```

**Arguments:**
- `name` - Persona name for the mission (e.g., `azazel`, `belial-ii`)

**Options:**
- `--role ROLE, -r ROLE` - Mission role (required)
- `--task DESCRIPTION, -t DESCRIPTION` - Task summary

**Valid Roles:**
- `Administrator` - Project coordination
- `Architect` - System design
- `Builder` - Implementation
- `Tester` - Quality assurance
- `Documentarian` - Documentation
- `Designer` - UI/UX design
- `Inspector` - Code review
- `Operator` - Operations/deployment

**Examples:**

Start a Builder mission:
```bash
s9 mission start azazel --role Builder --task "Implement authentication"
```

Start without task description:
```bash
s9 mission start belial --role Administrator
```

Start with suffix (for second instance):
```bash
s9 mission start azazel-ii --role Builder
```

**Output:**
```
✓ Started mission #1
  Name: azazel
  Role: Builder
  Task: Implement authentication
```

---

### `s9 mission list`

List missions with optional filters.

```bash
s9 mission list [OPTIONS]
```

**Options:**
- `--active-only` - Show only in-progress missions
- `--role ROLE, -r ROLE` - Filter by role

**Examples:**

List all missions:
```bash
s9 mission list
```

List active missions only:
```bash
s9 mission list --active-only
```

Filter by role:
```bash
s9 mission list --role Builder
```

**Output:**
```
                  Missions                  
┏━━━━┳━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ ID ┃ Name   ┃ Role    ┃ Status      ┃ Start Time ┃
┡━━━━╇━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ 1  │ azazel │ Builder │ in-progress │ 14:30:15   │
│ 2  │ belial │ Administrator │ completed   │ 13:20:00   │
└────┴────────┴─────────┴─────────────┴────────────┘
```

---

### `s9 mission show`

Show detailed information about a mission.

```bash
s9 mission show <mission-id>
```

**Arguments:**
- `mission-id` - Mission ID (integer)

**Example:**
```bash
s9 mission show 1
```

**Output:**
```
Mission #1
  Name: azazel
  Base Name: azazel
  Role: Builder
  Status: in-progress
  Mission Date: 2026-01-30
  Start Time: 14:30:15
  Mission File: .opencode/missions/2026-01-30.14:30:15.builder.azazel.md
  Task: Implement authentication
```

---

### `s9 mission end`

End a mission.

```bash
s9 mission end <mission-id> [OPTIONS]
```

**Arguments:**
- `mission-id` - Mission ID (integer)

**Options:**
- `--status STATUS` - End status (default: `completed`)

**Valid Statuses:**
- `completed` - Successfully finished (default)
- `paused` - Temporarily stopped
- `failed` - Failed to complete
- `aborted` - Cancelled

**Examples:**

End with default status:
```bash
s9 mission end 1
```

End with specific status:
```bash
s9 mission end 1 --status failed
```

**Output:**
```
✓ Ended mission #1 with status: completed
```

---

### `s9 mission pause`

Pause an active mission.

```bash
s9 mission pause <mission-id> [OPTIONS]
```

**Arguments:**
- `mission-id` - Mission ID (integer)

**Options:**
- `--reason TEXT` - Reason for pausing (optional)

**Examples:**

Pause a mission:
```bash
s9 mission pause 1
```

With reason:
```bash
s9 mission pause 1 --reason "Taking a break for lunch"
```

**Output:**
```
✓ Paused mission #1
  Reason: Taking a break for lunch
```

**Use cases:**
- Taking a break during work
- Switching to another urgent task
- End of workday (resume tomorrow)
- Waiting for external dependencies

---

### `s9 mission resume`

Resume a paused mission.

```bash
s9 mission resume <mission-id>
```

**Arguments:**
- `mission-id` - Mission ID (integer)

**Example:**
```bash
s9 mission resume 1
```

**Output:**
```
✓ Resumed mission #1
  Duration paused: 1h 23m
```

---

### `s9 mission update`

Update mission metadata.

```bash
s9 mission update <mission-id> [OPTIONS]
```

**Arguments:**
- `mission-id` - Mission ID (integer)

**Options:**
- `--task TEXT, -t TEXT` - Update task summary
- `--role ROLE, -r ROLE` - Update role

**Examples:**

Update task summary:
```bash
s9 mission update 1 --task "Implement OAuth instead of JWT"
```

Change role (if scope changed):
```bash
s9 mission update 1 --role Architect --task "Design authentication system"
```

**Output:**
```
✓ Updated mission #1
  Task: Implement OAuth instead of JWT
```

**Use cases:**
- Task requirements changed mid-mission
- Realized different role is more appropriate
- Refining task description for clarity

---

### `s9 mission roles`

Display available mission roles with descriptions.

```bash
s9 mission roles
```

**Output:**
```
Which role should I assume for this mission?

  • Administrator: coordinate and delegate to other personas
  • Architect: design systems and make technical decisions
  • Builder: implement features and write code
  • Tester: write tests and validate functionality
  • Documentarian: create documentation and guides
  • Designer: design user interfaces and experiences
  • Inspector: review code and audit security
  • Operator: deploy systems and manage infrastructure
```

**Use case:**
- Quick reference for available roles during mission start
- Part of the mission initialization workflow
- Standardized role descriptions across all missions

---

### `s9 mission list-opencode-sessions`

List OpenCode TUI sessions for the current project.

```bash
s9 mission list-opencode-sessions
```

**Output:**
```
OpenCode sessions for site-nine:

  ses_3e0a14315ffeEfMd0wqN7EZm84 (quiet-squid) - modified 1h ago
    Review summon.md in .opencode/docs/commands

  ses_3e058ebd6ffebwwd2lKOcGt1iw (hidden-wolf) - modified 3m ago
    Session-start skill usage

  ses_3e0432d71ffeA20XUhe8XxyG8e (hidden-panda) - modified 25s ago
    Session-start skill creation

To rename a session, use:
  s9 mission rename-tui <name> <role> --session-id <session-id>
```

**Use case:**
- Find the correct session ID when you have multiple OpenCode sessions open
- Verify which session corresponds to your current work
- Used before renaming a session to match persona identity

---

### `s9 mission rename-tui`

Rename the OpenCode TUI session to match persona identity.

```bash
s9 mission rename-tui <name> <role> [OPTIONS]
```

**Arguments:**
- `name` - Persona name (e.g., `calliope`, `atlas-ii`)
- `role` - Persona role (e.g., `Documentarian`, `Builder`)

**Options:**
- `--session-id ID, -s ID` - OpenCode session ID (if multiple sessions open)

**Examples:**

Auto-detect and rename current session:
```bash
s9 mission rename-tui calliope Documentarian
```

Rename specific session:
```bash
s9 mission rename-tui atlas Builder --session-id ses_3e058ebd6ffebwwd2lKOcGt1iw
```

**Output:**
```
✅ Renamed OpenCode session to "calliope - Documentarian"
```

**What it does:**
- Updates the OpenCode TUI session title to `<Name> - <Role>`
- Makes it easy to identify which persona you're working with
- Changes take effect immediately (no TUI restart needed)

**Use case:**
- Part of the mission initialization workflow
- Helps track which persona is working in which OpenCode session
- Useful when managing multiple missions simultaneously

---

### `s9 task list`

List tasks with optional filters.

```bash
s9 task list [OPTIONS]
```

**Options:**
- `--status STATUS, -s STATUS` - Filter by status
- `--role ROLE, -r ROLE` - Filter by role
- `--persona NAME, -p NAME` - Filter by persona name

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
s9 task list --role Builder
```

Filter by persona:
```bash
s9 task list --persona azazel
```

**Output:**
```
                       Tasks                       
┏━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┓
┃ ID   ┃ Title       ┃ Status ┃ Priority ┃ Persona ┃
┡━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━┩
│ T001 │ Auth system │ TODO   │ HIGH     │         │
│ T002 │ Write tests │ UNDER… │ MEDIUM   │ azazel  │
└──────┴─────────────┴────────┴──────────┴─────────┘
```

---

### `s9 task show`

Show detailed information about a task.

```bash
s9 task show <task-id>
```

**Arguments:**
- `task-id` - Task ID (string, e.g., `BLD-H-0003`, `OPR-M-0009`, or legacy format like `T001`)

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
  Role: Builder
  Objective: Build user login system
  Description: Implement JWT-based authentication...
  File: .opencode/planning/T001.md
```

---

### `s9 task claim`

Claim a task for a mission.

```bash
s9 task claim <task-id> --mission <id>
```

**Arguments:**
- `task-id` - Task ID (string)

**Options:**
- `--mission ID, -m ID` - Mission ID (required)

**Example:**
```bash
s9 task claim T001 --mission 1
```

**What it does:**
- Sets task status to `UNDERWAY`
- Records mission ID
- Sets `claimed_at` timestamp

**Output:**
```
✓ Task T001 claimed for mission 1
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

Show tasks claimed by a specific mission.

```bash
s9 task mine --mission <id>
```

**Options:**
- `--mission ID, -m ID` - Mission ID (required)

**Example:**
```bash
s9 task mine --mission 1
```

**Output:**
```
Tasks claimed by mission 1:

                     Tasks                      
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┓
┃ ID         ┃ Title           ┃ Status  ┃ Priority ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━┩
│ BLD-H-0003 │ Implement auth  │ UNDER…  │ HIGH     │
│ BLD-M-0008 │ Add validation  │ REVIEW  │ MEDIUM   │
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

Builder tasks only:
```bash
s9 task report --role Builder
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
  Builder      : 9 tasks
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

Search active Builder tasks:
```bash
s9 task search validation --role Builder --active-only
```

**Output:**
```
Found 3 tasks matching "auth":

                          Tasks                          
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┓
┃ ID         ┃ Title                ┃ Status  ┃ Priority ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━┩
│ BLD-H-0003 │ Implement JWT auth   │ UNDER…  │ HIGH     │
│ BLD-M-0012 │ Add auth middleware  │ TODO    │ MEDIUM   │
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

Suggest Builder tasks:
```bash
s9 task next --role Builder --count 5
```

**Output:**
```
Suggested next tasks:

1. BLD-H-0003 (HIGH) - Implement JWT authentication
   No dependencies • Estimated: 4-6 hours

2. TST-H-0005 (HIGH) - Write integration tests
   Depends on: BLD-H-0003 (COMPLETE)

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
s9 task add-dependency BLD-H-0008 BLD-H-0003
```

This means BLD-H-0008 depends on BLD-H-0003 completing first.

**Output:**
```
✓ Added dependency: BLD-H-0008 depends on BLD-H-0003
```

**Use case:**
```bash
# Task BLD-H-0008 (Add auth middleware) depends on BLD-H-0003 (Implement JWT)
s9 task add-dependency BLD-H-0008 BLD-H-0003

# Now BLD-H-0008 should wait until BLD-H-0003 is complete
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
s9 task sync --task BLD-H-0003
```

**What it does:**
- Reads task markdown files from `.opencode/planning/`
- Updates database with any changes from the files
- Creates missing files for tasks that don't have them
- Reports any mismatches or issues

**Output:**
```
Syncing tasks...

✓ BLD-H-0003.md - Up to date
✓ BLD-M-0008.md - Updated from file
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

**Valid Roles:**
- `Administrator`, `Architect`, `Builder`, `Tester`, `Documentarian`, `Designer`, `Inspector`, `Operator`

**Valid Priorities:**
- `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`

**Examples:**

Create a high-priority task:
```bash
s9 task create --title "Implement JWT authentication" --role Builder --priority HIGH
```

With category and description:
```bash
s9 task create \
  --title "Add user login API" \
  --role Builder \
  --priority HIGH \
  --category "Authentication" \
  --description "Build REST endpoint for user authentication with JWT tokens"
```

**Task ID Format:**

Task IDs are auto-generated with format: `{ROLE}-{PRIORITY}-{NUMBER}`

- Role codes: `MGR`, `ARC`, `BLD`, `TST`, `DOC`, `DSN`, `INS`, `OPR`
- Priority codes: `C` (Critical), `H` (High), `M` (Medium), `L` (Low)
- Number: Zero-padded sequence (0001, 0002, etc.)

**Examples:** `BLD-H-0003`, `OPR-M-0009`, `DOC-L-0001`

**Output:**
```
✓ Created task BLD-H-0003: Implement JWT authentication
  File: .opencode/planning/BLD-H-0003.md
```

---

### `s9 template list`

List available templates.

```bash
s9 template list
```

**Note:** This command is a placeholder in the current version.

---

### `s9 template show`

Show template content.

```bash
s9 template show <name>
```

**Note:** This command is a placeholder in the current version.

---

### `s9 config show`

Show current configuration.

```bash
s9 config show
```

**Note:** This command is a placeholder in the current version.

---

### `s9 config validate`

Validate configuration file.

```bash
s9 config validate <file>
```

**Note:** This command is a placeholder in the current version.

---

### `s9 name list`

List persona names with optional filters.

```bash
s9 name list [OPTIONS]
```

**Options:**
- `--role ROLE, -r ROLE` - Filter by role
- `--unused-only` - Show only unused names
- `--by-usage` - Sort by usage count

**Examples:**

List all names:
```bash
s9 name list
```

List unused Builder names:
```bash
s9 name list --role Builder --unused-only
```

Sort by most-used:
```bash
s9 name list --by-usage
```

**Output:**
```
                     Persona Names                     
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Name          ┃ Role     ┃ Mythology  ┃ Usage Count ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ azazel        │ Inspec…  │ Judaism    │ 2           │
│ calliope      │ Document │ Greek      │ 1           │
│ atlas         │ Builder  │ Greek      │ 0           │
└───────────────┴──────────┴────────────┴─────────────┘
```

---

### `s9 name suggest`

Suggest unused persona names for a specific role.

```bash
s9 name suggest <role> [OPTIONS]
```

**Arguments:**
- `role` - Role to suggest names for (required)

**Options:**
- `--count INTEGER, -c INTEGER` - Number of suggestions (default: 3)

**Examples:**

Get 3 suggestions for Builder:
```bash
s9 name suggest Builder
```

Get 5 suggestions:
```bash
s9 name suggest Documentarian --count 5
```

**Output:**
```
Suggested names for Builder:

1. hephaestus (Greek) - unused
   Greek god of blacksmiths and craftsmen

2. goibniu (Celtic) - unused
   Celtic god of smithcraft

3. vulcan (Roman) - unused
   Roman god of fire and metalworking
```

---

### `s9 name usage`

Show usage history for a persona name.

```bash
s9 name usage <name>
```

**Arguments:**
- `name` - Persona name to check (required)

**Example:**
```bash
s9 name usage atlas
```

**Output:**
```
Persona name: atlas
  Mythology: Greek
  Primary role: Builder
  Description: Titan who holds up the sky

Usage history:
  Times used: 2
  Last used: 2026-01-30 14:30:15

Missions:
  #15 - atlas    - Builder (2026-01-30 14:30:15)
  #8  - atlas-ii - Builder (2026-01-29 09:15:00)
```

---

### `s9 name add`

Add a new persona name to the database.

```bash
s9 name add <name> --role <ROLE> --mythology <MYTHOLOGY> --description <DESCRIPTION>
```

**Arguments:**
- `name` - Persona name (lowercase, required)

**Options:**
- `--role ROLE, -r ROLE` - Primary role for this name (required)
- `--mythology TEXT, -m TEXT` - Mythology origin (required)
- `--description TEXT, -d TEXT` - Brief description (required)

**Example:**
```bash
s9 name add sekhmet \
  --role Tester \
  --mythology Egyptian \
  --description "Lion-headed goddess of war and destruction"
```

**Output:**
```
✓ Added persona name 'sekhmet'
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
  default_role: Builder
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
  - persona_names: 145 entries
  - task_templates: 8 entries
  - missions: 12 entries
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
2026-02-02 11:06:45 | INFO  | Created task BLD-H-0003
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
  mission_tracking: boolean # Enable mission tracking (default: true)
  commit_guidelines: boolean # Include commit guidelines (default: true)
  persona_naming: boolean    # Use persona names (default: true)

agent_roles:
  - name: string           # Role name (required)
    enabled: boolean       # Enable this role (default: true)
    description: string    # Custom description (optional)

customization:
  persona_names: string     # Naming theme (default: "mythology")
  template_dir: string     # Custom template directory (optional)
  variables:               # Custom template variables (optional)
    key: value
```

## Environment Variables

Currently, s9 does not use environment variables for configuration.

## Database Schema

The SQLite database at `.opencode/data/project.db` has the following schema:

### `personas` Table

Stores 145+ mythology-based persona names.

| Column | Type | Description |
|--------|------|-------------|
| name | TEXT | Unique persona name |
| role | TEXT | Default role (CHECK constraint) |
| mythology | TEXT | Source mythology |
| description | TEXT | Name description |
| usage_count | INTEGER | Times used |
| last_used_at | TEXT | Last usage timestamp |

### `missions` Table

Tracks missions.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| persona_name | TEXT | Full name with suffix |
| base_name | TEXT | Base name (FK to personas) |
| suffix | TEXT | Roman numeral suffix |
| role | TEXT | Mission role |
| codename | TEXT | Mission codename |
| mission_file | TEXT | Log file path |
| mission_date | TEXT | Date (YYYY-MM-DD) |
| start_time | TEXT | Start time (HH:MM:SS) |
| end_time | TEXT | End time or NULL |
| status | TEXT | Mission status |
| objective | TEXT | Mission objective |
| created_at | TEXT | Creation timestamp |
| updated_at | TEXT | Update timestamp |

### `tasks` Table

Manages tasks.

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | Primary key (e.g., `BLD-H-0003` or legacy `T001`) |
| title | TEXT | Short description |
| status | TEXT | Task status |
| priority | TEXT | Priority level |
| role | TEXT | Required role |
| category | TEXT | Task category |
| persona_name | TEXT | Assigned persona |
| mission_id | INTEGER | FK to missions table |
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