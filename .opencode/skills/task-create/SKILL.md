---
name: task-create
description: Create new tasks in the s9 task database with proper formatting and validation
license: MIT
compatibility: opencode
metadata:
  audience: all-agents
  workflow: task-creation
---

## What I Do

I provide comprehensive instructions for creating new tasks in the s9 task database using the `task_create` tool. Use this skill when you need to add new work items to the project.

## Tool Overview

This skill uses the **`task_create` tool**, which:
- Creates tasks in the s9 database
- Auto-generates task IDs based on role and priority
- Returns clean JSON results
- Automatically receives possession context from OpenCode

## When to Create Tasks

- **Administrator** role adding new work items
- **Inspector** creating follow-up tasks from reviews
- **Architect** creating implementation tasks from design
- Breaking down epics into smaller tasks
- Creating tasks for bugs or technical debt

## Tool Syntax

```python
task_create(
    title="Brief task title",
    role="Administrator|Architect|Engineer|Tester|Documentarian|Designer|Inspector|Operator|Historian",
    priority="CRITICAL|HIGH|MEDIUM|LOW",
    category="Category name",  # Optional
    description="Detailed description of what needs to be done and why",  # Optional
    epic="Epic ID to link this task to"  # Optional
)
```

**Note:** Task IDs are **auto-generated** based on role and priority. You do not need to provide a task ID.

**Session Context:** Possession ID and role are automatically provided by OpenCode's session context - you don't need to specify them.

## Task ID Format

**Task IDs are auto-generated** using the format: `PREFIX-PRIORITY-NUMBER`

- **PREFIX**: 3-letter role code (e.g., OPR for Operator, ENG for Engineer)
- **PRIORITY**: Single letter (C=Critical, H=High, M=Medium, L=Low)
- **NUMBER**: 4-digit global sequential counter (0001-9999)

### Role Prefixes

- `ADM` - Administrator
- `ARC` - Architect  
- `ENG` - Engineer
- `TST` - Tester
- `DOC` - Documentarian
- `DES` - Designer
- `INS` - Inspector
- `OPR` - Operator
- `HIS` - Historian


### Examples

- `OPR-H-0001` - First high-priority Operator task
- `ENG-C-0005` - Critical Engineer task (fifth task overall)
- `DOC-M-0042` - Medium-priority Documentarian task (42nd task overall)

The number increments globally across all roles and priorities, ensuring each task has a unique ID.

## Priority Guidelines

### CRITICAL - Immediate action required
- Security vulnerabilities
- Data corruption risks
- Blocking all other work
- Production outages

### HIGH - Important, do soon
- Key features for current milestone
- P1 bugs affecting users
- Technical debt causing problems
- Required for next phase

### MEDIUM - Nice to have
- Enhancement requests
- Minor features
- Code quality improvements
- Non-urgent bugs

### LOW - Do when time permits
- Polish and refinement
- Documentation updates
- Minor improvements
- Nice-to-have features

## Role Assignment

Assign to the role that will do most of the work:

- **Administrator** - Planning, coordination, prioritization
- **Architect** - System design, ADRs, technical direction
- **Engineer** - Implementation, coding, integration
- **Tester** - Test writing, validation, QA
- **Documentarian** - Documentation, guides, examples
- **Designer** - UI/UX, visual design
- **Inspector** - Security review, code review, audits
- **Operator** - Deployment, infrastructure, monitoring
- **Historian** - Recording decisions, maintaining history

## Category Examples

Common categories:
- `Architecture` - System design work
- `Testing` - Test creation and QA
- `Documentation` - Docs and guides
- `Security` - Security reviews and fixes
- `Performance` - Optimization work
- `Bug Fix` - Fixing defects
- `Feature` - New functionality
- `Refactoring` - Code improvement
- `Infrastructure` - Deployment and tooling

## Epic Linking

Use the `epic` parameter to link a task to an epic:

```python
# Create task linked to an epic
task_create(
    title="Configure Gateway",
    description="Deploy gateway to staging environment with proper configuration",
    role="Operator",
    priority="HIGH",
    epic="EPC-H-0001"
)
```

**When to link to epics:**
- Task is part of a larger feature or initiative
- Task contributes to epic's overall goal
- Task needs to be tracked as part of epic progress

## Example: Creating a Task

```python
# Create a high-priority Engineer task
result = task_create(
    title="Implement Rate Limiting Middleware",
    description="Add rate limiting to protect API endpoints from abuse. Implement token bucket rate limiting with configurable limits per endpoint",
    role="Engineer",
    priority="HIGH",
    category="Security"
)

# Returns:
# {
#   "task_id": "ENG-H-0007",
#   "title": "Implement Rate Limiting Middleware",
#   "status": "TODO",
#   "file_path": ".opencode/work/tasks/ENG-H-0007.md"
# }
```


## What Happens When You Create

1. ✅ Task ID auto-generated (e.g., ENG-H-0007)
2. ✅ Database entry created in `project.db`
3. ✅ Markdown file created at `.opencode/work/tasks/ENG-H-0007.md` with template
4. ✅ Status set to `TODO`
5. ✅ Tool returns JSON with task details

## Validation

The tool validates:
- ✅ Priority is valid value (CRITICAL, HIGH, MEDIUM, LOW)
- ✅ Role is valid value
- ✅ Task ID is auto-generated correctly
- ✅ All required fields are provided
- ✅ Dependencies exist (if specified)

## After Creating

Verify task was created using the `task_show` tool:
```python
# Use the auto-generated task ID from the create result
task_show(task_id="ENG-H-0007")
```

## Tips and Best Practices

### Do
- ✅ Use clear, action-oriented titles
- ✅ Write detailed descriptions explaining what and why
- ✅ Assign appropriate priority
- ✅ Link to epics when task is part of larger initiative
- ✅ Choose the most appropriate role
- ✅ Add category for better organization

### Don't
- ❌ Don't create tasks for trivial work (<1 hour)
- ❌ Don't create duplicate tasks
- ❌ Don't use vague titles or descriptions
- ❌ Don't over-prioritize (not everything is CRITICAL)

## Troubleshooting

### "Invalid priority value"
- Check spelling: CRITICAL, HIGH, MEDIUM, LOW (all caps)
- See priority guidelines above

### "Invalid role value"
- Check spelling and capitalization
- Use full role name (e.g., "Engineer" not "Eng")

### "Epic not found"
- Epic ID in `epic` parameter doesn't exist
- Check epic IDs using `task_list` tool with epic category filter
- Fix the epic ID or create the epic first

## See Also

**Related Skills:**
- `task-query` - Finding and listing tasks
- `task-claim` - Claiming tasks to work on
- `task-management` - Overview of task system

**Documentation:**
- `.opencode/data/README.md` - Complete s9 system reference
