# Custom Commands & Skills

This directory contains custom OpenCode commands that leverage skills for standardized workflows.

> **Note on Task ID Format:** This document contains examples using the old task ID format (e.g., H027, H038). 
> The current format is `PREFIX-PRIORITY-NUMBER` (e.g., OPR-H-0001, ENG-C-0005). 
> Task IDs are now **auto-generated** by the `s9 task create` command.
> See `.opencode/skills/task-management/SKILL.md` for details.

## What Are Commands & Skills?

**Commands** are slash commands (like `/summon`) that users type in OpenCode to trigger specific workflows.

**Skills** are reusable instruction sets that agents load to follow complex, multi-step procedures.

Together, they provide a powerful way to standardize and simplify common development workflows.

---

## Available Commands

### Session Management

#### `/summon` - Start New Mission

**Purpose:** Initialize a new development mission with proper role selection and persona naming.

**Usage:**
```
/summon
/summon <role>
/summon <role> --auto-name
/summon <role> --auto-assign
/summon <role> --auto-name --auto-assign
/summon <role> --task TASK-ID
```

**Examples:**
- `/summon` - Interactive mode: asks you to choose a role and persona name
- `/summon operator` - Direct mode: starts an Operator session immediately with persona selection
- `/summon operator --auto-name` - Fully automated: auto-selects first unused persona name
- `/summon operator --auto-assign` - Automated task assignment: auto-claims and starts work on top priority task
- `/summon operator --auto-name --auto-assign` - Fully automated: auto-selects persona and auto-assigns top priority task
- `/summon operator --task OPR-H-0065` - Direct task assignment: auto-names persona, claims specific task, and starts work immediately

**What it does:**
1. (If no role provided) Asks you to choose a role (Administrator, Architect, Engineer, Tester, etc.)
2. Suggests a persona name from mythology appropriate to your role
3. Checks for name conflicts with existing missions
4. Creates a mission file with proper metadata
5. Reads essential project documentation
6. Shows available tasks for your role
7. (If `--auto-assign` flag) Auto-claims the top priority task for your role
8. (If `--task TASK-ID` flag) Auto-claims the specific task and starts work immediately

**Flags:**
- `--auto-name` - Automatically select the first unused persona name (skips persona selection prompt)
- `--auto-assign` - Automatically claim and start work on the top priority task for the role (requires role to be specified)
- `--task TASK-ID` - Claim a specific task and start work immediately (implies `--auto-name`, mutually exclusive with `--auto-assign`, requires role to be specified)

**Example interaction (interactive mode):**
```
User: /summon

Agent: Which role should I assume for this mission?
- Administrator (coordination & delegation)
- Architect (design & planning)
- Engineer (implementation)
- Tester (validation & QA)
- Documentarian (docs & guides)
- Designer (UI/UX)
- Inspector (review & audit)
- Operator (deployment & infrastructure)

User: Engineer

Agent: I suggest the persona "goibniu" for this Engineer mission.
(Goibniu is the Celtic god of metalworking and craft)

Would you like to use this persona, or choose a different one?

User: That's perfect!

Agent: ✅ Mission initialized!

I'm Goibniu, your Engineer persona for this mission.

[Session continues...]
```

**Example interaction (direct mode):**
```
User: /summon operator

Agent: I suggest the persona "hemera" for this Operator mission.
(Hemera is the Greek goddess of day)

Would you like to use this persona, or choose a different one?

User: yes

Agent: ✅ Mission initialized!

I'm Hemera, your Operator persona for this mission.

[Session continues...]
```

**Pro tip:** Use direct mode (`/summon <role>`) to skip the role selection and start working faster!

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
/dismiss great work today! thank you
/dismiss excellent job on the refactoring
```

**What it does:**
1. Captures optional thank you message from the Director
2. Locates your mission file
3. Gathers information about work completed (git status, commits, tasks)
4. Updates mission file with:
   - End time and duration
   - Files changed
   - Outcomes (✅ completed, ⚠️ partial, ❌ blocked)
   - Dismissal message (if provided)
   - Next steps for future work
5. Closes any open tasks in the task database
6. Verifies task artifacts are updated
7. Commits the mission file
8. Provides a summary of the mission
9. Displays the Director's message (if provided)
10. Says goodbye

**Example interaction (with message):**
```
User: /dismiss great work today! thank you

Agent: Closing mission...

[Agent checks git status, recent commits, open tasks...]

I've updated the mission file with:
- End time: 15:30:00
- Duration: ~2.5 hours
- Status: completed

Files changed:
- .opencode/commands/dismiss.md - Added message parameter
- .opencode/skills/session-end/SKILL.md - Added dismissal message handling

Tasks closed:
- OPR-M-0111: Add optional message parameter to /dismiss command (COMPLETE)

✅ Mission closed successfully!

**Summary:**
- Duration: ~2.5 hours
- Files changed: 2 files
- Tasks completed: OPR-M-0111
- Status: completed

**What was accomplished:**
- ✅ Added message parameter to /dismiss command
- ✅ Updated session-end skill to handle messages
- ✅ Documentation updated

**Next steps:**
- None - work complete

Mission file updated: .opencode/work/missions/2026-02-04.15:44:19.operator.dumuzid.titanium-nexus.md

💬 **From the Director:**
> great work today! thank you

Thank you for working with me! I'm Dumuzid, signing off.

I descend once more to the sacred flocks, my cycle renewed as the seasons turn eternal.
```

**Example interaction (without message):**
```
User: /dismiss

Agent: Closing mission...

[Agent checks git status, recent commits, open tasks...]

I've updated the mission file with:
- End time: 15:30:00
- Duration: ~2.5 hours
- Status: completed

Files changed:
- src/s9/main.py - Added rate limiting
- tests/test_auth.py - Added rate limiting tests  
- .opencode/data/tasks/H027.md - Updated task artifact

Tasks closed:
- H027: Implement Authentication Rate Limiting (COMPLETE)

✅ Mission closed successfully!

**Summary:**
- Duration: ~2.5 hours
- Files changed: 3 files
- Tasks completed: H027
- Status: completed

**What was accomplished:**
- ✅ Rate limiting implemented and tested
- ✅ All tests passing (313 tests, 100% pass rate)
- ✅ Documentation updated

**Next steps:**
- None - work complete

Mission file updated: .opencode/work/missions/2026-01-29.14:30:00.builder.goibniu.rate-limiting.md

Thank you for working with me! I'm Goibniu, signing off.

I return to my forge in the halls of the Tuatha Dé Danann, my craft complete.
```

**When to use:**
- ✅ You're done with your work mission
- ✅ Handing off to another persona
- ✅ User says "we're done for now"
- ✅ User says "goodbye" or "thanks"

**Don't use when:**
- ❌ Taking a short break
- ❌ Waiting for user response
- ❌ In the middle of work

---

### Task Management

#### `/create-task` - Create New Task

**Purpose:** Guide Administrator agents through creating well-formed tasks in the SQLite database.

**Usage:**
```
/create-task
```

**What it does:**
1. Validates you have Administrator role
2. Helps determine appropriate priority (C/H/M/L)
3. Finds next available task ID
4. Guides through title, objective, role, and category selection
5. Creates database entry and markdown artifact file
6. Verifies creation success

**Example interaction:**
```
User: /create-task

Agent: I'll help you create a new task.

First, what priority level should this task have?
- CRITICAL (C###) - Blocking, security, P0 bugs
- HIGH (H###) - Important features, P1 bugs  
- MEDIUM (M###) - Nice-to-have features
- LOW (L###) - Polish, docs, minor issues

User: HIGH

Agent: The next available HIGH priority ID is H038.

What is the title of this task?

User: Implement Rate Limiting for API Gateway

Agent: What is the primary role for this task?
- Administrator, Architect, Engineer, Tester, etc.

User: Engineer

Agent: Creating task H038...

✅ Task created successfully!

Task ID: H038
Title: Implement Rate Limiting for API Gateway
Priority: HIGH
Role: Engineer
Status: TODO

Markdown file: .opencode/tasks/artifacts/H038.md
```

---

#### `/claim-task` - Find & Claim Available Task

**Purpose:** Help agents find appropriate tasks and claim them safely.

**Usage:**
```
/claim-task
```

**What it does:**
1. Checks your current role
2. Lists available tasks (TODO status) matching your role
3. Shows task details when you select one
4. Claims the task with concurrency protection
5. Updates status to UNDERWAY
6. Shows the markdown artifact for reference

**Example interaction:**
```
User: /claim-task

Agent: I'm a Engineer agent. Let me find available Engineer tasks...

Available Engineer tasks (TODO):

H038 - Implement Rate Limiting for API Gateway (HIGH)
H040 - Add Database Connection Pooling (MEDIUM)
M012 - Refactor Error Handling Module (MEDIUM)

Which task would you like to claim?

User: H038

Agent: [Shows task details...]

Would you like to claim this task?

User: Yes

Agent: Claiming task H038...

✅ Task H038 claimed successfully!

Status changed: TODO → UNDERWAY
Claimed by: Goibniu (Engineer)
Claimed at: 2026-01-29T15:30:00+00:00

Task artifact: .opencode/tasks/artifacts/H038.md

What would you like to do first?
```

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
3. Asks for actual hours spent (optional)
4. Updates the task in database
5. Appends notes to markdown artifact
6. Shows updated status

**Example interaction:**
```
User: /update-task

Agent: I see you're working on H038. Let me update its progress.

What progress have you made? (Describe what you did)

User: Implemented token bucket algorithm, added Redis backend, wrote unit tests

Agent: How many hours did you spend? (optional, can skip)

User: 2.5

Agent: Updating task H038...

✅ Task updated!

Task: H038 - Implement Rate Limiting for API Gateway
Status: UNDERWAY
Actual time: 2.5 hours
Latest note: Implemented token bucket algorithm, added Redis backend, wrote unit tests

Updated: .opencode/tasks/artifacts/H038.md
```

---

### `/close-task` - Close Completed Task

**Purpose:** Properly close tasks with appropriate status and cleanup.

**Usage:**
```
/close-task
```

**What it does:**
1. Identifies your current UNDERWAY task
2. Asks for closing status (COMPLETE/PAUSED/BLOCKED/ABORTED)
3. Prompts for closing notes
4. Updates database with closed_at timestamp
5. Updates markdown artifact
6. Verifies closure success

**Example interaction:**
```
User: /close-task

Agent: I see you're working on H038. Let's close it.

What is the closing status?
- COMPLETE - Task finished successfully
- PAUSED - Temporarily stopped, will resume later
- BLOCKED - Can't proceed, waiting on dependency
- ABORTED - Cancelled, won't be completed

User: COMPLETE

Agent: Please provide closing notes (what was accomplished)

User: Rate limiting fully implemented with token bucket algorithm, Redis backend, comprehensive test coverage. All 25 tests passing. Documentation updated.

Agent: Closing task H038...

✅ Task H038 closed successfully!

Status: COMPLETE
Closed at: 2026-01-29T17:45:00+00:00
Duration: 2.5 hours
Final notes: Rate limiting fully implemented...

Great work! Ready for your next task?
```

**When to use each status:**
- `COMPLETE` - Work finished, verified, ready to ship
- `PAUSED` - Taking a break, will resume later (you still own it)
- `BLOCKED` - Can't proceed without something else (dependency, decision, etc.)
- `ABORTED` - Task cancelled, requirements changed, no longer needed

---

### Common Workflows

#### `/tasks` - Show Task Queue Report

**Purpose:** Display comprehensive task report showing all project work by priority and status.

**Usage:**
```
/tasks
```

**What it does:**
1. Generates task report from SQLite database
2. Groups tasks by priority (CRITICAL, HIGH, MEDIUM, LOW)
3. Shows status, role, title, agent, creation date
4. Provides summary with key metrics
5. Suggests next actions based on your role

**Example interaction:**
```
User: /tasks

Agent: Generating task report...

# Task Report

**Generated:** 2026-01-29T22:06:12-08:00 (local time)
**Total Tasks:** 59

## CRITICAL Priority
[No critical tasks]

## HIGH Priority

| ID | Status | Role | Title | Agent | Created |
|----|--------|------|-------|-------|---------|
| H003 | TODO | Tester | Validate Rate Limiting Functionality | - | 2026-01-30 |
| H035 | UNDERWAY | Tester | Full Stack Integration Testing | themis | 2026-01-30 |
| H036 | TODO | Inspector | Security Review of Gateway Authentication | - | 2026-01-30 |

## MEDIUM Priority

| ID | Status | Role | Title | Agent | Created |
|----|--------|------|-------|-------|---------|
| M021 | TODO | Documentarian | Update MkDocs Documentation | - | 2026-01-30 |

## LOW Priority

| ID | Status | Role | Title | Agent | Created |
|----|--------|------|-------|-------|---------|
| L008 | TODO | Engineer | Add SQL Injection Fuzzing Tests | - | 2026-01-30 |

---

**Summary:**
- **Total tasks:** 59
- **TODO (available):** 3 tasks
- **UNDERWAY (active):** 1 task
- **COMPLETE:** 55 tasks

**For your role (Tester):**
- 1 TODO task: H003 - Validate Rate Limiting Functionality
- 1 UNDERWAY: H035 (claimed by themis)

**Recommendations:**
You could claim H003 if you're ready to work on rate limiting validation.

Would you like to:
1. See details? `cd .opencode/tasks && ./tasks.py show H003`
2. Claim H003? Use `/claim-task`
3. Filter by status/priority? I can show just TODO, just HIGH, etc.
```

**When to use:**
- ✅ Starting a session - see what work is available
- ✅ Planning - understand project state
- ✅ Looking for work - find TODO tasks for your role
- ✅ Checking progress - see what's UNDERWAY or BLOCKED

**What you see:**
- **All tasks** by priority (CRITICAL → HIGH → MEDIUM → LOW)
- **Status** (TODO, UNDERWAY, BLOCKED, COMPLETE, etc.)
- **Role** assignment
- **Agent** currently working on it
- **Creation dates**
- **Summary metrics**

**Follow-up actions:**
- Use `/claim-task` to claim a TODO task
- Use `./tasks.py show TASK_ID` for full details
- Filter by role, status, or priority if needed

---

#### `/commit` - Commit & Push Changes

**Purpose:** Commit changes and push to origin following project standards (QA, task artifacts, Conventional Commits).

**Usage:**
```
/commit
```

**What it does:**
1. Runs QA checks (`make qa/full`)
2. Reviews git status and diff to see what's changing
3. Prompts you to update task artifact with implementation details
4. Guides you through creating a Conventional Commits message with agent attribution and task reference
5. Commits the changes
6. Pushes to origin

**Example interaction:**
```
User: /commit

Agent: I'll commit and push your changes following project standards.

Step 1: Running QA checks...

$ make qa/full
[Running tests, linting, type checking...]
✅ All quality checks pass!

Step 2: Reviewing changes...

$ git status
Modified files:
- .opencode/commands/commit.md
- .opencode/skills/commit-workflow/SKILL.md
- .opencode/commands/README.md

$ git diff --stat
 3 files changed, 542 insertions(+), 2 deletions(-)

Step 3: I need to update the task artifact. Let me add implementation details...

[Agent reads .opencode/data/tasks/M001.md and updates it]

Updated task artifact with:
- Implementation steps completed
- Files changed with descriptions
- Testing performed

Step 4: Staging files...

$ git add .opencode/commands/commit.md .opencode/skills/commit-workflow/SKILL.md .opencode/commands/README.md .opencode/data/tasks/M001.md

Step 5: Creating commit...

$ git commit -m "feat(commands): add /commit command and skill [Agent: Administrator - Ishtar]" -m "" -m "Created commit-workflow skill to standardize commit process with QA checks, task artifact updates, and Conventional Commits format." -m "" -m "- .opencode/commands/commit.md - Command entry point" -m "- .opencode/skills/commit-workflow/SKILL.md - Complete workflow (500+ lines)" -m "- .opencode/commands/README.md - Added documentation" -m "" -m "[Task: M001]"

[main 7a3f9e2] feat(commands): add /commit command and skill [Agent: Administrator - Ishtar]
 4 files changed, 542 insertions(+), 2 deletions(-)

Step 6: Pushing to origin...

$ git push
Enumerating objects: 15, done.
Counting objects: 100% (15/15), done.
Writing objects: 100% (9/9), 12.34 KiB | 12.34 MiB/s, done.
To github.com:user/s9.git
   abc1234..7a3f9e2  main -> main

✅ Commit and push successful!

Commit: 7a3f9e2
Message: feat(commands): add /commit command and skill [Agent: Administrator - Ishtar]
Files changed: 4 files
Branch: main
Pushed to: origin/main

Your changes are now in the remote repository!
```

**When to use:**
- ✅ You've completed a logical unit of work
- ✅ User says "commit my changes"
- ✅ User says "/commit"
- ✅ You want to save and push your work

**What it ensures:**
- ✅ QA checks pass (tests, linting, types)
- ✅ Task artifact is updated with implementation details
- ✅ Commit message follows Conventional Commits format
- ✅ Agent attribution is included
- ✅ Task reference `[Task: ID]` is included
- ✅ Changes are pushed to remote

---

#### `/handoff` - Hand Off to Another Persona

**Purpose:** Transfer work to another persona with full context and documentation.

**Usage:**
```
/handoff [Role]
```

**What it does:**
1. Identifies your current role and persona
2. Determines target role (or asks if not specified)
3. Gathers current state (git status, active tasks, recent commits)
4. Creates structured handoff document with:
   - What was done
   - Current state
   - What needs to be done next
   - Files to review
   - Approach and constraints
   - Acceptance criteria
5. Saves handoff as `.pending.md` file in `.opencode/work/missions/handoffs/`
6. Updates your mission file with handoff info
7. Provides instructions for recipient

**Example interaction:**
```
User: /handoff Engineer

Agent (Administrator - Ishtar): Creating handoff to Engineer...

Gathering current state...
- Branch: feature/query-caching
- Uncommitted: 0 files
- Active task: None
- Recent work: Created task H040, reviewed requirements

What should the Engineer focus on?

User: Implement database query caching for H040

Agent: Creating handoff document...

✅ Handoff created successfully!

**From:** Administrator (Ishtar)
**To:** Engineer (any)
**Created:** 2026-01-29 16:30:00

**Handoff Document:**
.opencode/work/missions/handoffs/2026-01-29.16:30:00.manager-ishtar.builder.pending.md

**Summary:**
- Task: H040 - Implement database query caching
- Priority: HIGH
- Estimated: 4-6 hours
- Approach: Redis-based caching with graceful degradation
- Files to review: 4 files
- Acceptance criteria: 7 items

**For Next Persona:**
When Engineer starts with `/summon`, they'll be notified of this handoff
and can read the full context.

**Your Options:**
- Continue working on other tasks
- Use `/dismiss` to end your mission
- Create another handoff if needed

Handoff document includes:
✅ Full context (what was done, current state)
✅ Clear task definition (H040 with details)
✅ Recommended approach (step-by-step)
✅ Files to review (with line numbers)
✅ Gotchas and constraints
✅ Acceptance criteria checklist
✅ Next steps for recipient
```

**When to use:**
- ✅ Administrator delegates implementation to Engineer
- ✅ Engineer hands off to Tester for validation
- ✅ Tester finds bugs and hands back to Engineer
- ✅ Engineer completes feature and hands to Inspector for review
- ✅ Any time work needs to transition between roles

**What gets handed off:**
- **Context:** What was done and why
- **State:** Current branch, files, tasks, commits
- **Task:** Specific task ID and requirements
- **Approach:** Recommended implementation strategy
- **Constraints:** Important limitations or requirements
- **Criteria:** How to know when it's done
- **Resources:** Files to review, docs to read, related work

**Handoff lifecycle:**
1. **Created (`.pending.md`)** - Waiting for recipient persona
2. **Accepted (`.accepted.md`)** - Recipient started work (via `/summon`)
3. **Completed (`.completed.md`)** - Work finished (via `/dismiss`)

**Integration with other commands:**
- `/summon` checks for pending handoffs and offers to accept them
- `/dismiss` marks accepted handoffs as completed
- `/claim-task` can be used after accepting handoff

---

## How It Works

### Command → Skill Flow

1. **User types command:** `/summon`
2. **OpenCode loads command file:** `.opencode/commands/summon.md`
3. **Command tells agent:** "Load the session-start skill"
4. **Agent calls skill tool:** `skill({ name: "session-start" })`
5. **OpenCode loads skill:** `.opencode/skills/session-start/SKILL.md`
6. **Agent follows skill instructions:** Role selection → naming → mission creation → doc reading

### Why This Design?

**Commands** provide:
- ✅ Easy discoverability (users can type `/` to see all commands)
- ✅ Simple invocation (just `/summon` instead of explaining the process)
- ✅ Consistent entry points across all personas

**Skills** provide:
- ✅ Detailed, step-by-step instructions
- ✅ Reusable across multiple commands if needed
- ✅ Version-controlled standardization
- ✅ Easy to update without changing command files

---

## Creating New Commands & Skills

Want to add more standardized workflows? Here's how:

### 1. Identify a Repetitive Workflow

Look for tasks that:
- Personas do repeatedly
- Have multiple steps
- Need consistency
- Can be standardized

**Examples:**
- Committing changes (run QA, update task artifact, format commit message)
- Creating architecture decisions (write ADR, update docs, link issues)
- Reviewing code (scan for issues, check patterns, generate report)
- Creating tasks (validate format, check dependencies, create files)

### 2. Create the Command File

**Location:** `.opencode/commands/your-command.md`

**Template:**
```markdown
---
description: Brief description of what this command does
agent: <optional-role-preference>
---

Load the <skill-name> skill and follow its instructions to <accomplish goal>.
```

**Example:** `.opencode/commands/commit.md`
```markdown
---
description: Commit changes following project standards
agent: builder
---

Load the commit-workflow skill and follow its instructions to commit the current changes.
```

### 3. Create the Skill File

**Location:** `.opencode/skills/<skill-name>/SKILL.md`

**Template:**
```markdown
---
name: skill-name
description: Brief description (1-2 sentences)
license: MIT
compatibility: opencode
metadata:
  audience: <target-agents>
  workflow: <workflow-type>
---

## What I Do

[Clear explanation of what this skill accomplishes]

## When to Use Me

[When should agents load this skill?]

## Step-by-Step Instructions

### Step 1: [First Action]
[Detailed instructions...]

### Step 2: [Second Action]
[Detailed instructions...]

## Important Notes

- [Key point 1]
- [Key point 2]

## Examples

[Show example usage if helpful]
```

### 4. Test the Command

1. Start OpenCode in the project
2. Type `/your-command`
3. Verify the agent loads the skill
4. Verify the agent follows the instructions
5. Check that the outcome is correct

### 5. Document It

Add your command to this README with:
- Command name and purpose
- Usage example
- What it does (step by step)
- Example interaction

---

## Best Practices

### For Commands

- ✅ Keep command files simple (just load the skill)
- ✅ Use descriptive command names (`/summon` not `/start`)
- ✅ Write clear descriptions for the TUI
- ✅ Specify agent if the command is role-specific

### For Skills

- ✅ Be explicit and detailed in instructions
- ✅ Include validation steps
- ✅ Show example commands with actual syntax
- ✅ Explain the "why" not just the "what"
- ✅ Include common gotchas and edge cases
- ✅ Keep instructions in logical order
- ✅ Use sections and headers for clarity

### For Both

- ✅ Test with actual personas before committing
- ✅ Keep instructions up to date
- ✅ Version control both files together
- ✅ Document in this README

---

## Skill Permissions

You can control which skills personas can access in `opencode.json`:

```json
{
  "permission": {
    "skill": {
      "*": "allow",              // Allow all skills by default
      "experimental-*": "ask"    // Ask before loading experimental skills
    }
  }
}
```

**Permission levels:**
- `allow` - Skill loads immediately
- `deny` - Skill is hidden and blocked
- `ask` - User is prompted for approval

Currently, all skills in this project use `allow` (no restrictions).

---

## Troubleshooting

### Command not showing up in TUI

- Verify file is in `.opencode/commands/`
- Verify filename is `<command-name>.md`
- Verify frontmatter has `description` field
- Restart OpenCode if needed

### Agent not loading skill

- Verify skill file is in `.opencode/skills/<name>/SKILL.md`
- Verify filename is exactly `SKILL.md` (all caps)
- Verify frontmatter has required `name` and `description` fields
- Verify `name` in frontmatter matches directory name
- Check permissions in `opencode.json`

### Skill name validation errors

Skill names must:
- Be 1-64 characters
- Be lowercase alphanumeric with single hyphen separators
- Not start or end with `-`
- Not contain consecutive `--`
- Match: `^[a-z0-9]+(-[a-z0-9]+)*$`

**Valid:** `session-start`, `commit-workflow`, `create-adr`
**Invalid:** `Session-Start`, `commit--workflow`, `-create-adr`, `adr-`

---

## Future Commands & Skills

Potential additions:

- `/create-adr` - Architecture decision record creation

Want to add one? Follow the guide above and submit a PR!

---

## Files

```
.opencode/
├── commands/              # Slash commands
│   ├── README.md         # This file
│   ├── summon.md         # /summon - Start mission
│   ├── dismiss.md        # /dismiss - End mission
│   ├── handoff.md        # /handoff - Hand off to another persona
│   ├── commit.md         # /commit - Commit & push changes
│   ├── tasks.md          # /tasks - Show task queue report
│   ├── create-task.md    # /create-task - Create new task
│   ├── claim-task.md     # /claim-task - Find & claim task
│   ├── update-task.md    # /update-task - Update progress
│   └── close-task.md     # /close-task - Close task
├── skills/               # Reusable instruction sets
│   ├── session-start/    # Session initialization skill
│   │   └── SKILL.md
│   ├── session-end/      # Session closure skill
│   │   └── SKILL.md
│   ├── handoff-workflow/ # Persona handoff skill
│   │   └── SKILL.md
│   ├── commit-workflow/  # Commit and push workflow
│   │   └── SKILL.md
│   ├── task-management/  # Task lifecycle skill
│   │   └── SKILL.md
│   └── tasks-report/     # Task queue report skill
│       └── SKILL.md
├── templates/            # Document templates
│   └── handoff-template.md  # Handoff document template
└── work/
    └── missions/
        └── handoffs/     # Persona handoff documents
            ├── *.pending.md   # Waiting for recipient
            ├── *.accepted.md  # Work in progress
            └── *.completed.md # Work finished
```

---

## See Also

- [OpenCode Commands Documentation](https://opencode.ai/docs/commands)
- [OpenCode Skills Documentation](https://opencode.ai/docs/skills)
- `.opencode/work/missions/README.md` - Mission file format
- `.opencode/tasks/README.md` - Task management system
