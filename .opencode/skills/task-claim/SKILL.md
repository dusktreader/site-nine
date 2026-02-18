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
s9 task claim TASK_ID --mission MISSION_ID --role ROLE
```

**Required:**
- `TASK_ID` - The task to claim (e.g., ENG-H-0037)
- `--mission` or `-m` - Your mission ID (from `s9 mission start`)
- `--role` or `-r` - Your role (must match task's assigned role)

## What Happens When You Claim

1. ✅ Status changes: `TODO` → `UNDERWAY`
2. ✅ `mission_id` set to your mission ID
3. ✅ `claimed_at` timestamp recorded
4. ✅ Markdown file header updated in `.opencode/work/tasks/`

## Mission ID

Use your **mission ID** from your current mission:

**How to find your mission ID:**
- It was displayed when you ran `s9 mission start`
- Check `s9 mission list` to see your active missions
- Look for the mission number (e.g., mission #42)

**Note:** You must have an active mission to claim tasks. If you don't have one, start a mission first with `s9 mission start`.

## Example: Claiming a Task

```bash
# 1. Find available tasks for your role
s9 task list --role Engineer --status TODO

# Output shows available tasks:
# ENG-H-0037 | Implement Rate Limiting Middleware | TODO | HIGH | Engineer

# 2. Claim the task (assuming mission ID is 42)
s9 task claim ENG-H-0037 --mission 42 --role Engineer

# Output: ✓ Claimed task ENG-H-0037

# 3. Verify it was claimed
s9 task show ENG-H-0037
# Status: UNDERWAY
# Mission: 42
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
s9 task claim ENG-H-0037 --mission 43 --role Engineer
# Error: Task ENG-H-0037 is already claimed by mission 42
```

**What to do:**
1. Check which mission claimed it:
   ```bash
   s9 task show ENG-H-0037
   ```

2. Coordinate with the other mission/agent if needed

3. Choose a different task:
   ```bash
   s9 task list --role Engineer --status TODO
   ```

## Claiming Multiple Tasks

You can claim multiple tasks, but claim one at a time:

```bash
s9 task claim ENG-H-0037 --mission 42 --role Engineer
s9 task claim ENG-H-0038 --mission 42 --role Engineer
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
s9 task show ENG-H-0038
# Depends on: ENG-H-0037
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
- ✅ Use your mission ID and role
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
- Make sure you're using the full task ID (e.g., ENG-H-0037)

### "Task already claimed"
- Someone else is working on it
- Check: `s9 task show TASK_ID`
- Choose a different task or coordinate with the other mission

### "Mission not found"
- Invalid mission ID provided
- Check your active mission: `s9 mission list`
- Make sure you started a mission first: `s9 mission start`

### "Role mismatch"
- Your role doesn't match the task's assigned role
- Check task details: `s9 task show TASK_ID`
- Either claim a task for your role, or coordinate with Administrator

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
