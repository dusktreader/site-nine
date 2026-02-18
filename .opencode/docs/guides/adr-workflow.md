# Architecture Decision Records (ADRs) Workflow

Database-backed ADR system for tracking architectural decisions and linking them to epics/tasks.


## Overview

ADRs document important architectural decisions. Site-nine stores ADRs in the database with markdown files for
presentation, providing bidirectional linking to epics/tasks for traceability.


## ADR Lifecycle

- **PROPOSED**: Initial state
- **ACCEPTED**: Decision approved for implementation
- **REJECTED**: Decision considered but declined
- **SUPERSEDED**: Replaced by newer ADR
- **DEPRECATED**: No longer recommended


## Basic Commands

### Create ADR

```bash
s9 adr create --title "My Architecture Decision" --status PROPOSED
```

Creates database entry (ADR-001, ADR-002...) and markdown file in `.opencode/docs/adrs/`.


### List ADRs

```bash
s9 adr list                    # All ADRs
s9 adr list --status ACCEPTED  # Filter by status
```


### Show Details

```bash
s9 adr show ADR-001  # Shows metadata, linked epics/tasks
```


### Update Metadata

```bash
s9 adr update ADR-001 --title "New Title"
s9 adr update ADR-001 --status ACCEPTED
s9 adr update ADR-001 --title "New Title" --status ACCEPTED
```


### Sync from Filesystem

```bash
s9 adr sync  # Import/update ADRs from .opencode/docs/adrs/
```


## Linking ADRs

### Epic Links

```bash
s9 epic link-adr EPC-H-0001 ADR-001    # Link
s9 epic sync --epic EPC-H-0001          # Update epic file
s9 epic unlink-adr EPC-H-0001 ADR-001  # Unlink
```


### Task Links

```bash
s9 task link-adr OPR-H-0063 ADR-006    # Link
s9 task sync --task OPR-H-0063          # Update task file
s9 task unlink-adr OPR-H-0063 ADR-006  # Unlink
```


## Workflow Examples

### Creating New ADR

```bash
s9 adr create --title "Use Adapter Pattern for Tool Abstraction"
# Edit markdown file with decision details
s9 epic link-adr EPC-H-0004 ADR-007
s9 epic sync --epic EPC-H-0004
s9 adr update ADR-007 --status ACCEPTED
```


### Linking During Implementation

```bash
s9 task link-adr OPR-H-0065 ADR-001
s9 task sync --task OPR-H-0065
```


### Finding Related Work

```bash
s9 adr show ADR-001  # Shows linked epics and tasks
```


### Superseding ADR

```bash
s9 adr create --title "Revised Adapter Pattern with MCP Support"
s9 adr update ADR-001 --status SUPERSEDED
# Reference old ADR in new ADR markdown
```


## ADR Markdown Template

Created ADRs use this template structure:

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
| Risk        | Mitigation     |
|-------------|----------------|
| [Risk 1]    | [Mitigation 1] |

## References
- [Related documents, tasks, or external resources]

## Notes
[Additional notes or context]
```


## Best Practices

- **Create ADRs early**: Document decisions as they're made
- **Link liberally**: Connect ADRs to relevant epics/tasks for traceability
- **Update status**: Keep ADR status current
- **Sync regularly**: Run sync commands after linking ADRs
- **Reference in code**: Add comments referencing ADR IDs
- **Review pending**: Use `s9 adr list --status PROPOSED` to review open decisions


## Troubleshooting

**ADR not in epic/task file**: Ensure linking (`s9 epic link-adr` / `s9 task link-adr`) and sync (`s9 epic sync` /
`s9 task sync`).

**ADR missing from database**: Run `s9 adr sync` to import from filesystem.

**Can't find ADR**: Use `s9 adr list` or `s9 adr list --status ACCEPTED`.


## Command Reference

```bash
# ADR management
s9 adr create       # Create new ADR
s9 adr list         # List ADRs (use --status to filter)
s9 adr show         # Show ADR details and links
s9 adr update       # Update metadata
s9 adr sync         # Import from filesystem

# Epic linking
s9 epic link-adr    # Link ADR to epic
s9 epic unlink-adr  # Unlink ADR from epic
s9 epic sync        # Sync epic file

# Task linking
s9 task link-adr    # Link ADR to task
s9 task unlink-adr  # Unlink ADR from task
s9 task sync        # Sync task file
```
