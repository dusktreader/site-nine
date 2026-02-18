---
name: task-create
description: Create new tasks in the s9 task database with proper formatting and validation
license: MIT
compatibility: opencode
metadata:
  audience: all-agents
  workflow: task-creation
---

## Important: CLI Tool Usage

**CRITICAL:** This project uses the `s9` CLI executable throughout these instructions.
- **CLI executable:** `s9` (use in bash commands)
- **Python module:** `site_nine` (use in Python imports: `from site_nine import ...`)

All commands in this skill use the `s9` executable via bash. You should NOT attempt to import an `s9` module in Python code.

## What I Do

I provide comprehensive instructions for creating new tasks in the s9 task database. Use this skill when you need to add new work items to the project.

## When to Create Tasks

- **Administrator** role adding new work items
- **Inspector** creating follow-up tasks from reviews
- **Architect** creating implementation tasks from design
- Breaking down epics into smaller tasks
- Creating tasks for bugs or technical debt

## Command Syntax

```bash
s9 task create \
  --title "Brief task title" \
  --objective "What this task accomplishes" \
  --role {Administrator|Architect|Engineer|Tester|Documentarian|Designer|Inspector|Operator|Historian} \
  --priority {CRITICAL|HIGH|MEDIUM|LOW} \
  [--category "Category name"] \
  [--description "Detailed description"] \
  [--depends-on OTHER_TASK_ID]
```

**Note:** Task IDs are **auto-generated** based on role and priority. You do not need to provide a task ID.

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

## Dependencies

Use `--depends-on` when a task cannot start until another completes:

```bash
# Create task that depends on another
s9 task create \
  --title "Configure Gateway" \
  --objective "Deploy gateway to staging" \
  --role Operator \
  --priority HIGH \
  --depends-on ENG-H-0037
```

**When to use dependencies:**
- Implementation depends on design approval
- Integration depends on component completion
- Deployment depends on code changes
- Testing depends on feature implementation

## Example: Creating a Task

```bash
# Create a high-priority Engineer task (ID will be auto-generated)
s9 task create \
  --title "Implement Rate Limiting Middleware" \
  --objective "Add rate limiting to protect API endpoints from abuse" \
  --role Engineer \
  --priority HIGH \
  --category "Security" \
  --description "Implement token bucket rate limiting with configurable limits per endpoint"

# Output: ✓ Created task ENG-H-0007: Implement Rate Limiting Middleware
```


## What Happens When You Create

1. ✅ Task ID auto-generated (e.g., ENG-H-0007)
2. ✅ Database entry created in `project.db`
3. ✅ Markdown file created at `.opencode/work/tasks/ENG-H-0007.md` with template
4. ✅ Status set to `TODO`

## Validation

The CLI validates:
- ✅ Priority is valid value (CRITICAL, HIGH, MEDIUM, LOW)
- ✅ Role is valid value
- ✅ Task ID is auto-generated correctly
- ✅ All required fields are provided
- ✅ Dependencies exist (if specified)

## After Creating

Verify task was created:
```bash
# Use the auto-generated task ID from the create command output
s9 task show ENG-H-0007
```

## Tips and Best Practices

### Do
- ✅ Use clear, action-oriented titles
- ✅ Write specific objectives (not "fix stuff")
- ✅ Assign appropriate priority
- ✅ Set dependencies when they exist
- ✅ Choose the most appropriate role
- ✅ Add category for better organization

### Don't
- ❌ Don't create tasks for trivial work (<1 hour)
- ❌ Don't create duplicate tasks
- ❌ Don't use vague titles or objectives
- ❌ Don't over-prioritize (not everything is CRITICAL)

## Troubleshooting

### "Invalid priority value"
- Check spelling: CRITICAL, HIGH, MEDIUM, LOW (all caps)
- See priority guidelines above

### "Invalid role value"
- Check spelling and capitalization
- Use full role name (e.g., "Engineer" not "Eng")

### "Dependency not found"
- Task ID in `--depends-on` doesn't exist
- Check task IDs: `s9 task list`
- Fix the dependency task ID

## See Also

**Related Skills:**
- `task-query` - Finding and listing tasks
- `task-claim` - Claiming tasks to work on
- `task-management` - Overview of task system

**Documentation:**
- `.opencode/data/README.md` - Complete s9 system reference
