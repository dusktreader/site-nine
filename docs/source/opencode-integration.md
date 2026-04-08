# OpenCode Integration

site-nine is designed to work seamlessly with [OpenCode](https://github.com/khulnasoft/opencode), an AI coding assistant. This guide covers how possessions are started and ended, how the session lifecycle works, and best practices for working with site-nine agents in OpenCode.

## What is OpenCode?

OpenCode is a terminal-based AI coding assistant that provides an interactive conversation interface for working with AI agents. When you use site-nine with OpenCode, you get:

- **Natural conversation interface** - Talk to specialized agents through chat
- **Multiple sessions** - Run several agents in parallel terminals
- **Session persistence** - Resume conversations where you left off
- **Automatic renaming** - Sessions labeled with daemon, role, and codename

## Starting a Possession

The Director (you) always starts a possession using the `s9 summon` CLI command. This launches OpenCode and automatically triggers the `possession-start` skill inside the new session.

```bash
s9 summon operator
s9 summon engineer
s9 summon documentarian
```

### What happens during possession-start

The `possession-start` skill runs through the possession initialization sequence:

1. Initializes a new possession record in the database (ROLE_PENDING state)
2. Records the selected role (DAEMON_PENDING state)
3. Auto-claims the least-recently-used daemon for that role (or invents one if all have been used within 3 days)
4. Transitions the possession to ACTIVE state
5. Renames the OpenCode session to `Operation <codename>: <Daemon> - <Role>`
6. Shows the daemon's whimsical bio
7. Displays the role-filtered task dashboard

Example result for `s9 summon documentarian`:

- Daemon: **Fukurokuju** (Japanese god of wisdom)
- Codename: **Operation silver-titan**
- Session title: `Operation silver-titan: Fukurokuju - Documentarian`

### Multiple sessions

You can run multiple OpenCode sessions in parallel, each with a different daemon. This enables powerful multi-agent workflows:

**Terminal 1 (Architect):**
```bash
s9 summon architect
# Design the authentication system
```

**Terminal 2 (Engineer):**
```bash
s9 summon engineer
# Implement the design
```

**Terminal 3 (Tester):**
```bash
s9 summon tester
# Write and run tests
```

Each agent works independently, coordinating through the shared task database.

## Ending a Possession

When work is done, the `possession-end` skill handles proper closure. Call it by asking the agent to end the possession, or by explicitly invoking the skill.

The skill:

1. Gathers git status, recent commits, and task information
2. Updates the possession file with outcomes and duration
3. Closes any UNDERWAY tasks
4. Commits the possession file
5. Displays a possession summary
6. Transitions possession status to EXORCISED

## OpenCode Session Mechanics

### Session naming

When a possession starts, OpenCode automatically renames the session to:

```
Operation <codename>: <Daemon> - <Role>
```

Examples:
- `Operation clever-blaze: Melpomene - Documentarian`
- `Operation silver-titan: Goibniu - Engineer`
- `Operation quantum-echo: Themis - Tester`

This helps you identify which daemon is working in each terminal when running multiple sessions.

### Resuming sessions

OpenCode sessions persist even if you close the terminal. To resume:

1. Launch OpenCode: `opencode`
2. Select your previous conversation
3. Continue where you left off

The agent will have the possession context available from the conversation history.

## Task Workflow

Agents work on tasks conversationally. The typical flow within an active possession:

1. Check available tasks (shown automatically at startup, or ask the agent)
2. Claim a task: "Can you claim task ENG-H-0027?"
3. Work on the task (code, test, document)
4. Update progress: "Let me update my progress on this task"
5. Close when done: "This task is complete"
6. End the possession when work for the session is done

## Talking to Agents

Agents respond to natural conversation. You don't need formal commands.

**Good examples:**
- "Can you implement user authentication?"
- "What tests are failing?"
- "Create a high-priority task for API rate limiting"

**Each role has its strengths:**

- **Administrator** - "Create tasks", "Show me the dashboard", "Coordinate the team"
- **Architect** - "Design the authentication system", "Review the database schema"
- **Engineer** - "Implement this feature", "Fix this bug", "Refactor this module"
- **Tester** - "Run the test suite", "Write tests for authentication", "Validate the API"
- **Documentarian** - "Update the README", "Document this API endpoint"
- **Inspector** - "Review this code for security issues", "Audit the authentication logic"
- **Operator** - "Deploy to staging", "Check the server logs", "Update the CI/CD pipeline"

### Be specific about context

Agents work best with clear context.

**Less helpful:**
- "Fix the bug"
- "Update the docs"

**More helpful:**
- "Fix the authentication timeout bug in src/auth/session.py:45"
- "Update the API documentation to include the new rate limiting endpoints"

## Best Practices

### Session hygiene

- **Always use `possession-end`** when ending a session (don't just close the terminal)
- **One possession per session** - Don't try to switch roles mid-session
- **Close completed possessions** - Properly ending possessions updates files and database records

### Multi-agent coordination

When running multiple agents:

- **Use task descriptions for context** - Don't assume other agents know what you did in another session
- **Check the dashboard** - `s9 dashboard` shows all active work and possession status
- **Use descriptive commit messages** - Include daemon attribution

## OpenCode Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+P` | List available actions/commands |
| `Ctrl+C` | Cancel current operation |
| `↑` / `↓` | Navigate message history |

## Troubleshooting

### Session not renaming

If your OpenCode session doesn't rename automatically after possession start:

1. Check that the `possession-start` skill ran successfully
2. If you have multiple OpenCode sessions open, the rename tool may have targeted the wrong session
3. Ask the agent to rename the session manually

### Agent not using skills

Skills are loaded by prompting the agent to use them. If the agent isn't following possession start/end procedures:

1. Ask explicitly: "Please load the possession-start skill"
2. Check that `.opencode/skills/` exists and contains the skill files
3. Restart the OpenCode session

### Multiple sessions confusion

When running multiple OpenCode sessions:

1. Use the session naming convention to identify each daemon
2. Check possession status with `s9 dashboard`
3. Each session has a unique possession ID in the database

## See Also

- [Quickstart Guide](quickstart.md) - Get started in 5 minutes
- [Working with Agents](agents/overview.md) - Learn about possessions, roles, and daemons
- [CLI Reference](cli/for-humans.md) - Command-line tools for Directors
- [Advanced Topics](advanced.md) - Multi-agent workflows
- [OpenCode Documentation](https://opencode.ai/docs) - Official OpenCode docs
