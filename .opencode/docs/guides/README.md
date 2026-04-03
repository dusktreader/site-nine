# Development Guides

Reference guides for s9-powered projects.


## Quick Start

**New to s9?** Start here:

1. [tasks.md](./tasks.md) - Task system
2. [markdown-style.md](./markdown-style.md) - Markdown standards (required)
3. [commit-guidelines.md](./commit-guidelines.md) - Commit format

## Task Management

### [tasks.md](./tasks.md)

Task management system: ID format, status values, priority levels, workflows.


### [task-sizing.md](./task-sizing.md)

Task complexity estimation: sizing categories (XS-XL), estimation techniques.


## Development Workflow

### [commit-guidelines.md](./commit-guidelines.md)

Commit format: `type(scope): description [Agent: Role - Name]`


### [testing.md](./testing.md)

Testing patterns: AAA pattern, fixtures, mocking, coverage requirements.


### [code-review.md](./code-review.md)

Code review checklist and feedback guidelines.


### [adr-workflow.md](./adr-workflow.md)

Architecture decision documentation: when to create, format, review process.


### [troubleshooting.md](./troubleshooting.md)

Common development issues: environment setup, test failures, database issues.


## Agent Coordination

### [agent-discovery.md](./agent-discovery.md)

Agent discovery patterns: finding available agents, using `--json` flags, desk mode status, messaging vs. asking
Director.


### [epic-possessions-and-desk-mode.md](./epic-possessions-and-desk-mode.md)

Epic possession workflows: starting possessions with `--epic`, using `s9 task next`, desk mode usage, periodic
status checks, responding to messages.


### [json-output-usage.md](./json-output-usage.md)

JSON output guidelines: when to use `--json` vs. table mode, parsing patterns, command examples, jq usage.


### [desk-mode-orchestration.md](./desk-mode-orchestration.md)

Desk mode orchestration reference for Admin agents: spawning background workers, sending work via messages,
monitoring worker status, coordination patterns, termination procedures.


### [admin-orchestration.md](./admin-orchestration.md)

Practical Admin orchestration guide: breaking down Director goals, assigning work with context, sequential and
parallel workflow patterns, handling worker problems, and reporting back to Director.


## Architecture & Design

### [architecture.md](./architecture.md)

System architecture overview: layers, core components, database, task management, possession system, agent
coordination, adapter pattern design.


### [tool-adapters.md](./tool-adapters.md)

Tool adapter system guide: what adapters are, how detection works, using adapters, implementing new adapters,
configuration mapping, environment variable overrides.


## Documentation Standards

### [markdown-style.md](./markdown-style.md) ⚠️ **REQUIRED**

Markdown formatting rules: 120-char line wrap, ATX headings, title case, blank line spacing.

**All agents must follow these standards when editing markdown files.**


## Quick Reference by Task

| What You're Doing                   | Read This                                                     |
|-------------------------------------|---------------------------------------------------------------|
| Working with tasks                  | tasks.md                                                      |
| Estimating task size                | task-sizing.md                                                |
| Making a commit                     | commit-guidelines.md                                          |
| Writing tests                       | testing.md                                                    |
| Reviewing code                      | code-review.md                                                |
| Documenting a design choice         | adr-workflow.md                                               |
| Editing any markdown file           | markdown-style.md                                             |
| Fixing an issue                     | troubleshooting.md                                            |
| Finding other agents to coordinate  | agent-discovery.md                                            |
| Working on epic-scoped possessions  | epic-possessions-and-desk-mode.md                             |
| Using --json vs table output        | json-output-usage.md                                          |
| Orchestrating background workers    | desk-mode-orchestration.md, admin-orchestration.md            |
| Understanding system architecture   | architecture.md                                               |
| Working with tool adapters          | tool-adapters.md                                              |
| Learning site-nine's code patterns  | [site-nine-dev/coding-patterns.md](../../site-nine-dev/coding-patterns.md) |


## Related Documentation

- **Agent Roles:** [`.opencode/docs/roles/`](../roles/) - Role definitions and responsibilities
- **Project Overview:** [`.opencode/README.md`](../../README.md) - Entry point for agents on this project
