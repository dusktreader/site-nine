---
name: task-claim
description: Claim tasks in the s9 database to take ownership and start work
license: MIT
compatibility: opencode
metadata:
  audience: all-agents
  workflow: task-claiming
---

## What I Do

> **⛔ AGENTS: NEVER USE THE `s9` CLI ⛔**
>
> The `s9` command is **for the Director (human) only**. Any `s9` bash snippets in this skill are legacy
> references. **Do not run them.** Use the designated OpenCode tools: `task_claim`, `task_show`, `task_list`.

I provide comprehensive instructions for claiming tasks in the s9 task database using the `task_claim` tool. Use this skill when you need to take ownership of a task and start working on it.

## Who Claims Tasks

- Any agent taking ownership of work
- Typically done at start of session
- When picking up available work from the task queue

## Tool Syntax

Invoke the `task_claim` tool with the task ID:

```
Invoke task_claim tool with task_id="TASK_ID"
```

**Required:**
- `task_id` - The task to claim (e.g., "ENG-H-0037")

**Automatic:**
- Mission ID - Retrieved automatically from your current session context
- Role - Retrieved automatically from your mission record

The tool automatically determines your mission ID and role from the current OpenCode session, so you don't need to provide them manually.

## What Happens When You Claim

1. ✅ Status changes: `TODO` → `UNDERWAY`
2. ✅ `mission_id` set to your mission ID (retrieved automatically from session)
3. ✅ `claimed_at` timestamp recorded
4. ✅ Markdown file header updated in `.opencode/work/tasks/`

## Example: Claiming a Task

Finding and claiming a task:

1. **Find available tasks** using the `task_show` tool:
   ```
   task_show({ role: "Engineer", status: "TODO" })
   ```

2. **Invoke the task_claim tool** with the task ID:
   ```
   Invoke task_claim tool with task_id="ENG-H-0037"
   ```

   The tool will:
   - Automatically retrieve your mission ID from the current session
   - Automatically retrieve your role from your mission record
   - Claim the task and update its status to UNDERWAY
   - Return confirmation that the task was claimed

3. **Verify the claim** using the `task_show` tool:
   ```
   task_show({ task_id: "ENG-H-0037" })
   ```
   Output will show:
   ```
   Status: UNDERWAY
   Mission: [your-mission-id]
   Claimed: [timestamp]
   ```

## Concurrency Protection

The database prevents race conditions:

- ✅ Only one agent can claim a specific task
- ✅ If two agents try simultaneously, only one succeeds
- ✅ WAL mode allows concurrent reads
- ✅ Atomic claim operations prevent conflicts

## Already Claimed Tasks

If a task is already claimed, the tool will return an error:

```
Error: Task ENG-H-0037 is already claimed by mission 42
```

**What to do:**
1. Check which mission claimed it using the `task_show` tool:
   ```
   task_show({ task_id: "ENG-H-0037" })
   ```

2. Coordinate with the other mission/agent if needed

3. Choose a different task and invoke the tool again with the new task ID

## Claiming Multiple Tasks

You can claim multiple tasks by invoking the tool multiple times:

```
Invoke task_claim tool with task_id="ENG-H-0037"
Invoke task_claim tool with task_id="ENG-H-0038"
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

Use the `task_show` tool to check dependencies:
```
task_show({ task_id: "ENG-H-0038" })
# Check the "dependencies" field
```

If task has dependencies:
- ✅ Make sure dependency is complete first
- ❌ Don't claim blocked tasks

### Check Priority

Use the `task_show` tool to find high-priority work:
```
task_show({ priority: "CRITICAL,HIGH", status: "TODO" })
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
- ✅ Use the `task_claim` tool to claim tasks
- ✅ Verify claim succeeded by checking tool output or calling `task_show`
- ✅ Start work on task soon after claiming

### Don't
- ❌ Don't claim tasks you can't start immediately
- ❌ Don't claim tasks outside your role without coordination
- ❌ Don't claim multiple unrelated tasks
- ❌ Don't claim tasks with incomplete dependencies

## Troubleshooting

### "Task not found"
- Check task ID spelling and case
- Verify task exists using `task_show` tool: `task_show({ task_id: "TASK_ID" })`
- Make sure you're using the full task ID (e.g., "ENG-H-0037")

### "Task already claimed"
- Someone else is working on it
- Check using `task_show` tool: `task_show({ task_id: "TASK_ID" })`
- Choose a different task or coordinate with the other mission

### "No active mission found"
- The tool cannot find your mission from the session context
- Make sure you initialized your mission with the `mission-start` skill
- Contact the Director if your mission appears to be corrupted

### "Role mismatch"
- Your role doesn't match the task's assigned role
- Check task details using `task_show` tool: `task_show({ task_id: "TASK_ID" })`
- Either claim a task for your role, or coordinate with Administrator

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
