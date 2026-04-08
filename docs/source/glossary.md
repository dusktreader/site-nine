# Glossary

![site-nine glossary](images/facility-2.png){ align=right width="400" }

A comprehensive reference for key concepts and terminology used throughout site-nine.

---

## Core Concepts

### Daemon

A mythology-based name assigned to an AI agent for a specific possession. Each daemon represents a unique working identity with a character drawn from ancient mythology.

**Examples:** Euterpe (Documentarian), Azazel (Engineer), Eris (Tester)

**Key characteristics:**

- Drawn from world mythology (Greek, Norse, Egyptian, Celtic, etc.)
- 256+ names available in the daemon database
- Selected automatically using a 3-day LRU algorithm
- Can be reused across multiple possessions over time
- Each active daemon works in a separate OpenCode terminal

**Usage:**
```bash
# Suggest daemon names for a role
s9 daemon suggest Documentarian --count 3
```

**See also:** [Role](#role), [Possession](#possession)

---

### Role

A specialized function that defines a daemon's capabilities, responsibilities, and area of expertise. Roles determine what type of work a daemon is best suited to perform.

**Available roles:**

- **Administrator** - Coordinate and delegate to other agents
- **Architect** - Design systems and make technical decisions
- **Engineer** - Implement features and write code
- **Tester** - Write tests and validate functionality
- **Documentarian** - Create documentation and guides
- **Designer** - Design user interfaces and experiences
- **Historian** - Document project history and decisions
- **Inspector** - Review code and audit security
- **Operator** - Deploy systems and manage infrastructure

**Key characteristics:**

- Each role has specialized knowledge and best practices
- Tasks are assigned to specific roles
- Multiple daemons can share the same role
- Role determines default workflows and priorities

**Usage:**
```bash
# Start a possession with a specific role
s9 summon documentarian

# View role-filtered dashboard
s9 dashboard --role Documentarian
```

**See also:** [Daemon](#daemon), [Task](#task), [Agent Roles documentation](agents/roles.md)

---

### Possession

A working session where a daemon (AI agent) actively works on project tasks. Each possession has a unique codename, objective, and tracks the daemon's activities.

**Possession lifecycle:**

1. **ROLE_PENDING** - Possession initialized, awaiting role selection
2. **DAEMON_PENDING** - Role selected, awaiting daemon assignment
3. **ACTIVE** - Daemon working on tasks and making changes
4. **SUSPENDED** - Possession exists but daemon is not actively working
5. **EXORCISED** - Possession ended and work documented

**Key characteristics:**

- Each possession gets a unique codename
- Tracked in the database with status, start time, and objective
- Generates a possession file at `.opencode/work/possessions/YYYY-MM-DD.HH-MM-SS.role.Daemon.md`
- Multiple possessions can run in parallel (different terminals)

**See also:** [Daemon](#daemon), [Session](#session), [Codename](#codename)

---

### Task

A discrete unit of work with a specific objective, priority, assigned role, and tracked status. Tasks are the fundamental building blocks of project management in site-nine.

**Task components:**

- **Task ID** - Unique identifier (e.g., `DOC-M-0056`)
- **Title** - Brief description of the work
- **Description** - Detailed context and requirements
- **Role** - Which type of daemon should handle this
- **Priority** - CRITICAL, HIGH, MEDIUM, or LOW
- **Status** - Current state (TODO, UNDERWAY, BLOCKED, etc.)
- **Dependencies** - Other tasks that must complete first
- **Epic** - Optional parent epic for grouping

**Task statuses:**

- **TODO** - Ready to be claimed
- **UNDERWAY** - Actively being worked on
- **BLOCKED** - Waiting on dependencies or external factors
- **REVIEW** - Work complete, awaiting review
- **PAUSED** - Temporarily suspended
- **COMPLETE** - Successfully finished
- **ABORTED** - Cancelled or no longer needed

**Usage:**
```bash
# Create a task
s9 task create --title "Create glossary" --role Documentarian --priority MEDIUM

# Claim a task
s9 task claim DOC-M-0056

# Show task details
s9 task show DOC-M-0056

# Close a task
s9 task close DOC-M-0056 --status COMPLETE
```

**See also:** [Epic](#epic), [Task ID](#task-id), [Priority](#priority), [Status](#status)

---

### Epic

An organizational container that groups related tasks under a larger initiative or feature. Epics help track overall progress for complex projects spanning multiple tasks and roles.

**Key characteristics:**

- **Purely organizational** - Not assigned to specific daemons
- **One task, one epic** - Tasks belong to at most one epic
- **Auto-computed status** - Updates automatically based on subtask states
- **Progress tracking** - Shows completion percentage and task breakdown
- **Database-driven** - Stored in database, markdown files are generated artifacts

**Epic lifecycle:**

1. **Create** - Define epic with title and priority
2. **Link tasks** - Add new or existing tasks to the epic
3. **Track progress** - Monitor as tasks are completed
4. **Complete** - Automatically marked when all tasks finish
5. **Abort** - Manually cancel if requirements change

**Epic statuses:**

- **TODO** (📋) - All subtasks are TODO or ABORTED
- **UNDERWAY** (🚧) - At least one subtask is being worked on
- **COMPLETE** (✅) - All subtasks completed
- **ABORTED** (❌) - Manually cancelled, subtasks also aborted

**Usage:**
```bash
# Create an epic
s9 epic create --title "User Authentication System" --priority HIGH

# Link tasks to epic
s9 task create --title "Design auth flow" --role Architect --epic EPC-H-0001
s9 task link ARC-H-0015 EPC-H-0001

# View epic progress
s9 epic show EPC-H-0001
s9 dashboard --epic EPC-H-0001

# Abort an epic
s9 epic abort EPC-H-0001 --reason "Requirements changed"
```

**See also:** [Task](#task), [Epic ID](#epic-id), [Epics documentation](epics/overview.md)

---

### Handoff

A mechanism for transferring work context from one daemon to another, ensuring continuity and knowledge sharing across role boundaries.

**Handoff workflow:**

1. **Create** - Originating daemon creates handoff with context
2. **Pending** - Handoff awaits acceptance by target role
3. **Accept** - Receiving daemon accepts and claims the work
4. **Complete** - Work transition is finished

**Key characteristics:**

- Includes task information, context, and notes
- Filtered by role (e.g., only Engineers see Engineer handoffs)
- Checked automatically during possession start
- Ensures smooth transitions between specialized roles

**Usage:**
```bash
# Create a handoff for a task
s9 handoff create TSK-H-0042 --role Engineer --message "Ready for implementation"

# List pending handoffs for your role
s9 handoff list --role Engineer --status pending

# Accept a handoff
s9 handoff accept <handoff-id>

# Show handoff details
s9 handoff show <handoff-id>
```

**See also:** [Role](#role), [Task](#task), [Review](#review)

---

### Review

A quality assurance process where completed work is evaluated before being marked as complete. Reviews ensure code quality, adherence to standards, and catch issues early.

**Review workflow:**

1. **Create** - Task owner requests review
2. **Pending** - Awaiting reviewer action
3. **Approved** - Reviewer accepts the work
4. **Changes requested** - Reviewer identifies issues to fix
5. **Complete** - Review process finished

**Key characteristics:**

- Typically handled by Administrator or Inspector roles
- Can block task completion until approved
- Includes comments and feedback
- Part of quality control process

**Usage:**
```bash
# Create a review request
s9 review create TSK-H-0042 --message "Ready for review"

# List pending reviews
s9 review list --status pending

# Approve a review
s9 review approve <review-id> --comment "Looks good!"

# Request changes
s9 review request-changes <review-id> --comment "Please add tests"
```

**See also:** [Task](#task), [Status](#status)

---

## Identifiers

### Task ID

A structured identifier that uniquely identifies a task and encodes its role and priority.

**Format:** `[ROLE]-[PRIORITY]-[NUMBER]`

**Components:**

- **ROLE** - 3-letter role prefix:
    - `ADM` - Administrator
    - `ARC` - Architect  
    - `ENG` - Engineer
    - `TST` - Tester
    - `DOC` - Documentarian
    - `DSN` - Designer
    - `HST` - Historian
    - `INS` - Inspector
    - `OPR` - Operator
- **PRIORITY** - Single letter:
    - `C` - CRITICAL
    - `H` - HIGH
    - `M` - MEDIUM
    - `L` - LOW
- **NUMBER** - Sequential 4-digit number (zero-padded)

**Examples:**

- `DOC-M-0056` - Documentarian task, MEDIUM priority, #56
- `ENG-H-0002` - Engineer task, HIGH priority, #2
- `TST-C-0001` - Tester task, CRITICAL priority, #1

**Benefits:**

- Easy to identify role and priority at a glance
- Sortable and filterable
- Human-readable in logs and commit messages

**See also:** [Task](#task), [Epic ID](#epic-id), [Role](#role), [Priority](#priority)

---

### Epic ID

A structured identifier for epics, similar to Task IDs but with an "EPC" prefix.

**Format:** `EPC-[PRIORITY]-[NUMBER]`

**Components:**

- `EPC` - Epic prefix (constant)
- **PRIORITY** - Single letter (C/H/M/L)
- **NUMBER** - Sequential 4-digit number

**Examples:**

- `EPC-H-0001` - First HIGH priority epic
- `EPC-C-0015` - Epic #15 with CRITICAL priority
- `EPC-M-0042` - Epic #42 with MEDIUM priority

**See also:** [Epic](#epic), [Task ID](#task-id)

---

### Codename

A randomly generated, memorable identifier assigned to each possession for easy reference and session naming.

**Characteristics:**

- Auto-generated when possession starts
- Unique per possession
- Used in possession filenames
- Appears in OpenCode session titles

**Examples:** phoenix-delta, nebula-seven, thunder-alpha

**See also:** [Possession](#possession)

---

## Status Values

### Status

The current state of a task, indicating its progress through the workflow.

**Task statuses:**

| Status | Symbol | Description |
|--------|--------|-------------|
| TODO | ⬜ | Ready to be claimed and started |
| UNDERWAY | 🔵 | Actively being worked on |
| BLOCKED | 🔴 | Waiting on dependencies or external factors |
| REVIEW | 🟡 | Work complete, awaiting review |
| PAUSED | ⏸️ | Temporarily suspended |
| COMPLETE | ✅ | Successfully finished |
| ABORTED | ❌ | Cancelled or no longer needed |

**Epic statuses:**

| Status | Symbol | Description |
|--------|--------|-------------|
| TODO | 📋 | All subtasks TODO or ABORTED |
| UNDERWAY | 🚧 | At least one subtask in progress |
| COMPLETE | ✅ | All subtasks completed |
| ABORTED | ❌ | Manually cancelled |

**Mission statuses:**

| Status | Description |
|--------|-------------|
| ACTIVE | Persona currently working |
| IDLE | Mission exists but not actively working |
| COMPLETE | Mission ended, work documented |

**See also:** [Task](#task), [Epic](#epic), [Mission](#mission)

---

### Priority

A ranking that indicates the urgency and importance of tasks and epics, helping teams focus on critical work first.

**Priority levels:**

| Priority | Symbol | When to use |
|----------|--------|-------------|
| CRITICAL | 🔴 | Urgent blockers, production issues, critical path items |
| HIGH | 🟠 | Important features, significant bugs, deadline-driven work |
| MEDIUM | 🟡 | Standard features, improvements, technical debt |
| LOW | 🟢 | Nice-to-have features, minor improvements, future work |

**Priority in IDs:**

- Encoded in Task IDs and Epic IDs as a single letter (C/H/M/L)
- Makes priority visible at a glance
- Used for sorting and filtering

**Best practices:**

- Not everything can be CRITICAL - use sparingly
- HIGH priority for features on current milestone
- MEDIUM for planned work in the backlog
- LOW for speculative or future improvements

**See also:** [Task](#task), [Epic](#epic), [Task ID](#task-id)

---

## System Components

### Dashboard

A real-time project overview showing active possessions, task summaries, epic progress, and quick statistics.

**Information displayed:**

- **Quick Stats** - Active possessions, total tasks, completion rates
- **Active Epics** - Top epics in TODO/UNDERWAY status
- **Active Possessions** - Currently running daemons and their work
- **Task Summary** - Tasks by status and priority
- **Recent Activity** - Latest task updates

**Dashboard views:**

```bash
# Full project dashboard
s9 dashboard

# Epic-specific view
s9 dashboard --epic EPC-H-0001

# Role-filtered view
s9 dashboard --role Documentarian
```

**Use cases:**

- Check project health at a glance
- See what daemons are working on
- Identify bottlenecks and blocked work
- Track epic and task progress
- Start of day project status review

**See also:** [Possession](#possession), [Epic](#epic), [Task](#task)

---

### Session

An OpenCode conversation instance where a daemon works on tasks. Each session corresponds to one OpenCode terminal window.

**Key characteristics:**

- One session = one OpenCode terminal
- Sessions can be named/renamed for organization
- Multiple sessions can run in parallel
- Each session has one active daemon/possession
- Session title includes daemon name, role, and codename

**Session naming:**

When a possession starts, the OpenCode session is automatically renamed to:
```
Operation <codename>: <Daemon> - <Role>
```

Example: `Operation silver-titan: Fukurokuju - Documentarian`

**Multi-session workflows:**

Run multiple daemons simultaneously in separate terminals:
- Terminal 1: Administrator coordinating work
- Terminal 2: Architect designing system
- Terminal 3: Engineer implementing features
- Terminal 4: Tester validating implementation

**See also:** [Possession](#possession), [Daemon](#daemon), [Advanced Topics documentation](advanced.md)

---

### Database

A SQLite database (`.opencode/data/project.db`) that stores all project management data including tasks, possessions, daemons, epics, and relationships.

**Database tables:**

- `daemons` - Available daemon names and usage tracking
- `possessions` - Possession history and status
- `tasks` - Task definitions and metadata
- `epics` - Epic definitions and progress
- `dependencies` - Task dependency relationships
- `handoffs` - Work transfer records
- `reviews` - Review requests and outcomes

**Important notes:**

- **Never edit directly** - Always use `s9` CLI commands
- Database is the source of truth
- Markdown files are generated from database
- Backed up with `.db-journal` and `.db-wal` files

**Database health:**

```bash
# Check database integrity
s9 doctor

# Fix common issues
s9 doctor --fix
```

**See also:** [.opencode Directory](#opencode-directory), [Directory Structure documentation](structure.md)

---

### .opencode Directory

The project directory created by `s9 init` that contains all site-nine configuration, data, and documentation.

**Directory structure:**

```
.opencode/
├── README.md              # Setup guide
├── data/                  # Database and storage
│   └── project.db         # SQLite database
├── docs/                  # Agent reference documentation
├── skills/                # OpenCode skills for possession lifecycle
├── tasks/                 # Task markdown files
└── work/                  # Active work artifacts
    ├── possessions/       # Possession documentation
    └── epics/             # Epic markdown files
```

**What you can edit:**

- `README.md` - Customize for your team
- `docs/*.md` - Add team-specific documentation

**What not to edit:**

- `data/project.db` - Use CLI commands instead
- `tasks/*.md` - Synced with database
- `work/possessions/*.md` - Managed by agents

**See also:** [Database](#database), [Directory Structure documentation](structure.md)

---

## Workflow Concepts

### Dependency

A relationship between tasks where one task must be completed before another can begin. Dependencies ensure work happens in the correct order.

**Key characteristics:**

- One-to-many: One task can have multiple dependencies
- Blocking: Tasks with incomplete dependencies are BLOCKED
- Visible in dashboard and task details
- Used for planning and sequencing work

**Usage:**
```bash
# Add a dependency (ENG-H-0016 depends on ARC-H-0015)
s9 task add-dependency ENG-H-0016 ARC-H-0015

# Remove a dependency
s9 task remove-dependency ENG-H-0016 ARC-H-0015

# View task dependencies
s9 task show ENG-H-0016
```

**Common patterns:**

- Architecture → Implementation → Testing → Documentation
- Design → Frontend → Backend → Integration
- Planning → Development → Review → Deployment

**See also:** [Task](#task), [Status](#status)

---

### Claim

The action of a daemon taking ownership of a task, indicating they will work on it.

**Claim workflow:**

1. **View available tasks** - Check dashboard or task list
2. **Claim task** - Daemon takes ownership
3. **Status changes** - Task moves from TODO to UNDERWAY
4. **Work begins** - Daemon starts implementation
5. **Complete task** - Daemon closes task when done

**Usage:**
```bash
# Claim a task
s9 task claim DOC-M-0056

# Unclaim if needed
s9 task unclaim DOC-M-0056
```

**Best practices:**

- Claim tasks appropriate for your role
- Don't claim more tasks than you can actively work on
- Update task status as work progresses
- Unclaim if you can't complete the task

**See also:** [Task](#task), [Status](#status)

---

### ADR (Architecture Decision Record)

A document that captures an important architectural decision along with its context and consequences. ADRs are typically created by Architect daemons.

**ADR structure:**

- **Title** - The decision made
- **Status** - Proposed, Accepted, Deprecated, Superseded
- **Context** - What led to this decision
- **Decision** - What was chosen and why
- **Consequences** - Impact and trade-offs

**Where stored:**

Typically in `docs/adr/` or `.opencode/planning/`, following a numbering convention like:
- `0001-use-jwt-tokens.md`
- `0002-choose-database-postgres.md`

**See also:** [Architect Role](agents/roles.md#architect)

---

## Operations

### s9 CLI

The command-line interface for interacting with site-nine, providing commands for tasks, missions, epics, personas, and project management.

**Command categories:**

- **Initialization** - `s9 init`, `s9 doctor`
- **Project overview** - `s9 dashboard`
- **Task management** - `s9 task create|claim|show|close|list`
- **Epic management** - `s9 epic create|show|list|abort|sync`
- **Mission management** - `s9 mission start|end|list|update`
- **Persona operations** - `s9 persona suggest|claim|release`
- **Handoffs** - `s9 handoff create|list|accept|show`
- **Reviews** - `s9 review create|list|approve`

**Getting help:**
```bash
# General help
s9 --help

# Command-specific help
s9 task --help
s9 epic create --help
```

**See also:** [CLI Reference documentation](cli/overview.md)

---

### s9 summon

The CLI command that starts a new possession by launching OpenCode and triggering the `possession-start` skill for the specified role.

**Usage:**

```bash
s9 summon <role>
```

**Examples:**
```bash
s9 summon documentarian
s9 summon engineer
s9 summon operator --auto-assign
```

**What it does:**

1. Launches OpenCode
2. Triggers the `possession-start` skill
3. Initializes a possession in ROLE_PENDING state
4. Records the role and transitions to DAEMON_PENDING
5. Auto-claims a daemon via LRU selection
6. Transitions to ACTIVE, renames the session
7. Shows role-specific task dashboard

**See also:** [Possession](#possession), [Daemon](#daemon), [Role](#role)

---

## Best Practices

### Possession File

A markdown file automatically generated for each possession that documents the daemon's work, decisions, and progress.

**Location:** `.opencode/work/possessions/YYYY-MM-DD.HH-MM-SS.role.Daemon.md`

**Contents:**

- Possession metadata (daemon, role, objective, start time)
- Work summary and accomplishments
- Decisions made
- Files changed
- Tasks claimed and completed
- Notes and context

**Management:**

- Auto-generated when possession starts
- Updated by daemon throughout possession
- Provides historical record of work

**See also:** [Possession](#possession), [Daemon](#daemon)

---

### Commit Message

Git commit messages in site-nine projects typically include persona or mission identification for traceability.

**Recommended formats:**

```bash
# With persona name and role
[Persona: Euterpe - Documentarian] Add glossary page to docs

# With mission codename
[Mission: phoenix-delta] Implement user authentication

# Standard format for clarity
<type>: <description>

[Persona: <name> - <role>]
<optional detailed body>
```

**Common types:**

- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation changes
- `refactor` - Code refactoring
- `test` - Adding or updating tests
- `chore` - Maintenance tasks

**See also:** `.opencode/procedures/COMMIT_GUIDELINES.md`

---

## Troubleshooting

### Doctor Command

A diagnostic tool that checks database integrity, validates relationships, and identifies common issues.

**Usage:**
```bash
# Run health checks
s9 doctor

# Show detailed output
s9 doctor --verbose

# Automatically fix safe issues
s9 doctor --fix
```

**What it checks:**

- Database integrity
- Invalid foreign key references
- Inconsistent task states
- Orphaned dependencies
- Missing referenced files
- Possession data issues

**See also:** [Database](#database), [CLI Reference](cli/overview.md)

---

## Related Documentation

For more detailed information on specific topics:

- **[Quickstart Guide](quickstart.md)** - Get started in 5 minutes
- **[Agent Roles](agents/roles.md)** - Detailed role descriptions and best practices
- **[Directory Structure](structure.md)** - Understanding the .opencode directory
- **[Epics](epics/overview.md)** - Complete guide to epic workflow
- **[Advanced Topics](advanced.md)** - Multi-agent workflows and patterns
- **[CLI Reference](cli/overview.md)** - Complete command documentation

---

## Mythology References

site-nine uses names from world mythology for daemons, drawing from diverse cultural traditions:

**Mythological traditions included:**

- **Greek** - Zeus, Athena, Hermes, Euterpe, etc.
- **Norse** - Odin, Thor, Loki, Freya, etc.
- **Egyptian** - Ra, Thoth, Anubis, Isis, etc.
- **Celtic** - Brigid, Cernunnos, Morrigan, etc.
- **Mesopotamian** - Marduk, Ishtar, Gilgamesh, etc.
- **Hindu** - Brahma, Vishnu, Shiva, Lakshmi, etc.
- **Japanese** - Amaterasu, Susanoo, Inari, etc.
- **And many more...**

**Why mythology?**

- Memorable and distinctive names
- Rich cultural heritage
- Easier to remember than IDs or random strings
- Adds personality to the workflow
- 256+ unique names ensure variety

**See also:** [Daemons documentation](agents/daemons.md)
