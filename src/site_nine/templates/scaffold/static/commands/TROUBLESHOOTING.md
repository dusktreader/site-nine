# Command Troubleshooting

## Why agents read command files instead of executing them

### The Problem

When a user types `.opencode/commands/summon.md`, the agent reads the file and explains it instead of executing the `/summon` command.

### Why This Happens

**This is correct behavior.** The agent is distinguishing between:

1. **User types `/summon`**
   - OpenCode loads `summon.md` and passes it to the agent as a command
   - Agent sees "user typed /summon" context
   - Agent should execute the command immediately

2. **User types `.opencode/commands/summon.md`**
   - User is literally asking to read that file path
   - Agent should read and explain the file
   - This is documentation request, not a command invocation

### How to Fix Command Files

Command files should handle both scenarios:

```markdown
---
description: Command description here
---

# /command-name Command

## If you are seeing this because the user typed `/command-name`:

**ACTION REQUIRED:** Execute the command immediately.

[Instructions for executing the command]

---

## If you are seeing this because the user asked about the command:

[Documentation about what the command does]
```

This way:
- When invoked as `/command`, the agent sees "ACTION REQUIRED" at the top
- When read as documentation, the agent can explain both sections

### Testing Commands

To test if a command works correctly:

1. **Test as command:** Type `/summon` (not the file path)
2. **Test as documentation:** Type "what does /summon do?" or read the file path

Both should work correctly but behave differently.

## Common Issues

### "Agent reads the file instead of executing"

**Cause:** User typed the file path (`.opencode/commands/summon.md`) instead of the command (`/summon`)

**Solution:** Use the `/summon` command syntax, not the file path

### "Command doesn't exist"

**Cause:** Command not registered in `opencode.json`

**Solution:** Add command to `.opencode/opencode.json`:

```json
{
  "command": {
    "your-command": {
      "template": ".opencode/commands/your-command.md",
      "description": "Description here"
    }
  }
}
```

### "Command loads but agent doesn't execute"

**Cause:** Command file doesn't clearly indicate it's an action command

**Solution:** Update command file to match the pattern shown above with "ACTION REQUIRED" section
