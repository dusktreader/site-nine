# OpenCode Configuration

This directory contains OpenCode configuration for AI-assisted development.

> **Note:** Site-nine specific development files are in the `site-nine-dev/` subdirectory.

## For OpenCode Agents

**To start a development session:**

Use the `/summon` command to initialize a session. The session-start skill will guide you through:

1. Role selection (Administrator, Architect, Engineer, Tester, Documentarian, Designer, Inspector, Operator)
2. Persona naming
3. Reading required documentation

**Essential documentation will be read during session start:**
- `.opencode/docs/guides/AGENTS.md` - Complete development guide
- `.opencode/site-nine-dev/development/SITE_NINE_DEV.md` - Site-nine specific patterns
- `.opencode/docs/procedures/COMMIT_GUIDELINES.md` - Commit format

## Directory Structure

```
.opencode/
├── commands/              # Slash commands (auto-discovered)
├── skills/                # Reusable workflows (auto-discovered)
├── docs/
│   ├── guides/           # Development guides (AGENTS.md is primary)
│   ├── roles/            # Role-specific documentation
│   ├── procedures/       # How-tos and workflows
│   └── adrs/            # Architecture decision records
├── site-nine-dev/        # Site-nine specific development files
├── data/                 # SQLite database
└── work/                 # Session logs, tasks, planning
```

## For Humans

See the main project README: `../README.md`
