<p align="center">
  <img src="docs/source/images/site-nine.png" alt="site-nine Logo" width="600">
</p>

<p align="center"><em>The headquarters for AI agent orchestration</em></p>

---

site-nine is an orchestration framework designed to work with [OpenCode](https://github.com/khulnasoft/opencode) for AI-assisted software development. It bootstraps `.opencode` project structures with agent roles, task management, and development workflows.

## Features

- **Agent Roles**: 8 specialized agent personas (Administrator, Architect, Builder, Tester, Documentarian, Designer, Inspector, Operator)
- **Task Management**: SQLite-based PM system with daemon name tracking
- **Session Tracking**: Track which agents worked on what and when
- **Commit Guidelines**: Standardized commit format with agent attribution
- **Templates**: Jinja2-based customizable templates for all project files

## Installation

```bash
pip install site-nine
```

## Quick Start

```bash
# Initialize a new project
cd /path/to/your-project
s9 init

# Answer interactive prompts to customize your setup
# Result: .opencode/ directory with complete orchestration structure
```

## CLI Commands

```bash
s9 init [--config FILE]          # Initialize .opencode structure
s9 agent start/end/list/show     # Manage agent sessions
s9 task list/claim/update/close  # Manage tasks
s9 template list/show            # View templates
s9 dashboard                     # Project overview
s9 changelog                     # Generate changelog
s9 doctor                        # Health checks
```

## Documentation

See [documentation](https://dusktreader.github.io/site-nine) for detailed usage guide.

## License

MIT License - see LICENSE.md
