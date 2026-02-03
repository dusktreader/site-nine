# Command Fix Summary

## Problem

Agents were reading command documentation files instead of executing commands when invoked.

### Example Issue

```
User: .opencode/commands/summon.md
Agent: I'll read the summon command documentation for you.
→ Read .opencode/commands/summon.md 
This is the documentation for the /summon command...
```

## Root Cause

**The agent behavior was actually CORRECT** - it distinguished between:

1. **User types `/summon`** (command invocation)
   - OpenCode loads `summon.md` and passes it as a command
   - Agent should execute the session-start skill immediately

2. **User types `.opencode/commands/summon.md`** (documentation request)
   - User is asking to read that file path
   - Agent should read and explain the file

The confusion arose because command files didn't clearly handle both scenarios.

## Solution

Updated all command files to follow a dual-purpose pattern:

### New Command File Structure

```markdown
---
description: Command description
---

# /command-name Command

## If you are seeing this because the user typed `/command-name`:

**ACTION REQUIRED:** Execute the command immediately.

[Execution instructions]

---

## If you are seeing this because the user asked about the command:

[Documentation about what the command does]
```

### Benefits

- **Clear action directive** when invoked as a command
- **Helpful documentation** when read as a file
- **Distinguishes intent** between execution and documentation
- **Reduces agent confusion** about what to do

## Files Updated

### Core Commands
- ✅ `summon.md` - Start agent session
- ✅ `dismiss.md` - End session
- ✅ `handoff.md` - Hand off work

### Task Management Commands
- ✅ `tasks.md` - Show task report
- ✅ `claim-task.md` - Claim a task
- ✅ `create-task.md` - Create new task
- ✅ `update-task.md` - Update task progress
- ✅ `close-task.md` - Close completed task

### Other Commands
- ✅ `commit.md` - Commit changes (updated to reference COMMIT_GUIDELINES since commit-workflow skill doesn't exist)

## New Documentation

- ✅ `TROUBLESHOOTING.md` - Command troubleshooting guide

## Testing

To verify the fix works:

1. **Test command execution:**
   ```
   /summon
   ```
   Expected: Agent executes session-start skill immediately

2. **Test documentation reading:**
   ```
   what does /summon do?
   ```
   or
   ```
   .opencode/commands/summon.md
   ```
   Expected: Agent explains what the command does

3. **Test other commands:**
   - `/dismiss` - Should execute session-end skill
   - `/handoff` - Should execute handoff-workflow skill
   - `/tasks` - Should execute tasks-report skill

## Future Improvements

1. **Create missing skills:**
   - `commit-workflow` - Standardized commit process
   
2. **Add more commands:**
   - `/debug` - Debug mode
   - `/help` - Show available commands
   
3. **Improve command discovery:**
   - Add command autocomplete
   - Show available commands in session start

## Related Files

- `.opencode/opencode.json` - Command registration
- `.opencode/commands/README.md` - Command system documentation
- `.opencode/skills/*/SKILL.md` - Skill implementations
