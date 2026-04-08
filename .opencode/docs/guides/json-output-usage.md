# JSON Output Usage for Agents

This guide explains when and how to use `--json` flags with s9 commands.

## Overview

All s9 commands support two output modes:
- **Table mode (default):** Pretty-printed tables for human consumption
- **JSON mode (`--json`):** Structured data for programmatic parsing

## General Rule

**Use `--json` when:**
- Agent needs to parse/consume the data programmatically
- Making decisions based on command output
- Extracting specific fields from results
- Integrating command output into workflows

**Use table mode (default) when:**
- Presenting data to the Director for review
- Showing status updates to humans
- Displaying results in skills for Director decision-making

## Examples

### ✅ Correct: Agent Consuming Data (Use --json)

**Discovery workflow:**
```bash
# Agent needs to check if Architect is available
possessions=$(s9 possession list --role Architect --epic EPC-H-0004 --json)

# Parse JSON to check minion_mode_active field
# Then make decision: send message or ask Director
```

**Auto-claiming next task:**
```bash
# Check if tasks are available before claiming
tasks=$(s9 task list --role Engineer --epic EPC-H-0005 --status TODO --json)

# Parse to see count, then proceed
if [ task_count > 0 ]; then
  s9 task next
fi
```

**Checking possession status:**
```bash
# Get structured data about current possession
possession_data=$(s9 possession show 124 --json)

# Extract specific fields for logic
epic_id=$(echo $possession_data | jq -r '.epic_id')
```

### ✅ Correct: Presenting to Director (Use table mode)

**Showing available tasks:**
```bash
# Director sees nicely formatted table
s9 task list --role Engineer --status TODO
```

**Displaying inbox:**
```bash
# Director sees formatted message summaries
s9 comms inbox
```

**Possession status report:**
```bash
# Director sees formatted possession details
s9 dashboard --role Architect
```

## Command Categories

### Discovery Commands (Use --json)

These are typically used by agents for coordination logic:

```bash
# Find available agents
s9 possession list --role <Role> --epic <EPIC-ID> --json

# Check for tasks programmatically
s9 task list --role <Role> --status TODO --json

# Get possession details for parsing
s9 possession show <possession-id> --json

# Check epic details
s9 epic show <EPIC-ID> --json
```

### Status/Reporting Commands (Use table mode by default)

These are typically for presenting to Director:

```bash
# Show inbox (human reads it)
s9 comms inbox

# Display dashboard
s9 dashboard
s9 dashboard --role <Role>

# List tasks for Director to review
s9 task list --status TODO

# Show possession status
s9 possession list
```

### Hybrid: Context Dependent

Some commands depend on context:

```bash
# FOR DIRECTOR (table mode):
s9 task show ENG-H-0037

# FOR AGENT LOGIC (--json):
s9 task show ENG-H-0037 --json
```

## Skills Documentation Pattern

When documenting workflows in skills, use this pattern:

**For agent consumption:**
```bash
# Check for available Architects on this epic
s9 possession list --role Architect --epic EPC-H-0004 --json
# Parse minion_mode_active field to find available agents
```

**For Director presentation:**
```bash
# Show current task status to Director
s9 task list --role Engineer --status TODO
```

**Make it clear why:**
```bash
# Agent parses JSON to make coordination decision
possessions=$(s9 possession list --role Architect --epic EPC-H-0004 --json)

# IF minion_mode_active == 1: send message
# ELSE: ask Director to summon agent
```

## Updating Existing Skills

When reviewing skills, check for these patterns:

### Pattern 1: Discovery Workflows

**Before:**
```bash
# Find agents working on epic
s9 possession list --role Architect --epic EPC-H-0004
```

**After:**
```bash
# Find agents working on epic (parse for minion_mode_active)
s9 possession list --role Architect --epic EPC-H-0004 --json
```

### Pattern 2: Auto-Claiming Tasks

**Before:**
```bash
# Query for next task
s9 task list --role Engineer --status TODO
```

**After (if agent will parse it):**
```bash
# Query for next task to auto-claim
s9 task list --role Engineer --status TODO --json
```

**Or keep table mode if just showing to Director:**
```bash
# Show available tasks to Director for selection
s9 task list --role Engineer --status TODO
```

### Pattern 3: Decision-Making

**Before:**
```bash
# Check task status
s9 task show ENG-H-0037
```

**After (if agent parses it):**
```bash
# Check task status for automated handling
s9 task show ENG-H-0037 --json
# Parse status field to determine next action
```

## JSON Structure Examples

Understanding the JSON structure helps agents parse correctly:

### Possession List JSON
```json
{
  "possessions": [
    {
      "id": 62,
      "daemon": "daedalus",
      "role": "Architect",
      "status": "ACTIVE",
      "minion_mode_active": 1,
      "epic_id": "EPC-H-0004",
      "codename": "swift-forge"
    }
  ]
}
```

**Useful fields for agents:**
- `minion_mode_active`: Is agent available for messages? (0 or 1)
- `epic_id`: What epic is agent working on?
- `id`: Possession ID for sending messages

### Task List JSON
```json
{
  "tasks": [
    {
      "id": "ENG-H-0037",
      "title": "Implement ToolRegistry",
      "status": "TODO",
      "priority": "HIGH",
      "role": "Engineer",
      "epic_id": "EPC-H-0004",
      "possession_id": null
    }
  ]
}
```

**Useful fields for agents:**
- `status`: Is task available to claim?
- `possession_id`: Is task already claimed?
- `priority`: For prioritization logic
- `epic_id`: Match with possession epic

### Task Show JSON
```json
{
  "id": "ENG-H-0037",
  "title": "Implement ToolRegistry",
  "status": "TODO",
  "priority": "HIGH",
  "role": "Engineer",
  "epic_id": "EPC-H-0004",
  "description": "...",
  "acceptance_criteria": "..."
}
```

## Parsing JSON with jq

Agents can use `jq` for parsing JSON output:

```bash
# Get all possession IDs with minion mode active
s9 possession list --role Architect --epic EPC-H-0004 --json | \
  jq -r '.possessions[] | select(.minion_mode_active == 1) | .id'

# Count TODO tasks
s9 task list --status TODO --role Engineer --json | \
  jq '.tasks | length'

# Extract epic_id from possession
s9 possession show 124 --json | jq -r '.epic_id'

# Get all task IDs with HIGH priority
s9 task list --priority HIGH --status TODO --json | \
  jq -r '.tasks[].id'
```

## Best Practices

1. **Document intent** - Explain WHY you're using --json in comments
2. **Parse safely** - Check for null/empty results before using data
3. **Show to Director** - When presenting results, use table mode
4. **Test both modes** - Verify commands work in both JSON and table mode
5. **Update skills** - Document --json usage when agents consume data

## See Also

- **Agent Discovery Guide**: `agent-discovery.md` for discovery workflow examples
- **Epic Possessions Guide**: `epic-possessions-and-minion-mode.md` for coordination patterns
- **ADR-008** (lines 985-999): JSON output flag design rationale
- **Task OPR-M-0074**: Implementation of --json flags across all s9 commands
