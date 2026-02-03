---
name: handoff-workflow
description: Hand off work to another agent with full context and documentation
license: MIT
compatibility: opencode
metadata:
  audience: all-agents
  workflow: agent-handoff
---

## Important: CLI Tool Usage

**CRITICAL:** This project uses the `s9` CLI executable throughout these instructions.
- **CLI executable:** `s9` (use in bash commands)
- **Python module:** `site_nine` (use in Python imports: `from site_nine import ...`)

All commands in this skill use the `s9` executable via bash. You should NOT attempt to import an `s9` module in Python code.

## What I Do

I guide you through creating a comprehensive handoff document when transitioning work between agents:

1. Identify current agent role and name
2. Determine target agent role
3. Gather current state (git status, active tasks, recent work)
4. Create structured handoff document with full context
5. Save handoff as `.pending.md` file
6. Provide instructions for recipient agent

This ensures smooth transitions between agents with no loss of context.

## When to Use Me

Use this skill when:
- ✅ User types `/handoff [Role]`
- ✅ Administrator delegates work to another agent
- ✅ User says "hand off to Builder/Tester/etc."
- ✅ You're done with your part and someone else needs to continue
- ✅ Context needs to be preserved for next agent

Don't use when:
- ❌ You're ending the entire session (use `/dismiss` instead)
- ❌ Just taking a short break
- ❌ No specific next agent needed

## Prerequisites

Before starting, ensure:
- You know your current role and daemon name
- You know which role you're handing off to
- You have context about what was done and what's next
- Current session file exists

## Step-by-Step Instructions

### Step 1: Identify Current Agent

Determine your current role and name from the session file.

**Find your session file:**
```bash
# List recent session files
ls -t .opencode/work/sessions/*.md | head -5

# Or find by your daemon name
ls .opencode/work/sessions/*your-name*.md
```

**Extract role and name:**
- From filename: `2026-01-29.16:00:00.manager.ishtar.task-name.md`
- Role: `manager`
- Name: `ishtar`

**If you don't have a session file yet:**
- Use `/summon` first to create a proper session
- Or determine role from context (what role user asked you to be)

### Step 2: Determine Target Agent Role

Ask the Director if not specified:

**If user said: `/handoff Builder`**
- Target role: Builder
- Target name: Any Builder agent (to be determined by `/summon`)

**If user said: `/handoff`**
- Ask: "Which agent role should I hand off to?"
- Options: Administrator, Architect, Builder, Tester, Documentarian, Designer, Inspector, Operator

**Common handoff patterns:**
- Administrator → Builder (implement)
- Administrator → Architect (design)
- Builder → Tester (validate)
- Tester → Builder (fix bugs)
- Builder → Inspector (review)
- Inspector → Documentarian (document)
- Architect → Builder (implement design)

### Step 3: Gather Current State

Collect information about current work state.

#### A. Git Status

```bash
# Check for uncommitted changes
git status

# Get current branch
git branch --show-current

# Recent commits (last 5)
git log --oneline -5 --pretty=format:"%h - %s"
```

**Capture:**
- Current branch name
- Number of uncommitted files
- List of modified files
- Recent commit messages

#### B. Active Tasks

```bash
# Check for tasks claimed by you
s9 task mine --agent-name "YourName"

# Show task details
s9 task show TASK_ID
```

**Capture:**
- Task IDs you're working on
- Task status and progress
- Remaining work

#### C. Recent Work Summary

From your session file, identify:
- What you've accomplished today
- Key files you modified
- Decisions you made
- Problems encountered

Read your session file to extract this context.

### Step 4: Determine Next Steps

Based on the current state, identify what the next agent needs to do.

**Questions to answer:**
- What is the primary task for next agent?
- Which task ID should they claim?
- What files do they need to review?
- What approach should they take?
- Are there any constraints or gotchas?
- What's the estimated effort?

**If unclear:**
- Ask the Director: "What should the [Role] agent focus on?"
- Review task descriptions for guidance
- Check project planning docs for next steps

### Step 5: Create Handoff Document

Generate handoff document using the template.

**Filename format:**
```
.opencode/work/sessions/handoffs/YYYY-MM-DD.HH:MM:SS.from-role-name.to-role.pending.md
```

**Example:**
```
.opencode/work/sessions/handoffs/2026-01-29.16:30:00.manager-ishtar.builder.pending.md
```

**Use the template at:** `.opencode/templates/handoff-template.md`

**Fill in all sections:**

1. **Header:** From/To roles, date, status
2. **Context:** What was done, current state, files to review
3. **What You Need to Do:** Primary task, approach, constraints
4. **Important Context:** Related work, gotchas, questions
5. **Acceptance Criteria:** Checklist for completion
6. **Next Steps:** Numbered list of actions
7. **Contact:** Links to session files and task details

**Write the file:**
```bash
# Create the handoff file
# (Use Write tool to create the file with filled template)
```

### Step 6: Update Current Session File

Add handoff information to your session file.

**In the "Work Log" or "Outcomes" section, add:**

```markdown
## Handoff

**Date:** 2026-01-29 16:30:00
**To:** Builder
**Document:** `.opencode/work/sessions/handoffs/2026-01-29.16:30:00.manager-ishtar.builder.pending.md`

**Summary:** Handed off task H040 (database query caching) to Builder agent. All planning complete, ready for implementation.

**Next Agent Should:**
1. Use `/summon` to start Builder session
2. Read handoff document
3. Claim task H040
4. Begin implementation
```

### Step 7: Confirm Handoff Created

Tell the Director the handoff is ready:

```
✅ Handoff created successfully!

**From:** Administrator (Ishtar)
**To:** Builder (any)
**Created:** 2026-01-29 16:30:00

**Handoff Document:**
.opencode/work/sessions/handoffs/2026-01-29.16:30:00.manager-ishtar.builder.pending.md

**Summary:**
- Task: H040 - Implement database query caching
- Priority: HIGH
- Estimated: 4-6 hours
- Files to review: 4 files
- Context: Full planning complete, ready for implementation

**For Next Agent:**
When the Builder agent starts with `/summon`, they'll be notified of this pending handoff.
```

Show them the key points from the handoff.

### Step 8: Add Mythological Signoff

**IMPORTANT:** After the handoff summary, add a mythologically appropriate farewell that matches your daemon name's mythology. This signoff is the Director's visual indicator that they can close the session.

Use the same format as described in the session-end skill:

```markdown
Thank you for the session! I'm <Name>, handing off now.

[Mythologically appropriate farewell - 1-2 sentences in italics]
```

**Examples by mythology:**

**Egyptian (Anubis, Thoth, Set):**
- *My judgment rendered, I return to the halls of Ma'at where the scales of truth are weighed...*
- *The scribe's papyrus is sealed. I fade into the eternal sands of time...*

**Norse (Loki, Hel, Bragi):**
- *The trickster's work is done. I slip back through the roots of Yggdrasil...*
- *My saga complete, I return to the mead halls of Asgard where tales are sung...*

**Greek/Roman (Athena, Hephaestus, Thanatos):**
- *Wisdom's task fulfilled, I ascend back to Olympus where strategy is eternal...*
- *The forge cools, my craft complete. I descend once more to the depths of Hephaestus...*

**Make it personal to your specific daemon!**

**Complete example:**
```
✅ Handoff created successfully!

**From:** Administrator (Ishtar)
**To:** Builder (any)
**Created:** 2026-01-29 16:30:00

**Handoff Document:**
.opencode/work/sessions/handoffs/2026-01-29.16:30:00.manager-ishtar.builder.pending.md

**Summary:**
- Task: H040 - Implement database query caching
- Priority: HIGH
- Estimated: 4-6 hours

Thank you for the session! I'm Ishtar, handing off now.

*My battle plans drawn, I return to the celestial palace where love and war intertwine. Until the next campaign calls...*
```

**This mythological signoff serves as the Director's visual confirmation that the handoff is complete and they can safely close the session.**

## Important Notes

### About Handoff Files

- **File naming:** Must include timestamp, from-role-name, to-role, and `.pending.md` suffix
- **Location:** Always in `.opencode/work/sessions/handoffs/` directory
- **Status suffix:**
  - `.pending.md` - Created, waiting for recipient
  - `.accepted.md` - Recipient started and acknowledged
  - `.completed.md` - Recipient finished the work
- **Git tracking:** Handoff files are committed to git for history

### About Handoff Content

- **Be specific:** Include file paths, line numbers, task IDs
- **Provide context:** Explain WHY not just WHAT
- **Anticipate questions:** Address potential confusion upfront
- **Set expectations:** Clear acceptance criteria and estimated effort
- **Link resources:** Session files, tasks, ADRs, planning docs

### About Target Agent

- **Target can be any agent with that role** - Don't specify a specific daemon name
- **Next agent chooses their own name** during `/summon`
- **Role matters more than identity** - Focus on what needs to be done, not who does it

### About Handoff Lifecycle

**Creation (this skill):**
1. Current agent creates `.pending.md` handoff
2. Updates their session file with handoff info
3. Can continue working or use `/dismiss`

**Acceptance (in `/summon` skill):**
1. Next agent runs `/summon` and chooses role
2. System checks for pending handoffs for that role
3. Agent reads handoff and marks as `.accepted.md`
4. Agent starts work

**Completion (in `/dismiss` skill):**
1. Agent finishes work from handoff
2. Uses `/dismiss` to end session
3. System marks handoff as `.completed.md`
4. Completion recorded in session file

### Common Scenarios

**Administrator delegates implementation:**
```
Administrator completes planning → /handoff Builder → Builder implements
```

**Builder needs validation:**
```
Builder completes feature → /handoff Tester → Tester validates
```

**Tester finds bugs:**
```
Tester identifies issues → /handoff Builder → Builder fixes
```

**Builder needs review:**
```
Builder finishes code → /handoff Inspector → Inspector reviews
```

**Inspector identifies improvements:**
```
Inspector finds issues → /handoff Builder → Builder improves
```

## Troubleshooting

### "I don't have a session file"
- Run `/summon` first to create a session
- Or manually determine your role from context
- Session file is recommended but not strictly required

### "I don't know what to hand off"
- Check your active tasks: `s9 task mine --agent-name "YourName"`
- Review your recent commits: `git log -5`
- Read your session file for context
- Ask the Director: "What should I hand off to [Role]?"

### "Multiple pending handoffs exist"
- This is normal - multiple agents can have work ready
- `/summon` will show all pending handoffs for chosen role
- Next agent picks which one to accept

### "Target role unclear"
- Ask the Director which role should receive the handoff
- Consider the type of work: code → Builder, tests → Tester, docs → Documentarian
- Check WORKFLOWS.md for typical patterns

### "Not sure what to include"
- Use the template - it has all required sections
- Include: task ID, files to review, approach, constraints, acceptance criteria
- Better to over-document than under-document
- Future agent will appreciate the context

## Examples

### Example 1: Administrator → Builder (Feature Implementation)

**Context:** Administrator planned query caching feature, ready for Builder to implement.

```bash
# Step 3: Gather state
git branch --show-current
# feature/query-caching

git status
# On branch feature/query-caching
# nothing to commit

s9 task list --status TODO --role Builder
# H040 - Implement database query caching (TODO)

# Step 5: Create handoff
# File: .opencode/work/sessions/handoffs/2026-01-29.16:30:00.manager-ishtar.builder.pending.md
# (Full content using template, specifying task H040, approach, files, etc.)

# Step 6: Update session file
# Added handoff section to current session

# Step 7: Confirm
"✅ Handoff created for Builder to implement H040"
```

### Example 2: Builder → Tester (Feature Validation)

**Context:** Builder implemented feature, needs Tester validation.

```bash
# Step 3: Gather state
git status
# 3 files changed, 1 file staged for commit

git log -1
# feat(database): implement query caching [Agent: Builder - Goibniu]

s9 task show H040
# Status: UNDERWAY, 90% complete

# Step 5: Create handoff
# File: .opencode/work/sessions/handoffs/2026-01-29.18:45:00.builder-goibniu.tester.pending.md
# Context: Feature implemented, all unit tests passing, needs integration testing

# Step 6: Update session
# Added handoff to session file

# Step 7: Confirm
"✅ Handoff created for Tester to validate query caching feature"
```

### Example 3: Tester → Builder (Bug Fixes)

**Context:** Tester found 2 bugs, needs Builder to fix.

```bash
# Step 3: Gather state
git status
# On branch feature/query-caching
# nothing to commit

s9 task show H040
# Status: REVIEW

# Step 4: Identify issues
# Bug 1: Cache not respecting investigation locks
# Bug 2: TTL not configurable via environment

# Step 5: Create handoff
# File: .opencode/work/sessions/handoffs/2026-01-29.19:30:00.tester-eris.builder.pending.md
# Lists 2 specific bugs with file locations and reproduction steps

# Step 7: Confirm
"✅ Handoff created for Builder to fix 2 bugs in query caching"
```

## Quick Reference

**Full workflow:**
```bash
# 1. Check current state
git status
git branch --show-current
s9 task mine --agent-name "YourName"

# 2. Determine target role
# (User specifies or you ask)

# 3. Create handoff file
# Use template: .opencode/templates/handoff-template.md
# Filename: YYYY-MM-DD.HH:MM:SS.from-role-name.to-role.pending.md
# Location: .opencode/work/sessions/handoffs/

# 4. Update session file
# Add handoff section with date, target, summary

# 5. Confirm to user
# Show handoff location and summary
```

**Handoff filename format:**
```
YYYY-MM-DD.HH:MM:SS.from-role-name.to-role.pending.md
```

**Status transitions:**
```
.pending.md   → Created, waiting for recipient
.accepted.md  → Recipient acknowledged
.completed.md → Work finished
```

## See Also

- `.opencode/commands/handoff.md` - Handoff command
- `.opencode/skills/session-start/SKILL.md` - Receiving handoffs in `/summon`
- `.opencode/skills/session-end/SKILL.md` - Completing handoffs in `/dismiss`
- `.opencode/templates/handoff-template.md` - Handoff document template
- `.opencode/docs/procedures/WORKFLOWS.md` - Common multi-agent patterns
- `.opencode/work/sessions/README.md` - Session file format
