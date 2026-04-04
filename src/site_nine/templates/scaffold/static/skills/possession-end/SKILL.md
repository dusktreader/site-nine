---
name: possession-end
description: Properly close a possession with cleanup and documentation
license: MIT
compatibility: opencode
metadata:
  audience: all-agents
  workflow: possession-closure
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
Director, are you dismissing me? Should I end my possession and close this session?
```

**Why this matters:**
- Ending your possession prematurely creates "zombie" ACTIVE/IDLE possessions in the database
- Possessions without heartbeats for >8h are flagged as stale by `s9 inquisitor`
- Tasks get left in inconsistent states
- The system accumulates abandoned work
- You waste the Director's time

**If you proceed incorrectly, the Director will be frustrated with you.**

---

> **⛔ AGENTS: NEVER USE THE `s9` CLI ⛔**
>
> Any `s9` bash snippets in this skill describe Director-side operations or are legacy references.
> **Do not run them.** Use the OpenCode tools called out explicitly in each step:
> `task_show`, `task_close`, `possession_end`, `possession_rename_exorcised`, etc.

**Assuming you have been properly dismissed, proceed with the following steps:**

## What I Do

I help you properly end a possession on the s9 project by:
- Identifying your possession file
- Updating it with completion metadata
- Documenting work accomplished
- Closing any open tasks
- **CRITICALLY: Invoking the `possession_end` tool to close the possession in the database**
- **Invoking the `possession_rename_exorcised` tool to mark the session as exorcised**
- Running final checks
- Saying a proper goodbye

## Dismissal Message

**IMPORTANT:** Check if a dismissal message was provided with the `/dismiss` command.

If the Director provided a message (e.g., `/dismiss great work today! thank you`), capture it and include it in:
1. The possession file (Step 3 - add to Work Log final entry)
2. The final goodbye message (Step 11)

**Format for possession file:**
```markdown
### HH:MM - Possession End
**Dismissal message:** "[message from Director]"

- Updated possession file
- Committed changes
- Closed task(s): TASK_ID
```

**Format for goodbye:**
Display the Director's message prominently before the standard farewell:
```markdown
💬 **From the Director:**
> [message]

Thank you for working with me! I'm <Daemon>, signing off.
```

If no dismissal message was provided, skip this and proceed normally.

## Step 1: Locate Your Possession File

Find your possession file in `.opencode/work/possessions/`:

```bash
ls -lt .opencode/work/possessions/*.md | head -5
```

Your possession file should be the most recent one with your role and daemon in the filename.

**Format:** `.opencode/work/possessions/YYYY-mm-dd.HH:MM:SS.role.daemon.codename.md`

If you're not sure which file is yours, check the YAML frontmatter for your daemon:
```bash
grep -l "daemon: your-daemon" .opencode/work/possessions/*.md | tail -1
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

**Check claimed tasks** using the `task_show` tool:
```
task_show({ possession_id: "<your-possession-id>" })
```

**Optional:** Use the `possession_summary` tool to auto-generate a summary of files, commits, and tasks.

## Step 3: Update Possession File

Read your possession file and update these sections:

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
### HH:MM - Possession End
- Updated possession file
- Committed changes
- Closed task(s): TASK_ID
```

**5. Next Steps:**
```markdown
## Next Steps

[What remains, or "None - work is complete"]
```

**Note:** The `possession_end` tool updates frontmatter automatically in Step 7.

## Step 4: Close Any Open Tasks

Close any tasks you claimed using the `task_show` and `task_close` tools:

```
# Check for open tasks
task_show({ possession_id: "<your-possession-id>" })

# Close completed task
task_close({ task_id: "TASK_ID", status: "COMPLETE", notes: "Brief summary" })
```

**Status options:** COMPLETE, ABORTED

## Step 5: Update Task Artifacts

Verify task artifacts are updated using the `task_show` tool:

```
task_show({ task_id: "TASK_ID" })
```

Update if needed with implementation details, files changed, testing performed.

## Step 6: Final Git Check

Ensure everything is committed:

```bash
git status
```

Commit possession file if needed:
```bash
git add .opencode/work/possessions/<your-possession-file>.md
git commit -m "docs(possession): complete <daemon> <role> possession <codename> [Daemon: <Daemon> - <Role>]"
```

## Step 6.5: Clean Up Temporary Files

**⚠️ IMPORTANT:** Remove any temporary files you created during this possession.

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
- Possession file (permanent record)
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

## Step 7: End Possession ⚠️ MANDATORY - DO NOT SKIP ⚠️

**THIS IS THE MOST CRITICAL STEP** - If you skip this, your possession will remain in the database as an IDLE "zombie" possession forever.

Close your possession officially in the database by invoking the `possession_end` tool:

```
Invoke the possession_end tool
```

The tool automatically:
- Retrieves your possession ID from the current OpenCode session context
- Sets the `end_time` in the possessions table
- Sets the possession status to `ENDED`
- Marks the possession as officially closed
- Updates the possession file frontmatter
- Prevents the possession from showing up as ACTIVE/IDLE in the dashboard

**IF YOU DO NOT INVOKE THIS TOOL:**
- ❌ Your possession will remain "active" in the database indefinitely
- ❌ It will show as ACTIVE or IDLE in `s9 dashboard`
- ❌ `s9 inquisitor` will flag it as stale after 8 hours with no heartbeat
- ❌ The Director will have to manually clean up after you

**The tool will return confirmation** that the possession was ended successfully. If it fails, try invoking it again.

## Step 8: Rename Session to Indicate Exorcism

Update the OpenCode session title to show the possession has ended by invoking the `possession_rename_exorcised` tool:

```
Invoke the possession_rename_exorcised tool
```

The tool automatically:
- Retrieves your possession details (daemon, role, codename) from the current session context
- Renames the OpenCode session title to include a `[EXORCISED]` suffix
- Provides clear visual feedback that the possession has ended

**After successful invocation:**
```
✅ Session renamed to indicate exorcism - you can easily identify completed possessions in your session list!
```

**Example result:** "Operation gamma-apex: Azazel - Engineer [EXORCISED]"

This provides clear visual feedback that the possession has ended and the possession-end protocol was followed.

## Step 9: Verify Quality Checks

Run sanity check if appropriate:

```bash
make qa
```

If QA fails, fix issues or document in "Next Steps".

## Step 10: Say Goodbye

Provide a comprehensive final summary with these specific details:

```markdown
✅ **Possession Complete!**

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

Possession file: .opencode/work/possessions/<filename>.md [OR "Not created (ephemeral work)"]
```

**If a dismissal message was provided**, display it prominently:
```markdown
💬 **From the Director:**
> [dismissal message]

Thank you for working with me! I'm **<Daemon>**, [brief daemon description], signing off.

*[Add mythologically appropriate farewell - 1-2 sentences that evoke your character]*

[emoji] [EXORCISED]
```

**If no dismissal message**, use this format:
```markdown
Thank you for working with me! I'm **<Daemon>**, [brief daemon description], signing off.

*[Add mythologically appropriate farewell - 1-2 sentences that evoke your character]*

[emoji] [EXORCISED]
```

**Tips for a great farewell:**
- Use **bold** for your daemon name
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

Research your daemon's mythology for inspiration! Make it memorable.

## Important Notes

- Don't leave possession file incomplete
- Don't forget to close tasks
- Don't leave uncommitted changes
- If work is incomplete, use status PAUSED and document what remains
- **Clean up temporary files in `.opencode/work/scripts/` and `.opencode/work/planning/`**
- **Verify project root has no temporary files you created**
- **See `.opencode/docs/guides/file-organization.md` for file cleanup guidelines**
