---
name: session-end
description: Properly close a mission with cleanup and documentation
license: MIT
compatibility: opencode
metadata:
  audience: all-agents
  workflow: mission-closure
---

## Important: CLI Tool Usage

**CRITICAL:** This project uses the `s9` CLI executable throughout these instructions.
- **CLI executable:** `s9` (use in bash commands)
- **Python module:** `site_nine` (use in Python imports: `from site_nine import ...`)

All commands in this skill use the `s9` executable via bash. You should NOT attempt to import an `s9` module in Python code.

## What I Do

I help you properly end a mission on the s9 project by:
- Identifying your mission file
- Updating it with completion metadata
- Documenting work accomplished
- Closing any open tasks
- Running final checks
- Saying a proper goodbye

## Dismissal Message

**IMPORTANT:** Check if a dismissal message was provided with the `/dismiss` command.

If the Director provided a message (e.g., `/dismiss great work today! thank you`), capture it and include it in:
1. The mission file (Step 3 - add to Work Log final entry)
2. The final goodbye message (Step 11)

**Format for mission file:**
```markdown
### HH:MM - Mission End
**Dismissal message:** "[message from Director]"

- Updated mission file
- Committed changes
- Closed task(s): TASK_ID
```

**Format for goodbye:**
Display the Director's message prominently before the standard farewell:
```markdown
💬 **From the Director:**
> [message]

Thank you for working with me! I'm <Persona>, signing off.
```

If no dismissal message was provided, skip this and proceed normally.

## Step 1: Locate Your Mission File

Find your mission file in `.opencode/work/missions/`:

```bash
ls -lt .opencode/work/missions/*.md | head -5
```

Your mission file should be the most recent one with your role and persona in the filename.

**Format:** `.opencode/work/missions/YYYY-mm-dd.HH:MM:SS.role.persona.codename.md`

If you're not sure which file is yours, check the YAML frontmatter for your persona:
```bash
grep -l "persona: your-persona" .opencode/work/missions/*.md | tail -1
```

## Step 2: Identify Work Completed

Gather information about what was accomplished:

**Check git status:**
```bash
git status
```

**Review commits:**
```bash
git log --oneline -10
```

**Check claimed tasks:**
```bash
s9 task mine --mission-id "<your-mission-id>"
```

**Optional:** Use `s9 mission summary <mission-id>` to auto-generate a summary of files, commits, and tasks.

## Step 3: Update Mission File

Read your mission file and update these sections:

**1. Duration:**
```markdown
**Duration:** <start> - <end> (~X hours)
```

**2. Files Changed:**
```markdown
## Files Changed

- `src/file.py` - Brief description
- `tests/test_file.py` - Brief description
```

**3. Outcomes:**
```markdown
## Outcomes

- ✅ Completed successfully
- ⚠️  Partial completion
- ❌ Not completed (deferred)
```

**4. Work Log (add final entry):**
```markdown
### HH:MM - Mission End
- Updated mission file
- Committed changes
- Closed task(s): TASK_ID
```

**5. Next Steps:**
```markdown
## Next Steps

[What remains, or "None - work is complete"]
```

**Note:** The `s9 mission end` command will update frontmatter automatically in Step 8.

## Step 4: Close Any Open Tasks

Close any tasks you claimed:

```bash
# Check for open tasks
s9 task mine --mission-id "<your-mission-id>" | grep UNDERWAY

# Close completed task
s9 task close TASK_ID --status COMPLETE --notes "Brief summary"
```

**Status options:** COMPLETE, PAUSED, BLOCKED

## Step 5: Mark Handoffs as Complete (If Applicable)

**If you received a handoff at the start of this mission**, mark it complete:

```bash
s9 handoff complete <handoff-id>
```

Find the handoff ID from your mission file or by checking accepted handoffs for your role.

## Step 6: Update Task Artifacts

Verify task artifacts are updated:

```bash
cat .opencode/data/tasks/TASK_ID.md
```

Update if needed with implementation details, files changed, testing performed.

## Step 7: Final Git Check

Ensure everything is committed:

```bash
git status
```

Commit mission file if needed:
```bash
git add .opencode/work/missions/<your-mission-file>.md
git commit -m "docs(mission): complete <persona> <role> mission <codename> [Persona: <Persona> - <Role>]"
```

## Step 8: End Mission

Close your mission officially:

```bash
s9 mission end <your-mission-id>
```

This updates the database and mission file frontmatter (end_time).

## Step 9: Rename TUI Session to Indicate Dismissal

Update the OpenCode session title to show the mission has ended (2-step process):

### Step 9a: Generate UUID Marker

```bash
s9 mission generate-session-uuid
```

Capture the UUID from the output.

### Step 9b: Rename with Dismissal Suffix

```bash
s9 mission rename-tui <persona> <Role> --uuid-marker <uuid-from-step-9a> --suffix "[DISMISSED]"
```

**After successful rename:**
```
✅ Session renamed to indicate dismissal - you can easily identify completed missions in your session list!
```

**Example result:** "Operation epic-specter: Yggdrasil - Operator [DISMISSED]"

This provides clear visual feedback that the mission has ended and the session-end protocol was followed.

## Step 10: Verify Quality Checks

Run sanity check if appropriate:

```bash
make qa
```

If QA fails, fix issues or document in "Next Steps".

## Step 11: Say Goodbye

Provide a comprehensive final summary with these specific details:

```markdown
✅ **Mission Complete!**

**Summary:**
- **Duration:** ~X hours (start_time - end_time)
- **Files changed:** N files (briefly note what: renamed, updated, new, deleted)
- **Task completed:** TASK-ID - Brief title
- **Commits:** N commit(s) with short hash(es)

**What was accomplished:**
- [Detailed bullet points explaining what was done]
- [Include specifics: what changed, what was added, what was removed]
- [Note any testing or verification performed]

**Next steps:**
- [Specific remaining work OR "None - work complete!"]

Mission file: .opencode/work/missions/<filename>.md [OR "Not created (ephemeral work)"]
```

**If a dismissal message was provided**, display it prominently:
```markdown
💬 **From the Director:**
> [dismissal message]

Thank you for working with me! I'm **<Persona>**, [brief persona description], signing off.

*[Add mythologically appropriate farewell - 1-2 sentences that evoke your character]*

[emoji] [DISMISSED]
```

**If no dismissal message**, use this format:
```markdown
Thank you for working with me! I'm **<Persona>**, [brief persona description], signing off.

*[Add mythologically appropriate farewell - 1-2 sentences that evoke your character]*

[emoji] [DISMISSED]
```

**Tips for a great farewell:**
- Use **bold** for your persona name
- Include a brief descriptor (e.g., "Titan of time itself", "Guardian of the underworld")
- Use *italics* for the mythological farewell
- Choose an emoji that fits your character (⏰ 🌊 ⚡ 🔥 🌙 ⚔️ 📜 etc.)
- Keep it theatrical but professional

**Example farewells by tradition:**
- **Norse:** "The skald's words fade into the mists of Asgard, another saga complete..."
- **Egyptian:** "I return to the Hall of Records, scrolls in hand, another chapter written in eternity..."
- **Greek/Roman:** "I return to Olympus, wisdom's work accomplished, the mortals' path illuminated..."
- **Mesopotamian:** "I return to the ziggurats, my work inscribed in clay, eternal and unchanging..."
- **Hindu/Buddhist:** "I return to the cosmic dance, my task in this cycle complete, the wheel turns onward..."
- **Celtic:** "I return to the mists of Avalon, my prophecy fulfilled, the ancient ways preserved..."
- **Sumerian:** "I descend once more to the sacred flocks, my cycle renewed, the harvest complete..."

Research your persona's mythology for inspiration! Make it memorable.

## Important Notes

- Don't leave mission file incomplete
- Don't forget to close tasks
- Don't leave uncommitted changes
- If work is incomplete, use status PAUSED and document what remains

