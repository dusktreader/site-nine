# CLI Overview

The `s9` command-line tool is the primary interface for interacting with site-nine. It provides commands for managing missions, tasks, epics, reviews, and more.

## Installation

If you have site-nine installed, the `s9` command should be available in your PATH:

```bash
s9 --version
```

## Getting Help

```bash
s9 --help              # Show all available commands
s9 <command> --help    # Show help for a specific command
```

## Command Audience Guide

The s9 CLI is designed to serve two primary audiences:

- **Human developers** use s9 for project oversight, planning, and coordination (creating tasks, reviewing work, managing epics, viewing dashboards)
- **AI agents** use s9 for automated workflows (starting missions, claiming tasks, creating handoffs, updating status)

Some commands are useful to both audiences (like viewing task details or listing missions), while others are optimized for one or the other.

### Where to Go Next

- **[For Humans →](for-humans.md)** - Common workflows for project management and oversight
- **[For Agents →](for-agents.md)** - Integration patterns for automated agent workflows  
- **[Complete Reference →](complete.md)** - Full alphabetical command documentation

Each command's help text includes a "typically used by" indicator to help you understand its primary audience.
