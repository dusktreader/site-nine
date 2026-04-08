# CLI Commands for Humans

This page covers the most common commands used by human developers for project management and oversight.

## Getting Started

### Initialize a New Project

```bash
s9 init
```

This interactive wizard will:
- Create the `.opencode/` directory structure
- Initialize the SQLite database
- Populate daemon names
- Render templates and configuration files

### View Project Status

```bash
s9 dashboard
```

Shows an overview including:
- Active possessions and daemons
- Task summary by status
- Epic progress
- Recent activity

Filter by role or epic:

```bash
s9 dashboard --role Operator
s9 dashboard --epic EPC-H-0001
```

## Task Management

### Create Tasks

```bash
s9 task create \
  --role Operator \
  --priority HIGH \
  --title "Implement rate limiting" \
  --description "Add rate limiting to API endpoints"
```

### List Tasks

```bash
s9 task list                    # All tasks
s9 task list --role Operator    # Filter by role
s9 task list --status TODO      # Filter by status
```

### Search Tasks

```bash
s9 task search "rate limiting"
```

### Get Task Suggestions

```bash
s9 task next                    # Suggest next tasks to work on
s9 task next --role Operator    # Suggest for specific role
```

### Generate Reports

```bash
s9 task report                  # Summary report of all tasks
```

## Possession Management

### List Possessions

```bash
s9 possession list                 # All possessions
s9 possession list --active-only   # Only active possessions
s9 possession list --role Operator # Filter by role
```

### View Possession Details

```bash
s9 possession show 42
```

### Generate Possession Summary

```bash
s9 possession summary 42
```

Shows:
- Files changed since possession start
- Commits made (filtered by daemon)
- Tasks claimed and their status

### List OpenCode Sessions

```bash
s9 possession list-opencode-sessions
```

Helpful for finding active OpenCode sessions for this project.

## Review Management

### List Reviews

```bash
s9 review list                  # All reviews
s9 review list --status pending # Only pending reviews
```

### View Review Details

```bash
s9 review show 5
```

### Approve or Reject Reviews

```bash
s9 review approve 5
s9 review reject 5 --reason "Needs more test coverage"
```

### Show Blocked Tasks

```bash
s9 review blocked
```

Shows all tasks that are blocked by pending reviews.

## Epic Management

### Create an Epic

```bash
s9 epic create \
  --title "User Authentication System" \
  --priority HIGH \
  --description "Complete authentication implementation"
```

### List Epics

```bash
s9 epic list
s9 epic list --status UNDERWAY
```

### View Epic Details

```bash
s9 epic show EPC-H-0001
```

### Abort an Epic

```bash
s9 epic abort EPC-H-0001
```

This will abort the epic and all its linked tasks.

## Architecture Decisions (ADRs)

### Create an ADR

```bash
s9 adr create \
  --title "Use PostgreSQL for production database" \
  --status accepted
```

### List ADRs

```bash
s9 adr list
s9 adr list --status accepted
```

### View ADR Details

```bash
s9 adr show 3
```

## Release Management

## Utilities

### Health Checks

```bash
s9 doctor
```

Runs infrastructure health checks and validates data integrity.

### Launch Agent

```bash
s9 summon operator              # Launch OpenCode with Operator role
s9 summon operator --auto-assign # Auto-assign top priority task
```

### Reset Project (Dangerous!)

```bash
s9 reset
```

Resets all project data. Use with extreme caution!

## JSON Output

Most commands support `--json` output for scripting:

```bash
s9 task list --json
s9 possession list --json
s9 dashboard --json
```

## Next Steps

- See [CLI Overview](overview.md) for command categorization
- See [Complete Reference](complete.md) for detailed command documentation
