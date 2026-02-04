# .opencode Directory Structure

After running `s9 init`, site-nine creates a `.opencode` directory in your project. This directory contains all the configuration, data, and documentation needed for AI persona orchestration.

## Directory Overview

```
.opencode/
├── README.md              # Complete guide to your setup
├── data/                  # Database and persistent storage
│   └── project.db         # SQLite database
├── guides/                # Reference documentation
│   └── PERSONAS.md        # How to work with personas
├── procedures/            # Workflow documentation
│   ├── COMMIT_GUIDELINES.md
│   └── TASK_WORKFLOW.md
├── missions/              # Mission history
├── tasks/                 # Task markdown files
└── work/                  # Active work artifacts
    └── missions/          # Mission documentation
```

## Directory Details

### `README.md`

The main entry point for understanding your `.opencode` setup. Contains:
- Overview of enabled features
- Quick reference for common workflows
- Links to detailed guides

**Safe to edit:** Customize this for your team's needs.

### `data/`

Contains the SQLite database that tracks all project management data.

!!! danger "Do Not Manually Edit"
    Manual edits can corrupt the database. Use `s9` CLI commands or ask agents to manage tasks and sessions instead.

### `guides/`

Reference documentation for working with personas and understanding the system.

**Key files:**
- `PERSONAS.md` - Comprehensive guide to persona roles and workflows

**Safe to edit:** Customize these markdown files for your team.

### `procedures/`

Step-by-step workflow documentation for common operations.

**Key files:**
- `COMMIT_GUIDELINES.md` - Git commit message conventions
- `TASK_WORKFLOW.md` - How to create, claim, and complete tasks

**Safe to edit:** Customize these to match your team's processes.

### `missions/`

Historical record of missions. Each mission creates a log file here.

!!! warning "Do Not Edit"
    Mission files are automatically managed. View mission history with `s9 mission list`.

### `tasks/`

Individual markdown files for each task, named by task ID (e.g., `BLD-H-0001.md`).

!!! warning "Do Not Edit"
    Task files sync with the database. Create/update tasks using `s9 task` commands or ask your persona.

### `work/`

Active work-in-progress artifacts, organized by type.

!!! warning "Do Not Edit"
    Personas manage these files automatically during missions.

## What Can I Safely Edit?

**Safe to edit:**
- `README.md` - Customize for your team
- `guides/*.md` - Add team-specific documentation
- `procedures/*.md` - Customize workflows and guidelines

**Read-only (view but don't edit):**
- `missions/*` - Historical mission logs
- `tasks/*.md` - Task documentation (synced with database)
- `work/missions/*.md` - Active mission documentation

**Do not touch:**
- `data/project.db` - Database file (use CLI commands instead)
- Any `.db-journal` or `.db-wal` files (SQLite internals)

## Asking Personas About Project Data

Instead of querying the database directly, ask your personas for information conversationally.

**You:**
> Show me all active tasks

**Persona:**
> Here are the active tasks:
> 
> | ID         | Priority | Role   | Title                          | Persona  |
> |------------|----------|--------|--------------------------------|----------|
> | BLD-H-0003 | HIGH     | Builder| Implement rate limiting        | Azazel   |
> | TST-M-0007 | MEDIUM   | Tester | Add integration tests          | Eris     |
> | DOC-L-0012 | LOW      | Docs   | Update README                  | Nabu     |

**You:**
> Which personas are currently working?

**Persona:**
> **Active Missions:**
> - Azazel (Builder) - Started 2 hours ago - Working on rate limiting
> - Eris (Tester) - Started 45 minutes ago - Writing integration tests

**You:**
> What are the most frequently used persona names?

**Persona:**
> **Most Active Persona Names:**
> 1. Azazel - 12 missions (Builder)
> 2. Eris - 8 missions (Tester)
> 3. Kothar - 6 missions (Architect)
> 4. Nabu - 5 missions (Documentarian)
> 5. Mephistopheles - 4 missions (Administrator)

## Backing Up Your Work

To backup your entire `.opencode` directory:

```bash
tar -czf opencode-backup-$(date +%Y%m%d).tar.gz .opencode/
```

To backup just the database:

```bash
cp .opencode/data/project.db .opencode/data/project.db.backup
```

## Troubleshooting

**Q: I accidentally deleted a mission file. How do I recover it?**

Mission files are not critical to system operation. The database maintains the mission record. However, you'll lose the detailed work log. Restore from backup if available.

**Q: The database seems corrupted. What should I do?**

Ask an Administrator persona to check the database health:

**You:**
> Check the database for any issues

**Persona (Administrator):**
> Running database health check...
> 
> ✓ Database integrity check passed
> ✓ All tables present and valid
> ✓ No orphaned records found
> 
> The database is healthy!

If the persona reports corruption, restore from backup. If no backup exists, you may need to reinitialize:
```bash
# Backup current state first!
mv .opencode/data/project.db .opencode/data/project.db.broken
# Then run
s9 doctor
```

**Q: Can I version control `.opencode`?**

Yes! Recommended `.gitignore` patterns:
```gitignore
# Ignore database and SQLite internals
.opencode/data/*.db
.opencode/data/*.db-journal
.opencode/data/*.db-wal

# Keep everything else
!.opencode/guides/
!.opencode/procedures/
!.opencode/README.md
```

Session and task files can be committed if you want to track persona work history.
