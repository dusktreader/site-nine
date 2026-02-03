# OpenCode Configuration for s9 Development

This directory contains OpenCode agent configuration for **developing** the s9 python project.

**Important**: This is NOT configuration for using/operating s9. This is for building and maintaining the codebase.


## Quick Start

### First Time Setup

```bash
# Install site-nine in editable mode (REQUIRED for development)
uv sync

# Install as uv tool (recommended for CLI access)
uv tool install --editable .

# Verify installation
s9 --help

# Configure environment (optional - Docker works without .env)
cp .env.example .env
# Edit .env if you need custom configuration

# Start docker services and open web demo
make demo
# This starts Docker services and opens web demo at http://localhost:15000

# Stop when done
docker compose down
```

**Optional: Run tests**
```bash
# Start Docker services for testing
docker compose up -d

# Run all tests
make qa/test-all
```

### Starting a Development Session

> [!TIP]
> **RECOMMENDED: Use the `/summon` command to start a new session!**
> 
> Type `/summon` for interactive mode (agent asks for role), or use `/summon <role>` 
> to start directly with a specific role (e.g., `/summon operator`, `/summon builder`).
> 
> The agent will guide you through daemon naming, session file creation, and 
> documentation reading automatically.
> 
> See `.opencode/docs/commands/README.md` for details about the `/summon` command.

> [!NOTE]
> **How sessions start**
> 
> Sessions are initiated by the Director using the `/summon` command.
> The agent will then guide you through the session start protocol below.

**Session Start Protocol:**

1. **Director invokes:** `/summon` command (or `/summon <role>` to skip role selection)

2. Agent asks: **"Which role should I assume?"** (skipped if role provided)
   - Administrator, Architect, Builder, Tester, Documentarian, Designer, or Inspector
   - **Pro tip:** Use `/summon operator` to start an Operator session immediately

3. Agent suggests or asks for a **daemon name** (from any religion's mythology)
   - **Prefer unused names first** - use `s9 name suggest <Role>` to get unused name suggestions
   - 142+ names available from various mythologies (Greek, Egyptian, Norse, Hindu, Celtic, Japanese, and more)
   - **Reusing names is OK** when good unused names are exhausted, but try fresh names first
   - If name used before, adds roman numeral: `-ii`, `-iii`, `-iv`, etc.

4. Agent introduces itself with **full name including suffix**: **"I'm [Name], your [Role] agent."**
   - ✅ If first use: "I'm Seraphina, your Designer agent."
   - ✅ If reused name: "I'm Seraphina-iii, your Designer agent." (includes `-iii` suffix)
   - ❌ Wrong: "I'm Seraphina, your Designer agent." (when name is Seraphina-iii)

5. Session file is created in `.opencode/work/sessions/` with format:  
   `YYYY-mm-dd.HH:MM:SS.role.name.task-summary.md`

6. Agent uses that name (with suffix if applicable) in all commits, changelog entries, and docs

**Example (Choosing an Unused Name - Preferred):**
```
User: /summon
Agent: Which role should I assume for this session?
User: Builder
Agent: Let me suggest an unused name for Builder role...
       
       I suggest "Belial" - a demon king from Hebrew tradition who taught humans metalworking.
       This name hasn't been used yet.
       Would you like to use this name or choose another?
User: That works
Agent: Great! I'm Belial, your Builder agent. What would you like me to work on?
```

**Example (Reusing Name When Necessary):**
```
User: /summon
Agent: Which role should I assume for this session?
User: Documentarian
Agent: I see "Thoth" has been used 3 times already. I could suggest "Thoth-iv" (fourth use),
       or I could pick an unused name like "Seshat" (Egyptian goddess of writing and wisdom)?
User: Let's go with Seshat
Agent: Great! I'm Seshat, your Documentarian agent. What would you like me to work on?
```

**Example (Direct Mode - Skip Role Selection):**
```
User: /summon operator
Agent: I suggest "Hemera" (Greek goddess of day). Would you like to use this name?
User: yes
Agent: Great! I'm Hemera, your Operator agent. What would you like me to work on?
```

### During Development

Just talk naturally to your agent:

```
"Add rate limiting to the database query tools"
"Fix the bug where queries timeout"
"Review the authentication code for security issues"
```

The agent will use their assigned role and name consistently throughout the session.

### Choosing Agent Names (For Agents)

**IMPORTANT: Prefer unused names over reusing existing names.**

Before suggesting a name:
1. Use `s9 name suggest <Role>` to get unused name suggestions
2. Use `s9 name usage <name>` to check if a name has been used
3. **Always prefer an unused name** from the 142+ names available
4. Only reuse a name (with roman numeral suffix) when most good names are taken

**Why this matters:**
- Makes it easier to track which agent did what work
- Reduces confusion when reading git history
- Gives each agent session a unique identity
- There are 142+ names available across 8+ mythologies - use them!

**Available mythologies**:
- **Greek/Roman** - Zeus, Athena, Hephaestus, etc.
- **Egyptian** - Ra, Thoth, Anubis, etc.
- **Norse** - Odin, Thor, Freya, etc.
- **Hindu/Buddhist** - Brahma, Shiva, Kali, etc.
- **Celtic/Gaelic** - Brigid, Lugh, Morrigan, etc.
- **Japanese** - Amaterasu, Susanoo, Benzaiten, etc.
- **Mesopotamian** - Marduk, Ishtar, Enki, etc.
- **Aztec/Mayan/African** - Quetzalcoatl, Anansi, etc.

**Browse available names**:
```bash
s9 name list --role <Role>        # See all names for a role
s9 name list --unused-only        # See only unused names
s9 name suggest <Role> --count 3  # Get 3 unused suggestions
```


---


## Specialized Agents

### Administrator (Default - Primary Interface)

**File**: `agents/manager.md`

**Use for**: Your main interaction point. Delegates to specialized agents based on task.

**Example**:
```
"Add rate limiting to external MCP calls"
→ Administrator coordinates: Architect → Builder → Tester → Documentarian
```


### Architect

**File**: `agents/architect.md`

**Use for**: Planning features, designing solutions, making architecture decisions

**Invoke**: `@architect`

**Example**:
```
"Design a token authentication system"
→ Architect creates design document, presents options
```


### Builder

**File**: `agents/builder.md`

**Use for**: Implementing features, writing code AND tests, fixing bugs

**Invoke**: `@builder`

**Example**:
```
"Implement the rate limiting feature"
→ Builder writes code + tests, runs QA checks
```


### Tester

**File**: `agents/tester.md`

**Use for**: Manual testing, running tests, validating features (does NOT write tests)

**Invoke**: `@tester`

**Example**:
```
"Test the database connection pooling"
→ Tester runs tests, tries different scenarios, reports findings
```


### Documentarian

**File**: `agents/documentarian.md`

**Use for**: Writing/updating documentation, docstrings, guides

**Invoke**: `@documentarian`

**Example**:
```
"Update README with token authentication setup"
→ Documentarian updates docs, maintains consistency
```


### Designer

**File**: `agents/designer.md`

**Use for**: UI/UX design, design specifications, user flows, accessibility

**Invoke**: `@designer`

**Example**:
```
"Design the Slack bot message format for investigation results"
→ Designer creates message templates, documents specs
```


### Inspector

**File**: `agents/inspector.md`

**Use for**: Code review, finding issues, checking consistency, security audits

**Invoke**: `@inspector`

**Example**:
```
"Review the knowledge base code for issues"
→ Inspector finds redundancies, inconsistencies, missing docs
```


### Operator

**File**: `agents/operator.md`

**Use for**: Meta-development - maintaining `.opencode/` infrastructure, agent definitions, scripts, workflows

**Invoke**: `@operator`

**Example**:
```
"Create a new agent type for security auditing"
→ Operator creates agent definition, updates configuration, documents usage
```


### Historian

**File**: `agents/historian.md`

**Use for**: Project history, change tracking, ADRs, retrospectives, CHANGELOG maintenance

**Invoke**: `@historian`

**Example**:
```
"Create retrospective for Phase 7"
→ Historian analyzes git history, generates retrospective document, captures lessons learned
```


---


## Commit Guidelines (Quick Reference)

**All agents use Conventional Commits format with agent attribution.**

**Format:**
```bash
git commit -m "feat(database): add connection pooling [Agent: Builder - Azazel]"
git commit -m "docs(readme): update setup guide [Agent: Documentarian - Seraphina-iii]"
```

**Note**: If the agent name has a roman numeral suffix (e.g., `-iii`), include it in the commit message.

**Common types**: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`, `perf:`, `style:`, `ci:`

**Workflow**:
1. Make changes
2. Update task artifact in `.opencode/work/tasks/TASK_ID.md`
3. Run `make qa`
4. Commit with conventional format
5. Repeat for next unit of work

**See**: `.opencode/docs/procedures/COMMIT_GUIDELINES.md` for complete reference and examples.


---


## Task Artifact Updates (Quick Reference)

**Document your work in task artifacts as you go!**

Task artifacts are located in `.opencode/work/tasks/{TASK_ID}.md`

**What to update during work:**
- **Implementation Steps** - Chronological log of what you did
- **Files Changed** - List of files modified with descriptions
- **Notes** - Important observations or decisions
- **Testing Performed** - Tests run and results

**When completing a task:**
- **Solutions Implemented** - High-level summary
- **Verification Results** - How acceptance criteria were met
- **Key Learnings** - Insights for future work
- **Git Commits** - List of commit SHAs

**Generate changelog from tasks:**
```bash
s9 changelog --since 2026-01-29
```

**See**: `.opencode/docs/procedures/COMMIT_GUIDELINES.md` for task workflow details.


---


## Example Workflows (Quick Reference)

**Adding a Feature:**
1. Administrator → @architect (design)
2. Administrator → @designer (UI/UX specs, if user-facing)
3. You approve
4. Administrator → @builder (implement + tests)
5. Administrator → @tester (validate)
6. Administrator → @documentarian (docs)
7. Administrator → @inspector (review)

**Fixing a Bug:**
1. Administrator → @tester (reproduce)
2. Administrator → @builder (fix + test)
3. Administrator → @tester (verify)

**See**: `.opencode/docs/procedures/WORKFLOWS.md` for detailed workflows, parallel work patterns, and more examples.


---


## Project Structure

```
site-nine/
├── src/
│   └── s9/                  # Main package
│       ├── cli/             # CLI commands
│       ├── core/            # Core framework
│       └── templates/       # Project templates
├── tests/                   # Unit tests
├── .opencode/               # This directory
│   ├── docs/                # Static instructions
│   │   ├── agents/          # Agent role definitions
│   │   ├── commands/        # Slash command instructions
│   │   ├── guides/          # Development patterns
│   │   ├── procedures/      # Operational how-tos
│   │   └── skills/          # Reusable skill workflows
│   ├── work/                # Tracking documents
│   │   ├── sessions/        # Agent session logs
│   │   ├── tasks/           # Task artifacts
│   │   └── planning/        # Strategic planning docs
│   ├── data/                # Data storage
│   │   └── project.db       # SQLite database
│   ├── scripts/             # Utility scripts
│   └── README.md            # This file
├── .env.example             # Configuration template (if needed)
├── Makefile                 # Development tasks
└── pyproject.toml           # Project config
```


---


## Key Commands

```bash
# Development
make demo                    # Start docker services + open web demo

# Quality checks
make qa                      # Run all checks (test + lint + types)
make qa/test                 # Run unit tests
make qa/test-integration     # Run integration tests (needs docker)
make qa/format               # Format code
make qa/lint                 # Lint code

# Docker (advanced)
docker compose up -d         # Start services
docker compose down          # Stop services
docker compose logs -f       # View logs

# Help
make help                    # Show all available commands
```


---


## Key Principles

When working on s9:

1. **Safety First**: Database access is read-only only
2. **Human in the Loop**: Propose solutions, get approval
3. **Guided Access**: Provide context (schema docs, query templates)
4. **Testing Required**: All features need tests
5. **Security**: Query validation, no hardcoded credentials


---


## Technology Stack

- **Python 3.12+** with uv for package management
- **FastMCP** - python framework
- **SQLAlchemy** - Database access (PostgreSQL, MySQL, SQLite)
- **DuckDB** - Knowledge base (embedded analytics)
- **pytest/pytest-bdd** - Testing
- **ruff** - Formatting and linting
- **basedpyright** - Type checking


---


## Architecture

**Hybrid MCP Pattern**: s9 acts as both:
- **python**: Exposes tools to AI agents
- **MCP Client**: Delegates to external pythons (JIRA, GitHub, Confluence)

**Benefits**: Single configuration point for users, unified tool interface


---


## Project Management System

**Unified management system** for tasks, agent sessions, and daemon names via the `s9` CLI:

```bash
# Quick project overview
s9 dashboard                # Show current status, active work, and available tasks

# Health checks and data integrity
s9 doctor                   # Run diagnostics (read-only)
s9 doctor --fix             # Fix issues automatically

# View available daemon names
s9 name suggest <Role>

# Start agent session (auto-registers and tracks usage)
s9 agent start <name> --role <Role> --session-file "..." --task-summary "..."

# Manage agent sessions
s9 agent pause <agent-id> [--reason "reason"]     # Pause active session
s9 agent resume <agent-id>                        # Resume paused session
s9 agent update <agent-id> [--task-summary "..."] [--role NewRole]  # Update session

# Manage tasks
s9 task next --role <Role>                    # Get smart task suggestions
s9 task search "<keyword>" --active-only      # Search for tasks
s9 task mine --agent-name <name>              # Show your claimed tasks
s9 task list --role <Role> --active-only
s9 task report --active-only                  # Generate task summary report
s9 task create --title "..." --objective "..." --role <Role> --priority <PRIORITY>  # Task ID auto-generated
s9 task claim <TASK_ID> --agent-name <name> --agent-id <ID>
s9 task update <TASK_ID> --notes "..." --actual-hours X.X
s9 task close <TASK_ID> --status COMPLETE

# Manage task templates (reusable task patterns)
s9 template list                              # See available templates
s9 template show <template-id>                # View template details

# End session
s9 agent end <ID> --status completed
```

**Documentation:**
- **`.opencode/data/README.md`** - Complete reference (schema, commands, workflows)
- **`.opencode/data/project.db`** - SQLite database (daemon names, tasks, agent sessions)


## Important Files

### For Development
- **`.opencode/docs/guides/AGENTS.md`** - Development patterns (READ THIS FIRST!)
- **`s9`** - **Unified project management CLI (tasks, agents, names)**
- **`.opencode/data/README.md`** - **Complete s9 system reference**
- **`.opencode/work/sessions/README.md`** - Session tracking format and guidelines
- **`.opencode/work/planning/build.md`** - Implementation phases
- **`.opencode/work/planning/PROJECT_STATUS.md`** - **Current project status and progress** (use this!)
- **`.opencode/docs/procedures/COMMIT_GUIDELINES.md`** - Commit format reference
- **`.opencode/docs/procedures/TASK_WORKFLOW.md`** - Task-first documentation workflow
- **`Makefile`** - Development commands
- **`.env.example`** - Configuration template

### For Reference
- **`.opencode/docs/guides/architecture.md`** - Architecture overview
- **`.opencode/docs/guides/database.md`** - Database patterns
- **`.opencode/docs/guides/design-philosophy.md`** - Design philosophy
- **`.opencode/docs/guides/design-system.md`** - Design system documentation (if created)
- **`.opencode/design/*.md`** - Feature design documents


---


## Current Status

**Completed** ✅:
- Phase 1: Foundation (python skeleton)
- Phase 2: External MCP Delegation (JIRA, GitHub, Confluence)
- Phase 3: Database Integration (guided access, query validation)
- Phase 4: Knowledge Base (DuckDB + S3 hybrid storage)
- Phase 5: Investigation Locks (prevent duplicate work)
- Phase 6: Write Queue (DuckDB concurrency)
- Phase 7: Rate Limiting (protect external APIs)
- Phase 8: Slack Bot (OpenCode HTTP integration)

**Current Focus** 🔨:
- Phase 9: Integration Testing & Validation

**Future Work** 📋 (Not Currently Planned):
- Production deployment and hardening
- Production security audit
- Production monitoring and alerting
- Production CI/CD pipeline
- Production launch activities

See `.opencode/work/planning/PROJECT_STATUS.md` for current project status and phase completion.


---


## Tips for Success

### 1. Every Session Starts with Role Selection

Each development session begins with the agent asking which role to assume and what name to use. This creates consistency and accountability:

- Agent uses the same name (including suffix) throughout the session
- Commits include the agent name: `[Agent: Builder - Azazel]` or `[Agent: Designer - Seraphina-iii]`
- Task artifacts document all work done
- Session history tracks all work done

### 2. Start with the Administrator (or Pick Your Role)

If you're starting a new task and aren't sure which role is best, choose Administrator. It will coordinate and delegate. If you know what you need, pick the specific role.

### 3. Be Specific About Goals

✅ Good: "Add rate limiting to database queries with 50/minute limit"  
❌ Less good: "Make it faster"

### 4. Agents Read AGENTS.md

The agents are configured to read `.opencode/docs/guides/AGENTS.md` for patterns. Keep it updated with lessons learned.

### 5. Builder Writes Tests, Tester Runs Them

- **Builder**: Implements features AND writes tests
- **Tester**: Runs tests, manual testing, validation

This distinction ensures tests are written as part of implementation.

### 6. Approve Designs Before Implementation

When Architect proposes a design, review and approve it before Builder starts. This saves time.

### 7. Inspector for Reviews, Not Just Bugs

Use Inspector for:
- Security audits
- Consistency checks
- Finding missing documentation
- Pattern validation


---


## Troubleshooting (Quick Reference)

**s9 command not found or ModuleNotFoundError?**
```bash
# Reinstall with uv tool
uv tool uninstall site-nine
uv tool install --editable .
s9 --help  # Verify it works
```
**Why this happens**: Stale installations from when the module was named `s9` instead of `site_nine`.

**Alternative**: Use `uv run s9` to run from project virtual environment instead of global tool.

**Tests failing?**
```bash
make docker/up          # Start services first
make qa/test-integration
```

**Which agent to use?** → Ask `@manager`

**Command not working?** → Run `make help`

**Database connection error?** → Check `.env` configuration

**See**: `.opencode/docs/procedures/TROUBLESHOOTING.md` for comprehensive troubleshooting guide covering:
- Test failures and debugging
- Docker issues
- Configuration problems
- Database query issues
- Rate limiting
- External pythons
- Authentication tokens
- And more...


---


## Questions?

- **Development patterns**: See `.opencode/docs/guides/AGENTS.md`
- **Architecture**: See `.opencode/docs/guides/architecture.md`
- **Current status**: See `.opencode/work/planning/PROJECT_STATUS.md`
- **Session tracking**: See `.opencode/work/sessions/README.md`
- **Commands**: Run `make help`
- **Not sure which agent**: Start a session and choose a role
- **Commit format**: See `.opencode/docs/procedures/COMMIT_GUIDELINES.md`
- **Task workflow**: See `.opencode/docs/procedures/TASK_WORKFLOW.md`
- **Change history**: Run `s9 changelog`
- **Workflows**: See `.opencode/docs/procedures/WORKFLOWS.md`
- **Troubleshooting**: See `.opencode/docs/procedures/TROUBLESHOOTING.md`


---


**Remember**: This `.opencode/` configuration is for **developing** s9 (building the codebase), not for using s9 in your projects (end-user operation).

Happy building! 🚀
