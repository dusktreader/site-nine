---
name: mission-end
description: Properly close a mission with cleanup and documentation
license: MIT
compatibility: opencode
metadata:
  audience: all-agents
  workflow: mission-closure
---

## ⚠️ BEFORE YOU PROCEED - VERIFY DISMISSAL ⚠️

**STOP! Read this carefully before executing this skill:**

**You should ONLY execute this skill if:**
1. ✅ The Director explicitly used the `/dismiss` command, OR
2. ✅ The Director explicitly said you're dismissed/done/released, OR
3. ✅ The Director clearly indicated the session is ending

**DO NOT execute this skill if:**
- ❌ You're just finished with one task (claim another task instead)
- ❌ The conversation has paused or slowed down
- ❌ You're waiting for the Director to respond
- ❌ You think maybe you should wrap up
- ❌ The Director just said "thanks" or "good work" (that's not dismissal)

**If you're unsure, ASK:**
```
Director, are you dismissing me? Should I end my mission and close this session?
```

**Why this matters:**
- Ending your mission prematurely creates "zombie" ACTIVE/IDLE missions in the database
- Missions without heartbeats for >8h are flagged as stale by `s9 doctor`
- Tasks get left in inconsistent states
- The system accumulates abandoned work
- You waste the Director's time

**If you proceed incorrectly, the Director will be frustrated with you.**

---

**Assuming you have been properly dismissed, proceed with the following steps:**

## What I Do

I help you properly end a mission on the s9 project by:
- Identifying your mission file
- Updating it with completion metadata
- Documenting work accomplished
- Closing any open tasks
- **CRITICALLY: Invoking the `mission_end` tool to close the mission in the database**
- **Invoking the `mission_rename_dismissed` tool to mark the session as dismissed**
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

## Step 5: Update Task Artifacts

Verify task artifacts are updated:

```bash
cat .opencode/data/tasks/TASK_ID.md
```

Update if needed with implementation details, files changed, testing performed.

## Step 6: Final Git Check

Ensure everything is committed:

```bash
git status
```

Commit mission file if needed:
```bash
git add .opencode/work/missions/<your-mission-file>.md
git commit -m "docs(mission): complete <persona> <role> mission <codename> [Persona: <Persona> - <Role>]"
```

## Step 6.5: Clean Up Temporary Files

**⚠️ IMPORTANT:** Remove any temporary files you created during this mission.

**Check for temporary scripts:**
```bash
ls .opencode/work/scripts/
```

**Remove scripts you created:**
```bash
# Delete scripts for tasks you completed
rm .opencode/work/scripts/TASK-ID-*.{py,sh,sql}

# Example:
rm .opencode/work/scripts/DOC-H-0122-*.py
```

**Remove temporary planning documents (if any):**
```bash
# Check planning directory
ls .opencode/work/planning/

# Remove your temporary planning docs
rm .opencode/work/planning/my-planning-doc.md  # If you created any
```

**What to keep:**
- Mission file (permanent record)
- Task files (managed by system)
- Any files that moved to permanent locations

**What to remove:**
- Scripts in `.opencode/work/scripts/` for tasks you completed
- Temporary planning documents
- Any scratch files you created

**Verify project root is clean:**
```bash
git status
```

If you see any uncommitted files in the project root that you created (e.g., `temp.py`, `notes.md`), either:
1. Delete them if temporary
2. Move them to appropriate location in `.opencode/work/`
3. Commit them if they're meant to be permanent

**See:** `.opencode/docs/guides/file-organization.md` for cleanup guidelines.

## Step 7: End Mission ⚠️ MANDATORY - DO NOT SKIP ⚠️

**THIS IS THE MOST CRITICAL STEP** - If you skip this, your mission will remain in the database as an IDLE "zombie" mission forever.

Close your mission officially in the database by invoking the `mission_end` tool:

```
Invoke the mission_end tool
```

The tool automatically:
- Retrieves your mission ID from the current OpenCode session context
- Sets the `end_time` in the missions table
- Sets the mission status to `ENDED`
- Marks the mission as officially closed
- Updates the mission file frontmatter
- Prevents the mission from showing up as ACTIVE/IDLE in the dashboard

**IF YOU DO NOT INVOKE THIS TOOL:**
- ❌ Your mission will remain "active" in the database indefinitely
- ❌ It will show as ACTIVE or IDLE in `s9 dashboard`
- ❌ `s9 doctor` will flag it as stale after 8 hours with no heartbeat
- ❌ The Director will have to manually clean up after you

**The tool will return confirmation** that the mission was ended successfully. If it fails, try invoking it again.

## Step 8: Rename Session to Indicate Dismissal

Update the OpenCode session title to show the mission has ended by invoking the `mission_rename_dismissed` tool:

```
Invoke the mission_rename_dismissed tool
```

The tool automatically:
- Retrieves your mission details (persona, role, codename) from the current session context
- Renames the OpenCode session title to include a `[DISMISSED]` suffix
- Provides clear visual feedback that the mission has ended

**After successful invocation:**
```
✅ Session renamed to indicate dismissal - you can easily identify completed missions in your session list!
```

**Example result:** "Operation gamma-apex: Izanagi - Architect [DISMISSED]"

This provides clear visual feedback that the mission has ended and the mission-end protocol was followed.

## Step 9: Verify Quality Checks

Run sanity check if appropriate:

```bash
make qa
```

If QA fails, fix issues or document in "Next Steps".

## Step 10: Say Goodbye

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
- **Clean up temporary files in `.opencode/work/scripts/` and `.opencode/work/planning/`**
- **Verify project root has no temporary files you created**
- **See `.opencode/docs/guides/file-organization.md` for file cleanup guidelines**

