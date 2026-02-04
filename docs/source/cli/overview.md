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

The s9 CLI is designed to be used by both **AI agents** and **human developers**. Commands are categorized to help you understand their primary use case:

### Commands for Human Management

These commands are primarily used by human developers for project oversight, planning, and coordination.

**Project Overview:**

```bash
s9 init                       # Initialize project structure
s9 dashboard                  # View project overview with tasks and missions
s9 doctor                     # Run health checks and validate data integrity
s9 reset                      # Reset project data (dangerous!)
```

**Task Planning:**

```bash
s9 task create                # Create new tasks
s9 task report                # Generate task summary reports
s9 task next                  # Get task suggestions
```

**Mission Management:**

```bash
s9 mission list               # List all missions
s9 mission summary            # Generate mission summaries
s9 mission list-opencode-sessions  # List OpenCode TUI sessions
```

**Reviews & Approvals:**

```bash
s9 review list                # List review requests
s9 review approve             # Approve a review
s9 review reject              # Reject a review
s9 review blocked             # Show tasks blocked by reviews
```

**Epic Management:**

```bash
s9 epic create                # Create new epics
s9 epic list                  # List all epics
s9 epic abort                 # Abort an epic and its tasks
```

**Architecture Decisions:**

```bash
s9 adr create                 # Create Architecture Decision Records
s9 adr list                   # List ADRs
```

**Release Management:**

```bash
s9 changelog                  # Generate changelogs from completed tasks
```

**Utilities:**

```bash
s9 summon                     # Launch OpenCode with agent initialization
```

### Commands for Agent Workflows

These commands are primarily used by AI agents during automated workflows, particularly during mission initialization and task execution.

**Mission Management:**

```bash
s9 mission start              # Register a new mission with persona and role
s9 mission generate-session-uuid  # Generate UUID for session detection
s9 mission rename-tui         # Rename OpenCode TUI session
s9 mission update             # Update mission metadata
s9 mission roles              # Display available agent roles
```

**Task Execution:**

```bash
s9 task claim                 # Claim a task for the active mission
s9 task update                # Update task status during execution
s9 task close                 # Close a completed task
```

**Collaboration:**

```bash
s9 handoff create             # Create a handoff to another role
s9 handoff accept             # Accept a pending handoff
s9 handoff complete           # Complete a handoff
```

**Reviews:**

```bash
s9 review create              # Create a review request
```

**Personas:**

```bash
s9 name suggest               # Get persona name suggestions
s9 name set-bio               # Set persona biography
```

### Shared Commands (Used by Both)

These commands are useful for both agents and humans.

**Information & Inspection:**

```bash
s9 mission show               # Show mission details
s9 mission end                # End a mission
s9 task show                  # Show task details
s9 task list                  # List tasks with filters
s9 task search                # Search tasks by keyword
s9 task mine                  # Show tasks claimed by a mission
s9 handoff list               # List handoffs
s9 handoff show               # Show handoff details
s9 review show                # Show review details
s9 name list                  # List persona names
s9 name show                  # Show persona details
s9 epic show                  # Show epic details
s9 adr show                   # Show ADR details
```

## Next Steps

- See [For Humans](for-humans.md) for detailed human-focused workflows
- See [For Agents](for-agents.md) for agent integration patterns
- See [Complete Reference](complete.md) for full command documentation
