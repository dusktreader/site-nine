# Temporary Scripts Directory

This directory contains **temporary, task-specific scripts** created during mission work. These scripts are typically one-time use utilities for data migrations, testing, or solving specific problems.

## Purpose

- Store temporary/ad-hoc scripts created during tasks
- Link scripts to specific tasks and missions for traceability
- Provide a clear location separate from permanent project utilities
- Establish guidelines for cleanup when work completes

## Naming Convention

All scripts must follow this naming pattern:

```
TASK-ID-descriptive-name.ext
```

**Examples:**
- `OPR-H-0116-migrate-task-status.py`
- `DOC-H-0118-audit-cli-commands.sh`
- `ENG-H-0123-test-database-migration.sql`

**Why this convention?**
- Clearly links script to originating task
- Makes purpose immediately visible
- Enables easy cleanup when tasks complete
- Prevents orphaned scripts with unclear ownership

## Script Header Requirements

Every script must include a header comment block with:

1. **Task ID** - The task that created this script (required)
2. **Mission ID** - The mission context (optional but recommended)
3. **Purpose** - Brief description of what the script does (required)
4. **Deletion Criteria** - When this script should be removed (required)

See `script-template.py` for a template with proper header format.

## Deletion Criteria

Scripts should be removed when:

- The associated task is completed
- The associated mission ends
- The script's purpose has been fulfilled
- The script is replaced by a permanent solution

**During mission cleanup:**
- Review scripts created during your mission
- Delete scripts that are no longer needed
- Move scripts to permanent locations if they have ongoing value
- Document any scripts left for future work

## scripts/ vs .opencode/work/scripts/

**Important distinction:**

- **`scripts/` (project root)** - Permanent utility scripts that are part of the project
  - Database utilities
  - Development tools
  - CI/CD helpers
  - Maintained as project code

- **`.opencode/work/scripts/` (this directory)** - Temporary task-specific scripts
  - One-time migrations
  - Quick testing utilities
  - Problem-solving scripts
  - Linked to specific tasks/missions
  - Should be cleaned up

**Rule of thumb:** If you're writing a script during a task and it's only needed for that task or mission, put it here. If it's a tool the project will use repeatedly, put it in `scripts/`.

## Task/Mission Linkage

Scripts in this directory must be:

1. **Created during active tasks** - Associated with a specific task ID
2. **Documented in task notes** - Mention script creation in task updates
3. **Referenced in mission files** - Note significant scripts in your mission log
4. **Cleaned up** - Removed or moved when the task/mission completes

This ensures scripts don't become orphaned and their purpose remains clear.

## Examples

### Good Script Usage

```python
# Task: DOC-H-0122
# Mission: 92 (Operation gamma-raven)
# Purpose: Validate all skill files have correct metadata format
# Delete when: DOC-H-0122 is complete

import glob
import yaml

# Script implementation...
```

### What NOT to Do

- Scripts without headers
- Scripts without task linkage
- Scripts with generic names like `test.py` or `fix_thing.sh`
- Leaving scripts behind after task completion
- Creating permanent utilities here instead of in `scripts/`

## Migration Path

If a temporary script proves valuable long-term:

1. **Refactor** - Clean up code, add proper error handling
2. **Generalize** - Remove task-specific hardcoding
3. **Document** - Add comprehensive docstrings
4. **Move** - Relocate to appropriate location in `scripts/`
5. **Update** - Add to project documentation
6. **Remove** - Delete the temporary version from this directory

## Questions?

See the broader file organization guide at `.opencode/guides/file-organization.md` for more context on where different types of files belong in the site-nine project.
