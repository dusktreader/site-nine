<p align="center">
  <img src="docs/source/images/site-nine.png" alt="site-nine Logo" width="600">
</p>

<p align="center"><em>The headquarters for AI agent orchestration</em></p>

---

## Overview

**site-nine** is an orchestration framework designed to work with [OpenCode](https://github.com/khulnasoft/opencode) for AI-assisted software development. Work naturally with specialized AI agents through conversation, while site-nine handles project coordination behind the scenes.

site-nine provides:

- **Agent Session Management** - Track which AI agents are working on what, with specialized roles (Engineer, Tester, Architect, etc.)
- **Task Management System** - SQLite-based project management with priorities and dependencies
- **Daemon Naming System** - 145+ mythology-based names for agent instances
- **Multi-Agent Workflows** - Run multiple specialized agents in parallel OpenCode terminals
- **Dashboard** - Real-time project overview

## How It Works

1. Initialize site-nine in your project: `s9 init`
2. Summon a persona directly: `s9 summon operator` (or any role)
3. Talk to your agents naturally - they handle tasks, write code, run tests, and coordinate with each other
4. Run multiple agents in parallel terminals for complex workflows

## Requirements

- Python 3.12 or later
- [OpenCode](https://github.com/khulnasoft/opencode) - AI coding assistant
- Modern terminal with Unicode support (for rich output)

## Installation

```bash
pip install site-nine
```

Or with uv:

```bash
uv pip install site-nine
```

## Initialize a Project

In your project directory, run:

```bash
s9 init
```

This launches an interactive wizard that asks:

- **Project name** (defaults to directory name)
- **Project type** (python, typescript, go, rust, other)
- **Project description**
- **Features to enable** (task management, session tracking, etc.)
- **Agent roles to include**

After initialization, check that the `.opencode` directory was created:

```bash
ls .opencode/
# agents/  data/  guides/  planning/  procedures/  sessions/
```

## Next Steps

### Start Working with Agents

The Director (you) can summon agents in two ways:

#### Option 1: Direct Summon (Recommended)

Use the `s9 summon` command to launch OpenCode with an agent automatically:

```bash
s9 summon operator
```

This will start OpenCode and immediately initialize an agent session with the specified role.

#### Option 2: Manual Summon via OpenCode

Launch OpenCode manually and use the `/summon` slash command:

```bash
opencode
```

Then execute the summon command to start an agent session:

```
/summon
```

This will guide you through selecting an agent role (Engineer, Tester, Architect, etc.) and choosing a daemon name from mythology. Once summoned, the Director can talk to the agent naturally through conversation.

## Documentation

- [Quickstart Guide](https://dusktreader.github.io/site-nine/quickstart) - Get started in 5 minutes
- [Agent Roles](https://dusktreader.github.io/site-nine/roles) - Learn about specialized agent types
- [Advanced Topics](https://dusktreader.github.io/site-nine/advanced) - Multi-agent workflows and patterns
- [CLI Reference](https://dusktreader.github.io/site-nine/reference) - Complete command documentation
- [Full Documentation](https://dusktreader.github.io/site-nine)

## Contributing / Development

Want to contribute to site-nine or develop it locally? Here's how to get started.

### Development Setup

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

### Running Tests

```bash
# Start Docker services for testing
docker compose up -d

# Run all tests
make qa/test-all

# Run unit tests only
make qa/test

# Run integration tests
make qa/test-integration
```

### Development Commands

```bash
# Quality checks
make qa                      # Run all checks (test + lint + types)
make qa/format               # Format code
make qa/lint                 # Lint code

# Docker (advanced)
docker compose up -d         # Start services
docker compose down          # Stop services
docker compose logs -f       # View logs

# Help
make help                    # Show all available commands
```

### Technology Stack

- **Python 3.12+** with uv for package management
- **FastMCP** - Python framework
- **SQLAlchemy** - Database access (PostgreSQL, MySQL, SQLite)
- **DuckDB** - Knowledge base (embedded analytics)
- **pytest/pytest-bdd** - Testing
- **ruff** - Formatting and linting
- **basedpyright** - Type checking

### Project Structure

```
site-nine/
├── src/
│   └── site_nine/           # Main package
│       ├── cli/             # CLI commands
│       ├── core/            # Core framework
│       └── templates/       # Project templates
├── tests/                   # Unit tests
├── .opencode/               # OpenCode agent configuration
│   ├── docs/                # Agent instructions
│   ├── work/                # Session logs and tasks
│   ├── data/                # SQLite database
│   └── scripts/             # Utility scripts
├── .env.example             # Configuration template
├── Makefile                 # Development tasks
└── pyproject.toml           # Project config
```

### Agent Roles Overview

site-nine development uses 8 specialized agent roles for different types of work:

- **Administrator** - Primary interface and coordinator, delegates to specialized agents
- **Architect** - Design and planning specialist, creates technical designs
- **Engineer** - Implementation specialist, writes code and tests
- **Tester** - Quality assurance specialist, runs tests and validates features
- **Documentarian** - Documentation specialist, writes and maintains docs
- **Designer** - User experience specialist, designs CLI output and workflows
- **Inspector** - Code review specialist, reviews code and finds issues
- **Operator** - Meta-development specialist, maintains `.opencode/` infrastructure

For detailed role documentation, see [Agent Roles](https://dusktreader.github.io/site-nine/roles)

## License

MIT License - See LICENSE.md for details
