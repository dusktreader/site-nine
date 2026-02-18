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

All commands in this skill use the `s9` executable via bash. You should NOT attempt to import an
`s9` module in Python code.

## What I Do

I guide you through handing off work to another agent:

1. Identify the task being handed off (or create one if needed)
2. Determine the target agent role
3. Write a handoff document in `.opencode/work/handoffs/`
4. Register the handoff in the database via `s9 handoff create` (referencing the document)
5. Release the task so the next agent can claim it
6. Confirm to the Director

This ensures smooth transitions between agents with no loss of context.

## When to Use Me

Use this skill when:
- ✅ User types `/handoff [Role]`
- ✅ You're done with your part and someone else needs to continue
- ✅ Context needs to be preserved for the next agent

Don't use when:
- ❌ You're ending the entire session with no successor (use `/dismiss` instead)
- ❌ Just taking a short break

## About the Task Requirement

**Every handoff must be tied to a task.** This is how the receiving agent discovers the handoff via
`s9 handoff list`. The task model is:

- **If you have a task you're currently working on:** Hand off that task. It's `UNDERWAY` and
  not finished — the next agent picks it up and completes it.
- **If you're handing off new work (not your current task):** Create the task first
  (`s9 task create ...`), then hand it off.
- **If there is genuinely no task:** Create one. Work without a task is invisible to the system.

## Step-by-Step Instructions

### Step 1: Identify Your Mission and Task

```bash
# Find your mission ID
s9 mission list --status active

# Find tasks claimed by your mission
s9 task mine --mission <MISSION_ID>
```

If you don't have a task yet, create one:
```bash
s9 task create --title "..." --role [TargetRole] --priority HIGH
```

### Step 2: Determine Target Agent Role

**If user said: `/handoff Engineer`** (role argument provided)
- Target role: Engineer

**If user said: `/handoff`** (no argument)
- Default target role to your **current role**
- Inform the Director and proceed — no need to ask:
  ```
  No target role specified — defaulting to [YourRole] (same role as current agent).
  ```
- If the Director then specifies a different role, use that instead.

**Common handoff patterns:**
- Administrator → Engineer (implement)
- Administrator → Architect (design)
- Architect → Engineer (implement design)
- Engineer → Tester (validate)
- Tester → Engineer (fix bugs)
- Engineer → Inspector (review)

### Step 3: Write the Handoff Document

Write a detailed handoff document so the receiving agent has full context. This is required — the
DB record alone is not enough for a real handoff.

**Location:** `.opencode/work/handoffs/`

**Filename:** `<TASK-ID>-<your-role>-<your-name>-to-<target-role>.md`

**Example:** `.opencode/work/handoffs/ARC-H-0131-architect-atum-to-architect.md`

**Required sections:**

```markdown
# Handoff: <Brief title>

**From:** <Role> (<Name>) — Mission <codename> (#<id>)
**To:** <Role> (any)
**Task:** <TASK-ID> — <Task title>
**Date:** YYYY-MM-DD

---

## What Was Done

[What you accomplished. Be specific.]

---

## What You Need to Do

[Primary task. Clear, actionable steps.]

---

## Key Decisions / Context

[Decisions already made that the next agent should know about. Things that are not up for debate.
Gotchas, constraints, and things to watch out for.]

---

## Files to Read

| File | Why |
|------|-----|
| path/to/file | reason |

---

## Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2
```

### Step 4: Register the Handoff and Release the Task

Two commands are required. Both matter.

**4a. Register the handoff in the database** — this is how the receiving agent discovers it.
Pass the handoff document as a `--file` so it appears in `s9 handoff show`:

```bash
s9 handoff create \
  --task <TASK-ID> \
  --from-mission <MISSION-ID> \
  --to-role <Role> \
  --summary "<one or two sentence summary>" \
  --file ".opencode/work/handoffs/<filename>.md" \
  --criteria "<what defines completion>" \
  --notes "Read .opencode/work/handoffs/<filename>.md for full context."
```

**4b. Release the task** — sets it back to `TODO` and clears the mission assignment so the next
agent can claim it:

```bash
s9 task release <TASK-ID>
```

Without this step, the task remains `UNDERWAY` under your mission and the next agent cannot claim
it.

**Verify both:**
```bash
s9 handoff list
s9 task show <TASK-ID>   # should show status TODO, no mission assigned
```

### Step 5: Update Your Mission File

Add a handoff note to your mission file's Work Log section:

```markdown
### HH:MM - Handoff

- Registered handoff #<id> for task <TASK-ID> to <Role>
- Handoff document: .opencode/work/handoffs/<filename>.md
```

### Step 6: Confirm to the Director

```
✅ Handoff created!

**Handoff ID:** #<id>
**Task:** <TASK-ID> — <Task title>
**To:** <Role>
**Document:** .opencode/work/handoffs/<filename>.md

**Summary:** <What was handed off>

**Next Agent:** When the <Role> agent starts with `/summon`, they will see this handoff via
`s9 handoff list --role <Role>`.
```

### Step 7: Close the Mission

A handoff means your work on this mission is done. **You must now close your mission properly**
using the full session-end protocol. Load and execute the `session-end` skill:

```
My work is handed off. I will now close this mission using the session-end skill.
```

Then load the skill and follow all of its steps:

```
skill(name="session-end")
```

**Important notes for session-end after a handoff:**

- **Step 4 (Close Tasks):** Do NOT close the task you handed off — it was released back to TODO
  for the next agent. Only close tasks that are genuinely complete.
- **Step 5 (Mark Handoffs Complete):** Skip — you are the *sender*, not the receiver. The
  `s9 handoff delete` step is for the receiving agent.
- The mythological signoff from session-end's Step 11 replaces the standalone farewell that was
  previously in this skill.

## Handoff Lifecycle

**Creation (this skill):**
1. Current agent writes handoff document to `.opencode/work/handoffs/`
2. Current agent runs `s9 handoff create` — stored in database, document path in `--file`
3. Current agent runs `s9 task release` — task reset to TODO
4. Current agent updates mission file
5. Current agent loads `session-end` skill and closes their mission

**Discovery (in session-start skill, Step 8):**
1. Next agent runs `s9 handoff list --role [Role]`
2. Agent runs `s9 handoff show <id>` — sees document path in Relevant Files
3. Agent reads the handoff document
4. Agent claims the task: `s9 task claim <TASK-ID> --mission <id> --role <Role>`
5. Agent runs `s9 handoff delete <id>` to consume it

## Troubleshooting

### "I don't have a task"
Create one first. Every handoff needs a task.

```bash
s9 task create --title "..." --role [TargetRole] --priority HIGH --description "..."
```

### "The task is already DONE"
If you've fully completed your task and there's nothing to hand off, use `/dismiss` instead.
Handoffs are for work-in-progress, not completed work.

## Quick Reference

```bash
# 1. Find your mission and task
s9 mission list --status active
s9 task mine --mission <ID>

# 2. Write the handoff document
# Location: .opencode/work/handoffs/<TASK-ID>-<role>-<name>-to-<target-role>.md

# 3. Register the handoff (reference the document with --file)
s9 handoff create \
  --task <TASK-ID> \
  --from-mission <MISSION-ID> \
  --to-role <Role> \
  --summary "<summary>" \
  --file ".opencode/work/handoffs/<filename>.md" \
  --criteria "<done when...>" \
  --notes "Read .opencode/work/handoffs/<filename>.md for full context."

# 4. Release the task (unassign from your mission)
s9 task release <TASK-ID>

# 5. Verify
s9 handoff list
s9 task show <TASK-ID>   # should show TODO, no mission

# 6. Update mission file, confirm to Director
# 7. Load session-end skill and close your mission
```

## See Also

- `.opencode/skills/session-start/SKILL.md` — Step 8 shows how the receiving agent discovers handoffs
- `.opencode/docs/procedures/WORKFLOWS.md` — Common multi-agent patterns
