# site-nine Architecture

## Overview

site-nine is a **CLI tool** that bootstraps `.opencode/` directory structures in user projects. It provides a framework for AI agent orchestration with built-in task management, session tracking, and daemon naming.

## Design Philosophy

**Bootstrap, Don't Prescribe**: site-nine creates a starting structure but remains flexible. Users can customize templates, add agent roles, and adapt workflows to their needs.

**Agent-Friendly Documentation**: All generated files are designed to be easily parsed and understood by AI agents. Markdown format, clear structure, consistent conventions.

**Local-First**: Everything lives in `.opencode/` directory within the user's project. No external services required. SQLite for data, Markdown for documents.

---

## Technology Stack

### Core Dependencies

- **Python 3.12+**: Modern Python with latest type hints and async features
- **Typer**: CLI framework with automatic help generation and type validation
- **Rich**: Terminal formatting for beautiful output (tables, progress bars, colors)
- **SQLAlchemy**: ORM for SQLite database (tasks, agents, daemon names)
- **Jinja2**: Template engine for generating `.opencode/` files
- **PyYAML**: Config file parsing for `s9 init --config`

### Development Tools

- **pytest**: Unit testing framework
- **ruff**: Fast Python linter and formatter
- **basedpyright**: Type checker (strict mode)
- **uv**: Package manager and virtual environment tool

---

## Project Structure

```
site-nine/
├── src/
│   └── s9/
│       ├── cli/                    # CLI commands (Typer apps)
│       │   ├── __init__.py
│       │   ├── main.py             # Main CLI app
│       │   ├── agent.py            # Agent session commands
│       │   ├── task.py             # Task management commands
│       │   ├── template.py         # Template commands
│       │   ├── config.py           # Config commands
│       │   └── name.py             # Daemon name commands
│       │
│       ├── core/                   # Core business logic
│       │   ├── __init__.py
│       │   ├── models.py           # SQLAlchemy models
│       │   ├── database.py         # Database connection/session
│       │   ├── renderer.py         # Template rendering
│       │   └── config.py           # Configuration management
│       │
│       └── templates/              # Jinja2 templates
│           ├── agents/             # Agent role definitions
│           ├── guides/             # Development guides
│           ├── procedures/         # Standard procedures
│           └── opencode.json       # OpenCode IDE config
│
├── tests/                          # Unit tests
│   ├── cli/                        # CLI command tests
│   └── core/                       # Core logic tests
│
├── docs/                           # User documentation (Sphinx)
│   └── source/
│       ├── index.md
│       ├── quickstart.md
│       ├── reference.md
│       └── usage.md
│
└── .opencode/                      # site-nine's own orchestration
    ├── README.md
    ├── data/
    │   └── project.db              # site-nine's own task database
    └── docs/
        ├── agents/
        ├── guides/
        └── procedures/
```

---

## Architecture Components

### 1. CLI Layer (`src/s9/cli/`)

**Typer-based command-line interface**

- **Main App** (`main.py`): Root CLI with version, init, dashboard, changelog, doctor
- **Agent App** (`agent.py`): Agent session management (start, end, list, pause, resume)
- **Task App** (`task.py`): Task management (create, claim, update, close, search)
- **Template App** (`template.py`): Template browsing (list, show)
- **Config App** (`config.py`): Configuration validation
- **Name App** (`name.py`): Daemon name management (list, suggest, usage, add)

**Benefits:**
- Automatic help generation
- Type validation via Python type hints
- Sub-command organization
- Rich integration for beautiful output

### 2. Database Layer (`src/s9/core/database.py` + `models.py`)

**SQLite + SQLAlchemy ORM**

**Schema:**
```sql
-- Missions (formerly agent sessions)
CREATE TABLE missions (
    id INTEGER PRIMARY KEY,
    codename TEXT NOT NULL,             -- Auto-generated mission codename (e.g., "azure-shadow")
    persona_name TEXT NOT NULL,         -- Persona name (e.g., "kuk", "thoth")
    role TEXT NOT NULL,                 -- Role (Engineer, Tester, etc.)
    status TEXT NOT NULL,               -- active, paused, completed
    mission_file TEXT,                  -- Path to mission markdown file
    objective TEXT,
    started_at TIMESTAMP,
    ended_at TIMESTAMP
);

-- Tasks
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,                -- Format: ROLE-PRIORITY-NUMBER (e.g., ENG-H-0003)
    title TEXT NOT NULL,
    objective TEXT,
    status TEXT NOT NULL,               -- TODO, IN_PROGRESS, COMPLETE
    priority TEXT NOT NULL,             -- LOW, MEDIUM, HIGH, CRITICAL
    role TEXT NOT NULL,
    assigned_mission_id INTEGER,        -- FK to missions.id
    file_path TEXT,                     -- Path to task markdown file
    estimated_hours REAL,
    actual_hours REAL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Task dependencies
CREATE TABLE task_dependencies (
    task_id TEXT,                       -- FK to tasks.id
    depends_on_task_id TEXT,            -- FK to tasks.id
    PRIMARY KEY (task_id, depends_on_task_id)
);

-- Personas (145+ mythology names)
CREATE TABLE personas (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,          -- e.g., "azazel", "thoth"
    role TEXT NOT NULL,                 -- Associated role
    mythology TEXT,                     -- Greek, Norse, Egyptian, etc.
    description TEXT,
    mission_count INTEGER DEFAULT 0     -- How many missions this persona has run
);
```

**Features:**
- SQLite for zero-config local storage
- SQLAlchemy ORM for type-safe queries
- Automatic migrations (future: Alembic)
- Foreign key constraints for referential integrity

### 3. Template Engine (`src/s9/core/renderer.py`)

**Jinja2-based file generation**

**Template Variables:**
```python
context = {
    "project_name": "my-project",
    "project_type": "python",
    "project_description": "My project description",
    "agent_roles": [
        {"name": "Administrator", "enabled": True},
        {"name": "Engineer", "enabled": True},
        # ...
    ],
    "features": {
        "pm_system": True,
        "session_tracking": True,
        "daemon_naming": True,
    }
}
```

**Template Locations:**
- `src/s9/templates/` - Packaged with site-nine
- User can override by creating custom templates

**Rendered Files:**
```
.opencode/
├── README.md                    # From templates/README.md.j2
├── opencode.json                # From templates/opencode.json.j2
├── agents/
│   ├── manager.md               # From templates/agents/manager.md.j2
│   ├── builder.md
│   └── ...
├── guides/
│   ├── AGENTS.md                # From templates/guides/AGENTS.md.j2
│   └── ...
└── procedures/
    ├── COMMIT_GUIDELINES.md
    └── ...
```

### 4. Configuration System (`src/s9/core/config.py`)

**YAML-based project configuration**

**Example `s9.yaml`:**
```yaml
project:
  name: my-project
  type: python
  description: My awesome project

features:
  pm_system: true
  session_tracking: true
  commit_guidelines: true
  daemon_naming: true

agent_roles:
  - name: Administrator
    enabled: true
  - name: Engineer
    enabled: true
  - name: Tester
    enabled: true
```

**Config Validation:**
- Pydantic models for type safety
- Schema validation before init
- Helpful error messages

---

## Key Workflows

### 1. Project Initialization (`s9 init`)

```
User runs: s9 init
    ↓
Load config (YAML or interactive wizard)
    ↓
Validate configuration
    ↓
Create .opencode/ directory structure
    ↓
Render all templates with Jinja2
    ↓
Initialize SQLite database
    ↓
Populate daemon_names table (145+ names)
    ↓
Create opencode.json for IDE integration
    ↓
Success! Project ready for agent orchestration
```

### 2. Mission Start (`s9 mission start`)

```
User runs: s9 mission start <name> --role Engineer --task "Build auth"
    ↓
Check persona name availability
    ↓
Create mission record in database
    ↓
Generate mission file (.opencode/work/missions/YYYY-MM-DD.HH:MM:SS.role.name.codename.md)
    ↓
Mark mission as active
    ↓
Return mission ID for tracking
```

### 3. Task Creation (`s9 task create`)

```
User runs: s9 task create --title "Login" --role Engineer --priority HIGH
    ↓
Generate task ID (ENG-H-0001)
    ↓
Create task record in database
    ↓
Create task markdown file (.opencode/work/tasks/ENG-H-0001.md)
    ↓
Return task ID
```

### 4. Task Workflow

```
1. Create task (TODO status)
2. Persona claims task → status = IN_PROGRESS
3. Persona works on task
4. Persona updates task with progress notes
5. Persona completes work → status = COMPLETE
6. Task file includes commit SHAs, learnings, artifacts
```

---

## Design Decisions

### Why CLI Tool Instead of Library?

**Chosen:** CLI tool (`s9` command)
**Alternative:** Python library (`import s9`)

**Rationale:**
- Users interact with orchestration framework via commands
- CLI is language-agnostic (works for any project type)
- Better UX for non-Python projects
- Natural integration with shell workflows

### Why SQLite Instead of JSON Files?

**Chosen:** SQLite database
**Alternative:** JSON/YAML files for data

**Rationale:**
- Relational data (tasks → missions, task dependencies)
- ACID transactions prevent corruption
- Built-in query capabilities
- Foreign key constraints enforce integrity
- Single-file portability (project.db travels with repo)

### Why Jinja2 Templates Instead of Hardcoded Files?

**Chosen:** Jinja2 templates
**Alternative:** Copy static files

**Rationale:**
- Customization: Users can override templates
- Variables: Project name, roles, features injected
- Conditional logic: Enable/disable sections
- Future: Multiple template "themes" or "flavors"

### Why Local-First Instead of Cloud Service?

**Chosen:** Local `.opencode/` directory
**Alternative:** Cloud-based task management

**Rationale:**
- Privacy: All data stays in user's repo
- Offline: Works without internet
- Git-friendly: Everything version controlled
- Zero config: No accounts, no API keys
- Portability: Clone repo = get full history

---

## Extension Points

### Custom Templates

Users can override templates:

```bash
# site-nine checks ~/.config/s9/templates/ first
mkdir -p ~/.config/s9/templates/agents/
cp my-custom-agent.md.j2 ~/.config/s9/templates/agents/
```

### Custom Agent Roles

Add new roles via database:

```bash
sqlite3 .opencode/data/project.db << EOF
INSERT INTO agent_roles (name, description) 
VALUES ('SecurityAuditor', 'Reviews code for security issues');
EOF
```

### Custom Persona Names

Add names from your favorite mythology:

```bash
s9 persona add --name "MyPersona" --role Engineer --mythology "Custom"
```

---

## Performance Characteristics

- **Init time:** ~1-2 seconds (create directory + populate database)
- **Database queries:** Subsecond (SQLite is fast for local data)
- **Template rendering:** ~100ms for full `.opencode/` structure
- **CLI responsiveness:** <100ms for most commands

---

## Security Considerations

- **No external network calls:** Everything is local
- **No credentials stored:** site-nine doesn't manage auth
- **File permissions:** Respects OS file permissions
- **SQL injection:** SQLAlchemy ORM prevents injection
- **Path traversal:** Template rendering validates paths

---

## Future Architecture Improvements

### Potential Enhancements

1. **Plugin System**
   - Allow third-party agent roles
   - Custom command extensions
   - Template packs

2. **Cloud Sync (Optional)**
   - Sync tasks across team members
   - Centralized persona registry
   - Opt-in, not required

3. **Web Dashboard**
   - Local web UI (`s9 dashboard --web`)
   - Visualize task dependencies
   - Mission activity timeline

4. **API Mode**
   - Run as HTTP server
   - REST API for integrations
   - Webhook support

---

## Comparison to Alternatives

### vs. Manual `.opencode/` Setup

| Aspect | site-nine | Manual |
|--------|-----------|--------|
| Setup time | 1-2 minutes | 30-60 minutes |
| Consistency | ✅ Standardized | ❌ Varies |
| Updates | ✅ Template updates | ❌ Manual sync |
| Task management | ✅ Built-in | ❌ DIY |

### vs. Project Management Tools (JIRA, Linear)

| Aspect | site-nine | PM Tools |
|--------|-----------|----------|
| Setup | ✅ Zero config | ❌ Account needed |
| Privacy | ✅ Local only | ❌ Cloud data |
| Git integration | ✅ Native | ⚠️ Via API |
| Persona-friendly | ✅ Designed for AI | ❌ Human UI |

---

## Key Takeaways

- **site-nine is a CLI tool**, not a library or service
- **Bootstraps `.opencode/` structures** for AI agent orchestration
- **SQLite + Markdown** for data and documentation
- **Jinja2 templates** for customization
- **Local-first** design for privacy and portability
- **Zero external dependencies** (no cloud, no API keys)
