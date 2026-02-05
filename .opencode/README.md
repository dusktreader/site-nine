# OpenCode Configuration for site-nine Development

This directory contains OpenCode configuration for **developing** the site-nine Python project.

> **Important:** This is configuration for developing site-nine itself, not for using site-nine in your projects.

## For OpenCode Agents

**To start a development session:**

Use the `/summon` command to initialize a session. The session-start skill will guide you through:

1. Role selection (Administrator, Architect, Engineer, Tester, Documentarian, Designer, Inspector, Operator)
2. Persona naming
3. Reading required documentation

**Essential documentation will be read during session start:**
- `.opencode/docs/guides/AGENTS.md` - Complete development guide
- `.opencode/docs/development/SITE_NINE_DEV.md` - Site-nine specific patterns
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
├── data/                 # SQLite database
└── work/                 # Session logs, tasks, planning
```

## For Humans

See the main project README: `../README.md`
