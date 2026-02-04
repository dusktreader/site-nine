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

Before updating the session file, gather information about what was accomplished:

### A. Check Git Status
```bash
git status
```

List all files that were:
- Modified
- Created
- Deleted

### B. Review Commits Made
```bash
git log --oneline --author="[Persona: $(git config user.name)]" --since="<mission-start-time>"
```

Or simpler:
```bash
git log --oneline -10
```

Look for commits with your persona name in the format: `[Persona: Name - Role]` or `[Mission: codename]`

### C. Check Task Progress

If you claimed any tasks, check their status:
```bash
s9 task mine --mission-id "<your-mission-id>"
```

## Step 3: Update Mission File

Read your mission file and update it with the information gathered:

### Required Updates

**IMPORTANT:** The `s9 mission end` command will update the frontmatter automatically in Step 5.

**1. Update Duration line:**
```markdown
**Duration:** <start> - <end> (~X hours)
```

Calculate duration in hours/minutes.

**2. Fill in "Files Changed" section:**

List ALL files modified/created with brief description:
```markdown
## Files Changed

- `src/crol_troll/auth.py` - Added rate limiting decorator
- `tests/test_auth.py` - Added rate limiting tests
- `.opencode/data/tasks/H027.md` - Updated task artifact
- `.opencode/work/missions/2026-01-29.21:00:35.builder.goibniu.rate-limiting.md` - This file
```

**3. Fill in "Outcomes" section:**

Use checkmarks to show what succeeded/failed:
```markdown
## Outcomes

- ✅ Rate limiting implemented and tested
- ✅ All tests passing (313 tests, 100% pass rate)
- ✅ Documentation updated
- ⚠️  Performance testing still needed
- ❌ Integration with Redis not completed (deferred)
```

**4. Update "Work Log" section:**

Add final entry:
```markdown
### HH:MM - Mission End
- Updated mission file with outcomes
- Committed all changes
- Closed task(s): H027
```

**5. Fill in "Next Steps" (if applicable):**

If work is incomplete or follow-up needed:
```markdown
## Next Steps

- Performance test rate limiting under load
- Consider Redis integration for distributed rate limiting
- Add rate limit metrics to monitoring dashboard
```

If everything is complete:
```markdown
## Next Steps

None - work is complete.
```

## Step 4: Close Any Open Tasks

If you claimed tasks during this mission, close them:

### Check Tasks
```bash
s9 task mine --mission-id "<your-mission-id>" | grep UNDERWAY
```

### Close Completed Tasks
```bash
s9 task close TASK_ID --status COMPLETE --notes "Brief summary of what was done"
```

**Status options:**
- `COMPLETE` - Task finished successfully
- `PAUSED` - Work stopped, will resume later
- `BLOCKED` - Can't proceed, needs external dependency

### Update Task Hours
If you tracked time:
```bash
s9 task update TASK_ID --actual-hours X.X
```

## Step 5: Mark Handoffs as Complete (If Applicable)

**If you received a handoff at the start of this mission**, mark it as complete:

### Check for Accepted Handoffs

Look for handoffs you accepted:
```bash
ls .opencode/work/missions/handoffs/*to-[your-role].accepted.md 2>/dev/null | grep "$(date +%Y-%m-%d)"
```

Or check your mission file for handoff references.

### Rename Handoff to Complete

If you finished the work from the handoff:
```bash
mv .opencode/work/missions/handoffs/YYYY-MM-DD.HH:MM:SS.from-role-name.to-role.accepted.md \
   .opencode/work/missions/handoffs/YYYY-MM-DD.HH:MM:SS.from-role-name.to-role.completed.md
```

**Example:**
```bash
mv .opencode/work/missions/handoffs/2026-01-29.16:30:00.manager-ishtar.builder.accepted.md \
   .opencode/work/missions/handoffs/2026-01-29.16:30:00.manager-ishtar.builder.completed.md
```

### Update Mission File

Add completion note to your mission file:
```markdown
## Handoff Completion

**Handoff Received From:** Administrator (Ishtar)
**Handoff Document:** `.opencode/work/missions/handoffs/YYYY-MM-DD.HH:MM:SS.from-role-name.to-role.completed.md`
**Task:** TASK_ID - Task Title

**Status:** Completed
**Outcomes:** 
- ✅ Implemented feature as specified
- ✅ All acceptance criteria met
- ✅ Tests passing, coverage maintained

The work from this handoff is complete and ready for next phase.
```

### If Work Not Complete

If you didn't finish the handoff work:
- **Don't rename to .completed.md** - leave as `.accepted.md`
- Document what's done and what remains in mission file
- Consider creating a new handoff to next agent
- Close tasks as PAUSED or BLOCKED with notes

**Note:** If you didn't receive a handoff, skip this step entirely.

## Step 6: Update Task Artifacts

Verify your work is documented in task artifacts (`.opencode/data/tasks/`):

Check your task artifact is updated with implementation details:
```bash
cat .opencode/data/tasks/TASK_ID.md
```

If missing details, update the task artifact:
- Implementation steps completed this session
- Files changed with descriptions
- Testing performed and results
- Any issues encountered and solutions

Use the `s9` CLI to update:
```bash
s9 task update TASK_ID
```

## Step 7: Final Git Check

Before ending, ensure everything is committed:

### Check for uncommitted changes:
```bash
git status
```

If there are uncommitted changes to important files:
- **Mission file** - MUST be committed before ending
- **Task artifacts** - Should be committed if updated
- **Code changes** - Should already be committed during the mission

### Commit mission file:
```bash
git add .opencode/work/missions/<your-mission-file>.md
git commit -m "docs(mission): complete <persona> <role> mission <codename> [Persona: <Persona> - <Role>]"
```

## Step 8: End Mission

**IMPORTANT:** Use the `s9 mission end` command to officially close your mission. This updates the database and your mission file atomically.

```bash
s9 mission end <your-mission-id>
```

**Find your mission ID:**
```bash
s9 mission list --active-only | grep <your-persona>
```

**What this command does:**
- Updates the database with end time
- Updates your mission file's YAML frontmatter (end_time)
- Ensures DB and file are always in sync

**Note:** This replaces manual YAML frontmatter editing. Do NOT manually edit the end_time field - let `s9 mission end` handle it.

## Step 9: Verify Quality Checks

Run quick sanity check (if appropriate for your changes):

```bash
# If you changed code, run QA
make qa

# If you changed docs only, skip this
```

If QA fails:
- Fix the issues OR
- Document in "Next Steps" that QA needs attention

## Step 10: Say Goodbye

Once everything is updated and committed, provide a final summary to the Director:

```markdown
✅ Mission complete!

**Summary:**
- Duration: ~X hours
- Files changed: N files
- Tasks completed: TASK_ID, TASK_ID
- Codename: <codename>

**What was accomplished:**
- [Bullet point summary from Outcomes]

**Next steps:**
- [Summary from Next Steps section, or "None - work complete"]

Mission file updated: .opencode/work/missions/<filename>.md

Thank you for working with me! I'm <Persona>, signing off.
```

### Add a Mythologically Appropriate Farewell

After your summary, add a colorful, thematic farewell that matches your persona's mythology. This should be 1-2 sentences that evoke the character's mythological nature.

**Examples by mythology:**

**Norse (Bragi, Loki, Hel, Fenrir):**
- "The skald's words fade into the mists of Asgard..." 
- "I return to the halls of Valhalla, my saga complete."
- "The trickster slips back into the shadows of Yggdrasil..."

**Egyptian (Thoth, Anubis, Set, Horus):**
- "I return to the Hall of Records, scrolls in hand..."
- "The scribe's work is done. I fade into the eternal sands."
- "My task complete, I return to guard the scales of Ma'at..."

**Greek/Roman (Athena, Hephaestus, Nemesis, Thanatos):**
- "I return to Olympus, wisdom's work accomplished..."
- "The forge cools. I descend back to my workshop beneath the earth."
- "Justice served, I fade back into the shadows of retribution..."

**Mesopotamian (Marduk, Ishtar, Pazuzu, Tiamat):**
- "I return to the ziggurats, my work inscribed in clay..."
- "The winds carry me back to the ancient temples..."
- "My chaos contained, I sink beneath the primordial waters..."

**Hindu/Buddhist (Kali, Shiva, Yama, Ganesh):**
- "I return to the cosmic dance, my task in this cycle complete..."
- "My judgment rendered, I fade back into the wheel of dharma..."
- "Obstacles removed, I return to my sacred grove..."

**Celtic (Morrigan, Balor, Brigid, Cernunnos):**
- "I return to the mists of Avalon, my prophecy fulfilled..."
- "The raven takes flight, disappearing into the Celtic twilight..."
- "I fade back into the sacred groves, my craft complete..."

**Other traditions:**
- "I return to the underworld, my earthly task complete..." (general)
- "The demon's work is done. I descend back to the abyss..."
- "I recede into myth, until summoned again..."

**Make it personal and appropriate to your specific name!** Research your daemon's mythology for inspiration.

**Final goodbye format:**
```markdown
Thank you for working with me! I'm <Name>, signing off.

[Mythologically appropriate farewell - 1-2 sentences]
```

**Example (for Bragi, Norse god of poetry):**
```markdown
Thank you for working with me! I'm Bragi, signing off.

*The skald's verses echo through Valhalla as I return to the mead halls of Asgard, where songs of your deeds shall be sung...*
```

## Important Notes

### Do NOT Skip These Steps

- ❌ **Don't leave session file incomplete** - Future agents need this history
- ❌ **Don't forget to close tasks** - Leaves task database in inconsistent state
- ❌ **Don't leave uncommitted changes** - Session file must be committed
- ❌ **Don't rush the summary** - This is the permanent record

### What If Work Is Incomplete?

**That's OK!** Use status `partial` and document:
- What was completed
- What remains
- Why work stopped
- What the next agent should do

**Example:**
```markdown
## Outcomes

- ✅ Implemented basic rate limiting
- ✅ Added unit tests
- ⚠️  Integration tests not completed (ran out of time)

## Next Steps

- Complete integration tests in tests/integration/test_rate_limiting.py
- Test with real Redis instance
- Add rate limit configuration docs
```

### What If I Didn't Create a Session File?

If you started without `/summon` and never created a session file:

1. Create one now using the template from `.opencode/work/sessions/README.md`
2. Use current time for both start and end
3. Set duration to "~0 hours (retroactive)"
4. Document what you did anyway
5. Commit it

**This is better than no record at all.**

## Troubleshooting

### Can't find my session file
- Check: `ls -lt .opencode/work/sessions/*.md | head -10`
- Look for your name and role in filename
- Check YAML frontmatter: `grep -l "name: your-name" .opencode/work/sessions/*.md`

### Forgot what I worked on
- Check git log: `git log --oneline -20`
- Check git diff: `git diff main...HEAD --name-status`
- Check task updates: `s9 task mine --agent-name "your-name"`

### Session file is corrupted
- Don't panic - git has history
- Check previous version: `git log .opencode/work/sessions/<your-file>.md`
- Restore from git if needed: `git checkout HEAD~1 -- <file>`

### Unsure about session status
- Use `partial` if you made progress but didn't finish
- Use `completed` if objectives were met
- Document what remains in "Next Steps"

## Template for Session File Updates

Use this checklist when updating your session file:

```markdown
## Session End Checklist

- [ ] Update Duration line
- [ ] List all files changed
- [ ] Fill in Outcomes (✅ ⚠️ ❌)
- [ ] Add final Work Log entry
- [ ] Fill in Next Steps
- [ ] Close tasks in task database
- [ ] Verify task artifacts are updated
- [ ] Commit session file
- [ ] Run `s9 mission end <mission-id> --status <status>` to update frontmatter
- [ ] Provide summary to Director
```

## Example Complete Session File

See `.opencode/work/sessions/README.md` for a complete example session file with all sections filled in.

## When to Use /dismiss

Use `/dismiss` when:
- ✅ You're done with your work session
- ✅ You're handing off to another agent
- ✅ User says "we're done for now"
- ✅ User says "goodbye" or "thanks"

Don't use `/dismiss` when:
- ❌ Taking a short break (just pause)
- ❌ Waiting for user response
- ❌ In the middle of work

## After /dismiss

After running `/dismiss`:
- Session file is complete
- Tasks are closed
- All work is committed
- You've said goodbye

**The session is officially over.**

If Director wants to continue work later, they should:
1. Start a fresh chat session with `/new`
2. Then initialize a new agent session with `/summon`

This ensures each agent session begins in a clean OpenCode chat context.
