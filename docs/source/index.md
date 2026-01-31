![site-nine Logo](images/site-nine.png){ .s9-logo }

<p style="text-align: center; font-style: italic; margin-top: -1em; margin-bottom: 2em;">The headquarters for AI agent orchestration</p>

## Overview

**site-nine** is an orchestration framework designed to work with [OpenCode](https://github.com/khulnasoft/opencode) for AI-assisted software development. Work naturally with specialized AI agents through conversation, while site-nine handles project coordination behind the scenes.

site-nine provides:

- **Agent Session Management** - Track which AI agents are working on what, with specialized roles (Builder, Tester, Architect, etc.)
- **Task Management System** - SQLite-based project management with priorities and dependencies
- **Daemon Naming System** - 145+ mythology-based names for agent instances
- **Multi-Agent Workflows** - Run multiple specialized agents in parallel OpenCode terminals
- **Dashboard** - Real-time project overview

## How It Works

1. Initialize site-nine in your project: `s9 init`
2. Launch OpenCode and summon an agent: `opencode` → `/summon`
3. Talk to your agents naturally - they handle tasks, write code, run tests, and coordinate with each other
4. Run multiple agents in parallel terminals for complex workflows

## Quick Links

- [Quickstart Guide](quickstart.md) - Get started in 5 minutes
- [Agent Roles](roles.md) - Learn about specialized agent types
- [Advanced Topics](advanced.md) - Multi-agent workflows and patterns
- [CLI Reference](reference.md) - Complete command documentation
- [GitHub Repository](https://github.com/dusktreader/site-nine)

## Requirements

- Python 3.12 or later
- [OpenCode](https://github.com/khulnasoft/opencode) - AI coding assistant
- Modern terminal with Unicode support (for rich output)

## License

MIT License - See LICENSE.md for details