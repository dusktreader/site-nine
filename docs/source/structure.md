# .opencode Directory Structure

After running `s9 init`, site-nine creates a `.opencode` directory in your project. This directory contains all the configuration, data, and documentation needed for AI agent orchestration.

## Directory Overview

```
.opencode/
├── README.md              # Complete guide to your setup
├── data/                  # Database and persistent storage
│   └── project.db         # SQLite database
├── docs/                  # Internal agent reference documentation
│   └── roles/             # Role-specific guides
├── procedures/            # Workflow documentation
│   ├── COMMIT_GUIDELINES.md
│   └── TASK_WORKFLOW.md
├── tasks/                 # Task markdown files
└── work/                  # Active work artifacts
    ├── epics/             # Epic documentation
    └── possessions/       # Possession session files
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

### `docs/`

Internal reference documentation for agents. Role-specific guides live here and are loaded automatically during possession initialization.

**Key files:**
- `roles/*.md` - Per-role instructions and context for agents

**Safe to edit:** Customize these markdown files for your team.

### `procedures/`

Step-by-step workflow documentation for common operations.

**Key files:**
- `COMMIT_GUIDELINES.md` - Git commit message conventions
- `TASK_WORKFLOW.md` - How to create, claim, and complete tasks

**Safe to edit:** Customize these to match your team's processes.

### `tasks/`

Individual markdown files for each task, named by task ID (e.g., `ENG-H-0001.md`).

!!! warning "Do Not Edit"
    Task files sync with the database. Create/update tasks using `s9 task` commands or ask your agent.

### `work/`

Active work-in-progress artifacts, organized by type.

!!! warning "Do Not Edit"
    Agents manage these files automatically during possessions.

#### `work/possessions/`

Session files for active and completed possessions, named by timestamp and role:

```
.opencode/work/possessions/2026-03-14.09-15-00.engineer.Hephaestus.md
```

Each file documents the possession's objectives, progress, and commit history.

#### `work/epics/`

Generated markdown views of active epics. These are regenerated from the database; the database is the source of truth.

## What Can I Safely Edit?

**Safe to edit:**
- `README.md` - Customize for your team
- `docs/*.md` - Add team-specific documentation
- `procedures/*.md` - Customize workflows and guidelines

**Read-only (view but don't edit):**
- `tasks/*.md` - Task documentation (synced with database)
- `work/possessions/*.md` - Active possession documentation

**Do not touch:**
- `data/project.db` - Database file (use CLI commands instead)
- Any `.db-journal` or `.db-wal` files (SQLite internals)

## Asking Agents About Project Data

Instead of querying the database directly, ask your agents for information conversationally.

**You:**
> Show me all active tasks

**Agent:**
> Here are the active tasks:
> 
> | ID         | Priority | Role   | Title                          | Daemon     |
> |------------|----------|--------|--------------------------------|------------|
> | ENG-H-0003 | HIGH     | Engineer| Implement rate limiting        | Hephaestus |
> | TST-M-0007 | MEDIUM   | Tester | Add integration tests          | Eris       |
> | DOC-L-0012 | LOW      | Docs   | Update README                  | Nabu       |

**You:**
> Which agents are currently working?

**Agent:**
> **Active Possessions:**
> - Hephaestus (Engineer) - Started 2 hours ago - Working on rate limiting
> - Eris (Tester) - Started 45 minutes ago - Writing integration tests

**You:**
> What are the most frequently used daemon names?

**Agent:**
> **Most Active Daemons:**
> 1. Azazel - 12 possessions (Inspector)
> 2. Eris - 8 possessions (Tester)
> 3. Kothar - 6 possessions (Architect)
> 4. Nabu - 5 possessions (Documentarian)
> 5. Mephistopheles - 4 possessions (Administrator)

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

**Q: I accidentally deleted a possession file. How do I recover it?**

Possession files are not critical to system operation. The database maintains the possession record. However, you'll lose the detailed work log. Restore from backup if available.

**Q: The database seems corrupted. What should I do?**

Ask an Administrator agent to check the database health:

**You:**
> Check the database for any issues

**Agent (Administrator):**
> Running database health check...
> 
> ✓ Database integrity check passed
> ✓ All tables present and valid
> ✓ No orphaned records found
> 
> The database is healthy!

If the agent reports corruption, restore from backup. If no backup exists, you may need to reinitialize:
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
!.opencode/docs/
!.opencode/procedures/
!.opencode/README.md
```

Session and task files can be committed if you want to track agent work history.
