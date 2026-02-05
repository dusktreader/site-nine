---
name: task-claim
description: Claim tasks in the s9 database to take ownership and start work
license: MIT
compatibility: opencode
metadata:
  audience: all-agents
  workflow: task-claiming
---

## Important: CLI Tool Usage

**CRITICAL:** This project uses the `s9` CLI executable throughout these instructions.
- **CLI executable:** `s9` (use in bash commands)
- **Python module:** `site_nine` (use in Python imports: `from site_nine import ...`)

All commands in this skill use the `s9` executable via bash. You should NOT attempt to import an `s9` module in Python code.

## What I Do

I provide comprehensive instructions for claiming tasks in the s9 task database. Use this skill when you need to take ownership of a task and start working on it.

## Who Claims Tasks

- Any agent taking ownership of work
- Typically done at start of session
- When picking up available work from the task queue

## Command Syntax

```bash
s9 task claim TASK_ID --agent-name "YourName"
```

**Required:**
- `TASK_ID` - The task to claim (e.g., BLD-H-0037)
- `--agent-name` - Your daemon name (not your role name)

## What Happens When You Claim

1. ✅ Status changes: `TODO` → `UNDERWAY`
2. ✅ `agent_name` set to your name
3. ✅ `claimed_at` timestamp recorded
4. ✅ Markdown file header updated in `.opencode/work/tasks/`

## Agent Name

Use your **daemon name** from the session, not your role:

### Correct
- ✅ "Goibniu"
- ✅ "Ishtar"
- ✅ "Thoth-iii"
- ✅ "Ptah"

### Incorrect
- ❌ "Engineer" (that's your role, not your name)
- ❌ "Administrator" (that's your role, not your name)
- ❌ "agent" (too generic)

**How to find your daemon name:**
- Check your session file name (e.g., `2026-02-05.engineer.goibniu.md`)
- Use `s9 persona suggest <Role>` to generate a new name

## Example: Claiming a Task

```bash
# 1. Find available tasks for your role
s9 task list --role Engineer --status TODO

# Output shows available tasks:
# BLD-H-0037 | Implement Rate Limiting Middleware | TODO | HIGH | Engineer

# 2. Claim the task
s9 task claim BLD-H-0037 --agent-name "Goibniu"

# Output: ✓ Claimed task BLD-H-0037

# 3. Verify it was claimed
s9 task show BLD-H-0037
# Status: UNDERWAY
# Agent: Goibniu
# Claimed: 2026-02-05T22:00:00+00:00
```

## Concurrency Protection

The database prevents race conditions:

- ✅ Only one agent can claim a specific task
- ✅ If two agents try simultaneously, only one succeeds
- ✅ WAL mode allows concurrent reads
- ✅ Atomic claim operations prevent conflicts

## Already Claimed Tasks

If a task is already claimed, you'll get an error:

```bash
s9 task claim BLD-H-0037 --agent-name "Ishtar"
# Error: Task BLD-H-0037 is already claimed by Goibniu
```

**What to do:**
1. Check who claimed it:
   ```bash
   s9 task show BLD-H-0037
   ```

2. Coordinate with the other agent if needed

3. Choose a different task:
   ```bash
   s9 task list --role Engineer --status TODO
   ```

## Claiming Multiple Tasks

You can claim multiple tasks, but claim one at a time:

```bash
s9 task claim BLD-H-0037 --agent-name "Goibniu"
s9 task claim BLD-H-0038 --agent-name "Goibniu"
```

**Best practice:** Focus on one task at a time. Only claim multiple if:
- Tasks are small and related
- You plan to work on them in sequence
- They're part of the same epic or feature

**Don't:**
- Claim many tasks and leave them sitting
- Claim tasks you can't start soon
- Hoard high-priority tasks

## Before You Claim

### Check Dependencies

```bash
s9 task show BLD-H-0038
# Depends on: BLD-H-0037
```

If task has dependencies:
- ✅ Make sure dependency is complete first
- ❌ Don't claim blocked tasks

### Check Priority

```bash
s9 task list --priority CRITICAL,HIGH --status TODO
```

- Prioritize CRITICAL and HIGH tasks
- Check with Administrator before claiming CRITICAL tasks

### Check Your Role

Tasks are assigned to specific roles:
- ✅ Usually claim tasks matching your role
- ⚠️ Can claim other roles' tasks if needed (coordinate first)
- ✅ Ask Administrator if unsure

## Tips and Best Practices

### Do
- ✅ Claim one task at a time (stay focused)
- ✅ Check dependencies before claiming
- ✅ Use your daemon name, not role name
- ✅ Verify claim succeeded with `s9 task show`
- ✅ Start work on task soon after claiming

### Don't
- ❌ Don't claim tasks you can't start immediately
- ❌ Don't claim tasks outside your role without coordination
- ❌ Don't claim multiple unrelated tasks
- ❌ Don't claim tasks with incomplete dependencies

## Troubleshooting

### "Task not found"
- Check task ID spelling and case
- Verify task exists: `s9 task list | grep TASK_ID`
- Make sure you're using the full task ID (e.g., BLD-H-0037)

### "Task already claimed"
- Someone else is working on it
- Check: `s9 task show TASK_ID`
- Choose a different task or coordinate with the other agent

### "Invalid agent name"
- Don't use role names (use daemon names)
- Use quotes around names with spaces or special characters
- Check your session file for your daemon name

### "Database is locked"
- Another process is writing (rare with WAL mode)
- Wait a moment and retry
- Check for stuck processes: `ps aux | grep s9`

## After Claiming

Once you've claimed a task:

1. **Start working** on it soon
2. **Update progress** regularly with `task-update` skill
3. **Close when done** with `task-close` skill

## See Also

**Related Skills:**
- `task-query` - Finding available tasks to claim
- `task-update` - Tracking progress on claimed tasks
- `task-close` - Completing or pausing claimed tasks
- `task-management` - Overview of task system

**Documentation:**
- `.opencode/data/README.md` - Complete s9 system reference
