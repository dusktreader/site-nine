# Development Sessions

This directory contains individual session files documenting development work on s9.

Each session is a separate markdown file with metadata and detailed work log.


---


## Session File Naming

**Format:** `<YYYY-mm-dd>.<HH:MM:SS>.<role>.<name>.<task-summary>.md`

**Examples:**
- `2026-01-29.14:30:45.engineer.azazel.add-rate-limiting.md`
- `2026-01-29.16:15:00.documentarian.seraphina.update-readme.md`
- `2026-01-30.09:00:00.architect.mephistopheles.design-auth-system.md`
- `2026-01-30.11:00:00.engineer.azazel-ii.refactor-queries.md` (second use of "azazel")

**Components:**
- `YYYY-mm-dd` - Session start date
- `HH:MM:SS` - Session start time (24-hour format)
- `role` - Agent role (lowercase: manager, architect, engineer, tester, documentarian, inspector, operator)
- `name` - Agent daemon name (lowercase, from any religion's mythology)
  - First use: just the name (e.g., `lucifer`)
  - Subsequent uses: append roman numeral (e.g., `lucifer-ii`, `lucifer-iii`)
- `task-summary` - Brief task description (lowercase, hyphen-separated)

**Daemon Name Examples:**
- **Christian/Jewish:** lucifer, mephistopheles, beelzebub, asmodeus, mammon, leviathan, belphegor, azazel, belial, moloch
- **Islamic:** iblis, shaitan, ifrit, marid, jinn
- **Hindu:** rakshasas, asuras, ravana, kali, mahishasura
- **Buddhist:** mara, yama, vetala
- **Greek/Roman:** erinyes (furies), hecate, nemesis, thanatos, charon
- **Norse:** loki, hel, fenrir, jormungandr, surtr
- **Zoroastrian:** ahriman, angra mainyu, druj
- **Sumerian/Babylonian:** pazuzu, lamashtu, lilitu, tiamat
- **Egyptian:** apep, set, ammit
- **Celtic:** balor, morrigan
- **Slavic:** chernobog, baba yaga

**Disambiguation Rules:**
- First agent named "azazel": `azazel`
- Second agent named "azazel": `azazel-ii`
- Third agent named "azazel": `azazel-iii`
- Fourth agent named "azazel": `azazel-iv`
- And so on...


---


## Session File Template

Each session file should follow this structure (see `TEMPLATE.md` in this directory):

```markdown
---
date: YYYY-MM-DD
start_time: HH:MM:SS
end_time: HH:MM:SS (or "in-progress")
role: <role>
name: <name>
task_summary: <brief description>
status: completed | failed | aborted | in-progress
---

# Session: <Task Summary>

**Agent:** <Name> (<Role>)
**Date:** <YYYY-MM-DD>
**Duration:** <start> - <end> (<duration>)
**Status:** <status>


## Objective

What this session aimed to accomplish.


## Work Log

Chronological log of work done:

### HH:MM - Task/Action
- Details
- Decisions made
- Issues encountered


## Files Changed

- `path/to/file` - Description of changes
- `path/to/another/file` - Description


## Outcomes

- ✅ What was successfully completed
- ⚠️  What needs follow-up
- ❌ What failed or was blocked


## Next Steps

What should be done next (if applicable).


## Notes

Any additional context, learnings, or observations.
```


---


## Finding Sessions

**List all sessions:**
```bash
ls -lt .opencode/work/sessions/*.md
```

**Find sessions by agent name:**
```bash
ls .opencode/work/sessions/*.<name>.*.md
```

**Find sessions by role:**
```bash
ls .opencode/work/sessions/*.<role>.*.md
```

**Find sessions by date:**
```bash
ls .opencode/work/sessions/2026-01-29.*.md
```

**Search session content:**
```bash
grep -r "keyword" .opencode/work/sessions/
```


---


## Session Lifecycle

### Starting a Session

1. Agent asks user for role
2. Agent suggests daemon name or asks user to choose one
3. Agent checks if name has been used before (scan existing session files)
4. If name used before, append roman numeral (e.g., `-ii`, `-iii`, `-iv`)
5. Agent creates session file: `YYYY-mm-dd.HH:MM:SS.<role>.<name>.<task>.md`
6. Agent fills in metadata with `status: in-progress`
7. Agent documents objective

### During Session

- Agent updates Work Log with timestamped entries
- Agent records decisions, issues, and progress
- Work Log shows chronological development

### Ending Session

1. Agent summarizes outcomes (completed/failed/blocked items)
2. Agent lists all changed files
3. Agent adds next steps if needed
4. Agent updates metadata:
   - `end_time: HH:MM:SS`
   - `status: completed` (or failed/aborted)


---


## Session Status Values

| Status | Meaning |
|--------|---------|
| `in-progress` | Session currently active |
| `completed` | Session finished successfully |
| `failed` | Session attempted but failed to complete objective |
| `aborted` | Session stopped early (user interrupted, blocked, etc.) |


---


## Benefits

1. **Self-Documenting** - Filename contains key metadata
2. **Discoverable** - Easy to find sessions by date, role, name, or task
3. **Independent** - Each session is standalone
4. **Detailed** - Chronological work log with context
5. **Traceable** - Clear outcomes and file changes
6. **Continuity** - Next steps link sessions together


---


## Related Documents

- **procedures/COMMIT_GUIDELINES.md** - How to format commits with agent names
- **procedures/CHANGELOG.md** - High-level change history
- **procedures/WORKFLOWS.md** - Development workflow patterns
