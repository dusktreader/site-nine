# OpenCode Integration

site-nine is designed to work seamlessly with [OpenCode](https://github.com/khulnasoft/opencode), an AI coding assistant. This guide covers OpenCode-specific features, slash commands, and best practices for working with site-nine personas.

## What is OpenCode?

OpenCode is a terminal-based AI coding assistant that provides an interactive conversation interface for working with AI agents. When you use site-nine with OpenCode, you get:

- **Natural Conversation Interface** - Talk to specialized personas through chat
- **Slash Commands** - Quick commands for common workflows
- **Multiple Sessions** - Run several personas in parallel terminals
- **Session Persistence** - Resume conversations where you left off
- **Automatic Renaming** - Sessions labeled with persona and role

## Starting OpenCode Sessions

There are two ways to start working with a site-nine persona in OpenCode:

### Method 1: Direct Summon (Recommended)

Use the `s9 summon` command to launch OpenCode with a persona automatically:

```bash
s9 summon operator
```

This will:
1. Start OpenCode
2. Initialize a mission with the specified role
3. Auto-select an unused persona name
4. Show you available tasks

### Method 2: Manual Launch

Launch OpenCode manually, then use the `/summon` slash command:

```bash
opencode
```

Inside OpenCode:
```
/summon operator
```

## Slash Commands Reference

OpenCode provides several slash commands for managing site-nine workflows. Type these commands directly in the OpenCode chat interface.

### Session Management

#### `/summon` - Start New Mission

**Purpose:** Initialize a new development mission with role and persona selection.

**Usage:**
```
/summon
/summon <role>
/summon <role> --persona <name>
/summon <role> --auto-assign
/summon <role> --task TASK-ID
```

**Examples:**
```
/summon                          # Interactive: asks you to choose role
/summon operator                 # Direct: starts Operator mission
/summon operator --persona atlas # Use specific persona "atlas"
/summon operator --auto-assign   # Auto-claim top priority task
/summon operator --task OPR-H-0065  # Claim specific task and start
```

**What it does:**
1. Selects or asks for a role (Administrator, Architect, Engineer, Tester, Documentarian, Designer, Inspector, Operator)
2. Auto-selects an unused persona name from mythology (or uses `--persona` if provided)
3. Creates a mission file with metadata
4. Shows the persona's whimsical bio
5. Renames your OpenCode session to match the persona
6. Checks for pending handoffs and reviews (if Administrator)
7. Shows available tasks for your role
8. (Optional) Auto-claims and starts work on a task

**Role Options:**
- **Administrator** - Coordination, delegation, task creation
- **Architect** - Design, planning, technical decisions
- **Engineer** - Implementation, coding, feature development
- **Tester** - Testing, validation, QA
- **Documentarian** - Documentation, guides, knowledge management
- **Designer** - UI/UX, visual design, user experience
- **Inspector** - Code review, security audit, quality checks
- **Operator** - Deployment, infrastructure, DevOps

---

#### `/dismiss` - End Current Mission

**Purpose:** Properly close a development mission with cleanup and documentation.

**Usage:**
```
/dismiss
/dismiss [optional message]
```

**Examples:**
```
/dismiss
/dismiss great work today!
/dismiss excellent job on the refactoring
```

**What it does:**
1. Captures optional thank you message
2. Locates mission file
3. Gathers git status, commits, and tasks
4. Updates mission file with end time, duration, outcomes
5. Closes open tasks in the database
6. Commits the mission file
7. Displays mission summary
8. Shows your message (if provided)
9. Says goodbye

**When to use:**
- Work is complete for this session
- Handing off to another persona
- User says "we're done for now"
- User says "goodbye" or "thanks"

**Don't use when:**
- Taking a short break
- Waiting for user response
- In the middle of active work

---

### Task Management

#### `/create-task` - Create New Task

**Purpose:** Guide Administrator agents through creating well-formed tasks.

**Usage:**
```
/create-task
```

**What it does:**
1. Validates Administrator role
2. Helps determine priority (CRITICAL/HIGH/MEDIUM/LOW)
3. Guides through title, objective, role, category
4. Creates database entry and markdown file
5. Verifies creation success

**Note:** Only available to Administrator role.

---

#### `/claim-task` - Find & Claim Available Task

**Purpose:** Help agents find appropriate tasks and claim them safely.

**Usage:**
```
/claim-task
```

**What it does:**
1. Checks your current role
2. Lists available TODO tasks matching your role
3. Shows task details when you select one
4. Claims the task with concurrency protection
5. Updates status to UNDERWAY
6. Shows the markdown artifact

---

#### `/update-task` - Update Task Progress

**Purpose:** Record progress, notes, and time spent on tasks.

**Usage:**
```
/update-task
```

**What it does:**
1. Identifies your current UNDERWAY task
2. Prompts for progress notes
3. Asks for hours spent (optional)
4. Updates the task in database
5. Appends notes to markdown artifact

---

#### `/close-task` - Close Completed Task

**Purpose:** Properly close tasks with appropriate status.

**Usage:**
```
/close-task
```

**What it does:**
1. Identifies your current UNDERWAY task
2. Asks for closing status:
   - **COMPLETE** - Task finished successfully
   - **PAUSED** - Temporarily stopped, will resume later
   - **BLOCKED** - Can't proceed, waiting on dependency
   - **ABORTED** - Cancelled, won't be completed
3. Prompts for closing notes
4. Updates database with closed_at timestamp
5. Updates markdown artifact

---

#### `/tasks` - Show Task Queue Report

**Purpose:** Display comprehensive task report by priority and status.

**Usage:**
```
/tasks
```

**What it does:**
1. Generates report from SQLite database
2. Groups tasks by priority (CRITICAL → HIGH → MEDIUM → LOW)
3. Shows status, role, title, agent, creation date
4. Provides summary with key metrics
5. Suggests next actions based on your role

---

### Collaboration

#### `/handoff` - Hand Off to Another Agent

**Purpose:** Transfer work to another persona with full context.

**Usage:**
```
/handoff [Role]
```

**What it does:**
1. Identifies your current role and persona
2. Determines target role (or asks if not specified)
3. Gathers current state (git status, tasks, commits)
4. Creates structured handoff document with:
   - What was done
   - Current state
   - What needs to be done next
   - Files to review
   - Approach and constraints
   - Acceptance criteria
5. Saves handoff as `.pending.md` file
6. Updates your mission file
7. Provides instructions for recipient

**When to use:**
- Administrator delegates to Engineer
- Engineer hands off to Tester
- Tester finds bugs, hands back to Engineer
- Engineer completes feature, hands to Inspector
- Any work transition between roles

**Handoff lifecycle:**
1. **Created (`.pending.md`)** - Waiting for recipient
2. **Accepted (`.accepted.md`)** - Recipient started work
3. **Completed (`.completed.md`)** - Work finished

---

#### `/commit` - Commit & Push Changes

**Purpose:** Commit changes and push to origin following project standards.

**Usage:**
```
/commit
```

**What it does:**
1. Runs QA checks (`make qa/full`)
2. Reviews git status and diff
3. Prompts to update task artifact with details
4. Guides Conventional Commits message creation
5. Commits with agent attribution and task reference
6. Pushes to origin

**What it ensures:**
- QA checks pass (tests, linting, types)
- Task artifact updated
- Conventional Commits format
- Agent attribution included
- Task reference `[Task: ID]` included
- Changes pushed to remote

---

## OpenCode Session Mechanics

### Session Lifecycle

1. **Start** - `/summon <role>` creates a new mission
2. **Work** - Persona claims tasks, writes code, runs tests
3. **End** - `/dismiss` closes the mission properly

### Session Naming

When you start a mission, OpenCode automatically renames the session to:

```
Operation <codename>: <Persona> - <Role>
```

Examples:
- `Operation clever-blaze: Melpomene - Documentarian`
- `Operation silver-titan: Goibniu - Engineer`
- `Operation quantum-echo: Themis - Tester`

This helps you identify which persona is working in each terminal when running multiple sessions.

### Multiple Sessions

You can run multiple OpenCode sessions in parallel, each with a different persona. This is powerful for complex workflows:

**Example: Feature Development Flow**

Terminal 1 (Architect):
```bash
s9 summon architect
# Design the authentication system
```

Terminal 2 (Engineer):
```bash
s9 summon engineer
# Implement the design
```

Terminal 3 (Tester):
```bash
s9 summon tester
# Write and run tests
```

Each persona works independently but can hand off work using `/handoff`.

### Resuming Sessions

OpenCode sessions persist even if you close the terminal. To resume:

1. Launch OpenCode: `opencode`
2. Select your previous conversation
3. Continue where you left off

The persona will remember the mission context and tasks.

## Tips for Effective Persona Communication

### Talk Naturally

Personas respond to natural conversation. You don't need to use formal commands:

**Good Examples:**
- "Can you implement user authentication?"
- "What tests are failing?"
- "Create a high-priority task for API rate limiting"
- "Hand this off to an Engineer"

**Avoid Over-Formality:**
- ❌ "Execute command: implement authentication module"
- ✅ "Can you implement authentication?"

### Be Specific About Context

Personas work best with clear context:

**Less Helpful:**
- "Fix the bug"
- "Update the docs"

**More Helpful:**
- "Fix the authentication timeout bug in src/auth/session.py:45"
- "Update the API documentation to include the new rate limiting endpoints"

### Ask for Clarification

If you're unsure, ask the persona:

- "What tasks are available for your role?"
- "What's the status of task ENG-H-0027?"
- "Can you explain what you just changed?"

### Use Personas' Strengths

Each role specializes in different work:

- **Administrator** - "Create tasks", "Show me the dashboard", "Coordinate the team"
- **Architect** - "Design the authentication system", "Review the database schema"
- **Engineer** - "Implement this feature", "Fix this bug", "Refactor this module"
- **Tester** - "Run the test suite", "Write tests for authentication", "Validate the API"
- **Documentarian** - "Update the README", "Document this API endpoint"
- **Inspector** - "Review this code for security issues", "Audit the authentication logic"
- **Operator** - "Deploy to staging", "Check the server logs", "Update the CI/CD pipeline"

### Leverage Handoffs

Don't try to do everything in one session. Use `/handoff` to pass work between specialized roles:

```
1. Administrator creates tasks
2. Architect designs the solution
3. Architect hands off to Engineer
4. Engineer implements the feature
5. Engineer hands off to Tester
6. Tester validates and reports results
7. Inspector reviews code quality
```

## OpenCode Keyboard Shortcuts

OpenCode provides several keyboard shortcuts to improve your workflow:

| Shortcut | Action |
|----------|--------|
| `Ctrl+P` | List available actions/commands |
| `Ctrl+C` | Cancel current operation |
| `/` then `Tab` | Show available slash commands |
| `↑` / `↓` | Navigate command history |
| `Ctrl+L` | Clear screen (in some terminals) |

**Tip:** Type `/` and press `Tab` to see all available slash commands with descriptions.

## OpenCode UI Features

### Chat Interface

OpenCode presents a clean chat interface where you can:

- Type messages naturally to your persona
- See formatted code blocks with syntax highlighting
- Review task tables and status reports
- Read file paths as clickable links (in some terminals)

### Command Palette

Press `Ctrl+P` to open the command palette:

- See available slash commands
- Access OpenCode settings
- View session management options
- Get help and feedback options

### Session Management

OpenCode's session management UI lets you:

- View all active and past sessions
- Resume previous conversations
- Rename sessions manually
- Delete old sessions

Access this from the command palette or startup screen.

## Troubleshooting

### Session Not Renaming

If your OpenCode session doesn't rename automatically:

1. The persona should have run `s9 mission rename-tui` during `/summon`
2. Check if you have multiple OpenCode sessions open
3. Try manually: `s9 mission rename-tui <persona> <Role>`

### Slash Command Not Found

If a slash command isn't recognized:

1. Verify the command file exists in `.opencode/commands/`
2. Check frontmatter has `description` field
3. Restart OpenCode
4. Type `/` then `Tab` to see available commands

### Multiple Sessions Confusion

When running multiple OpenCode sessions:

1. Use session naming to identify each persona
2. Check mission status: `s9 mission list`
3. View dashboard: `s9 dashboard`
4. Each session has a unique mission ID

### Persona Not Following Commands

If a persona doesn't respond to slash commands:

1. Verify you typed the command correctly (starts with `/`)
2. Some commands are role-specific (e.g., `/create-task` for Administrator)
3. Try asking naturally: "Can you create a task?"
4. Check `.opencode/commands/` for command documentation

## Best Practices

### Session Hygiene

- **Always use `/dismiss`** when ending a session (don't just close the terminal)
- **One mission per session** - Don't try to switch roles mid-session
- **Close completed missions** - Use `/dismiss` to properly update mission files

### Task Workflow

1. Start session with `/summon <role>`
2. Check available tasks (shown automatically or use `/tasks`)
3. Claim a task naturally: "Can you claim task ENG-H-0027?"
4. Work on the task (code, test, document)
5. Update progress: `/update-task` or naturally: "Let me update my progress"
6. Close when done: `/close-task` or naturally: "This task is complete"
7. End session: `/dismiss`

### Multi-Persona Coordination

When running multiple personas:

1. **Use handoffs for context** - Don't assume other personas know what you did
2. **Check the dashboard** - `s9 dashboard` shows all active work
3. **Coordinate in comments** - Leave notes in task artifacts
4. **Use descriptive commit messages** - Include agent attribution

### Communication Style

- **Be conversational** - Personas respond to natural language
- **Provide context** - Share relevant files, line numbers, requirements
- **Ask questions** - Personas can explain, explore, and investigate
- **Give feedback** - Let personas know if something isn't working

## See Also

- [Quickstart Guide](quickstart.md) - Get started in 5 minutes
- [Working with Agents](agents/overview.md) - Learn about roles and personas
- [CLI Reference](cli/for-humans.md) - Command-line tools for Directors
- [Advanced Topics](advanced.md) - Multi-persona workflows
- [OpenCode Documentation](https://opencode.ai/docs) - Official OpenCode docs
