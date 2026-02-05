# Architecture Decision Records (ADRs) Workflow

This guide explains how to work with Architecture Decision Records (ADRs) in site-nine using the database-backed ADR tracking system.

## Overview

ADRs are documents that capture important architectural decisions made during development. Site-nine provides a database-backed system for managing ADRs and linking them to epics and tasks, ensuring traceability between decisions and implementation work.

### Key Features

- **Database-backed**: ADRs are stored in the project database with markdown files as the presentation layer
- **Bidirectional linking**: Link ADRs to epics and tasks to show which decisions informed which work
- **Status tracking**: Track ADR lifecycle from PROPOSED through ACCEPTED/REJECTED to SUPERSEDED/DEPRECATED
- **Automatic sync**: ADR information automatically appears in epic and task markdown files
- **CLI management**: Full CLI support for creating, listing, updating, and linking ADRs

## ADR Lifecycle

ADRs can have the following statuses:

- **PROPOSED**: Initial state when ADR is created
- **ACCEPTED**: Decision has been accepted and will be implemented
- **REJECTED**: Decision was considered but rejected
- **SUPERSEDED**: Decision was accepted but has been replaced by a newer ADR
- **DEPRECATED**: Decision is no longer recommended but not formally superseded

## Basic Commands

### Create a new ADR

```bash
s9 adr create --title "My Architecture Decision" --status PROPOSED
```

This creates:
- A new database entry with auto-incremented ID (ADR-001, ADR-002, etc.)
- A markdown file in `.opencode/docs/adrs/` with a template structure

### List all ADRs

```bash
# List all ADRs
s9 adr list

# Filter by status
s9 adr list --status ACCEPTED
```

### Show ADR details

```bash
s9 adr show ADR-001
```

This displays:
- ADR metadata (title, status, file path, timestamps)
- Linked epics
- Linked tasks

### Update ADR metadata

```bash
# Update title
s9 adr update ADR-001 --title "New Title"

# Update status
s9 adr update ADR-001 --status ACCEPTED

# Update both
s9 adr update ADR-001 --title "New Title" --status ACCEPTED
```

### Sync ADRs from filesystem

If you manually create or edit ADR markdown files, sync them to the database:

```bash
s9 adr sync
```

This command:
- Scans `.opencode/docs/adrs/` for ADR markdown files
- Imports new ADRs into the database
- Updates existing ADRs if title or status changed
- Reports import/update/skip counts

## Linking ADRs to Epics and Tasks

### Link ADR to Epic

```bash
s9 epic link-adr EPC-H-0001 ADR-001
```

After linking, sync the epic to update its markdown file:

```bash
s9 epic sync --epic EPC-H-0001
```

The epic file will include a "Related Architecture" section with a table showing:
- ADR ID
- Title
- Status
- File path

### Unlink ADR from Epic

```bash
s9 epic unlink-adr EPC-H-0001 ADR-001
```

### Link ADR to Task

```bash
s9 task link-adr OPR-H-0063 ADR-006
```

After linking, sync the task to update its markdown file:

```bash
s9 task sync --task OPR-H-0063
```

The task file will include a "Related Architecture" section showing linked ADRs with markdown links.

### Unlink ADR from Task

```bash
s9 task unlink-adr OPR-H-0063 ADR-006
```

## Workflow Examples

### Creating a new ADR for a design decision

```bash
# 1. Create the ADR
s9 adr create --title "Use Adapter Pattern for Tool Abstraction"

# This creates ADR-007 (for example)

# 2. Edit the markdown file with your decision details
vim .opencode/docs/adrs/ADR-007-use-adapter-pattern-for-tool-abstraction.md

# 3. Link to related epic
s9 epic link-adr EPC-H-0004 ADR-007

# 4. Sync epic to show the link
s9 epic sync --epic EPC-H-0004

# 5. Later, accept the decision
s9 adr update ADR-007 --status ACCEPTED
```

### Linking existing ADRs to tasks during implementation

```bash
# You're working on task OPR-H-0065 which implements ADR-001
s9 task link-adr OPR-H-0065 ADR-001

# Sync to update task markdown
s9 task sync --task OPR-H-0065

# Now the task file shows which ADR informed this work
```

### Finding all work related to an ADR

```bash
# Show which epics and tasks are linked to an ADR
s9 adr show ADR-001

# Output:
# ADR ADR-001
#   Title: Adapter Pattern for Tool Abstraction
#   Status: ACCEPTED
#   File: .opencode/docs/adrs/ADR-001-adapter-pattern-abstraction.md
#   Created: 2026-02-04 17:47:27
#   Updated: 2026-02-04 17:47:27
#
#   Linked Epics: EPC-H-0004
#   Linked Tasks: OPR-H-0065, OPR-H-0066, OPR-H-0067
```

### Superseding an ADR

```bash
# Create new ADR that supersedes old one
s9 adr create --title "Revised Adapter Pattern with MCP Support"

# Mark old ADR as superseded
s9 adr update ADR-001 --status SUPERSEDED

# In the new ADR markdown, reference the old one in the context section
```

## ADR Markdown Template

When you create an ADR, a template is generated with these sections:

```markdown
# ADR-XXX: Title

**Status:** PROPOSED
**Date:** YYYY-MM-DD
**Deciders:** [To be filled]
**Related Tasks:** [To be filled]

## Context
[Describe the issue that motivates this decision]

## Decision
[Describe the decision and how it addresses the issue]

## Alternatives Considered

### Alternative 1: [Name]
**Approach:** [Description]
**Pros:** [...]
**Cons:** [...]
**Rejected because:** [Reason]

## Consequences

### Positive
- ✅ [Benefit 1]

### Negative
- ⚠️ [Trade-off 1]

### Risks & Mitigation
| Risk | Mitigation |
|------|-----------|
| [Risk 1] | [Mitigation 1] |

## References
- [Related documents, tasks, or external resources]

## Notes
[Additional notes or context]
```

## Database Schema

ADRs are stored in three tables:

1. **architecture_docs**: Main ADR data (id, title, status, file_path, timestamps)
2. **epic_architecture_docs**: Links between epics and ADRs (epic_id, adr_id)
3. **task_architecture_docs**: Links between tasks and ADRs (task_id, adr_id)

The database is the source of truth. Markdown files are synchronized from the database during epic/task sync operations.

## Best Practices

1. **Create ADRs early**: Document decisions as they're being made, not after
2. **Link liberally**: Connect ADRs to all relevant epics and tasks for traceability
3. **Update status**: Keep ADR status current as decisions are accepted/rejected
4. **Sync regularly**: Run `s9 epic sync` and `s9 task sync` after linking ADRs
5. **Reference in code**: Add comments in code referencing relevant ADR IDs
6. **Review periodically**: Use `s9 adr list --status PROPOSED` to review pending decisions

## Integration with Workflows

### Epic Planning
When creating a new epic that requires architectural decisions:
1. Create ADRs for key decisions
2. Link ADRs to the epic using `s9 epic link-adr`
3. Sync epic to show architecture in the epic file
4. Create tasks that implement the ADRs
5. Link ADRs to implementation tasks

### Task Implementation
When working on a task that implements an ADR:
1. Link the ADR to the task using `s9 task link-adr`
2. Sync task to show the ADR in the task header
3. Reference ADR decisions in code comments and commit messages
4. Update ADR status to ACCEPTED once implemented

### Code Reviews
When reviewing code:
1. Check if task has linked ADRs using `s9 task show TASK-ID`
2. Verify implementation matches ADR decisions
3. Suggest ADR links if architectural decisions aren't documented

## Troubleshooting

### ADR not showing in epic/task file
- Make sure you've linked the ADR: `s9 epic link-adr` or `s9 task link-adr`
- Run sync command: `s9 epic sync` or `s9 task sync`

### ADR missing from database
- Run `s9 adr sync` to import ADRs from filesystem

### Can't find an ADR
- Use `s9 adr list` to see all ADRs
- Filter by status: `s9 adr list --status ACCEPTED`
- Search markdown files directly: `grep -r "search term" .opencode/docs/adrs/`

## Related Commands

```bash
# ADR commands
s9 adr create       # Create new ADR
s9 adr list         # List all ADRs
s9 adr show         # Show ADR details and links
s9 adr update       # Update ADR metadata
s9 adr sync         # Import ADRs from filesystem

# Epic ADR linking
s9 epic link-adr    # Link ADR to epic
s9 epic unlink-adr  # Unlink ADR from epic
s9 epic sync        # Sync epic file (includes ADRs)

# Task ADR linking
s9 task link-adr    # Link ADR to task
s9 task unlink-adr  # Unlink ADR from task
s9 task sync        # Sync task file (includes ADRs)
```

## Further Reading

- [ADR Template Format](../adrs/ADR-001-adapter-pattern-abstraction.md) - Example ADR structure
- [Architecture Guide](./architecture.md) - Overall architecture documentation
- [Design Philosophy](./design-philosophy.md) - Project design principles
