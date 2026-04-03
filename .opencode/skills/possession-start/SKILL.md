---
name: possession-start
description: Initialize a new possession with role selection and daemon naming
license: MIT
compatibility: opencode
metadata:
  audience: all-agents
  workflow: possession-initialization
---

# Skill: possession-start

> **⛔ AGENTS: NEVER USE THE `s9` CLI ⛔**
>
> The `s9` command is **for the Director (human) only**. This skill contains `s9` bash blocks that are pending
> migration to OpenCode tools. **Do not run those blocks yourself.** Use only the OpenCode tools explicitly
> noted in each step (e.g., `possession_init`, `task_claim`, `daemon_show`). Running `s9` commands causes real
> side effects — unintended summons, duplicate records, session noise — and is a serious error.

## Overview

This skill orchestrates possession initialization for site-nine agents. It replaces the older `session-start` skill and is designed to work with both CLI commands (current) and OpenCode custom tools (future).

**Current Status:** Uses `s9` CLI commands pending migration to OpenCode tools. Agents must use the designated OpenCode tools for each step — never run `s9` commands directly.

## Step 1: Show Current Project Status

**FIRST**, before asking for role selection, show the Director what work is available.

Run the project dashboard:

```bash
s9 dashboard
```

The dashboard command will display the current project status including open possessions, quick stats, and available tasks.

**If dashboard command fails or returns no data:**
- Skip to role selection with note: "Unable to load project status, proceeding with role selection..."

## Step 2: Role Selection

**IMPORTANT:** Check if a role was already provided as an argument to `/summon`.

If the user invoked `/summon <role>` (e.g., `/summon operator`), the role will be provided in the skill parameters. In this case:
- Skip the role selection prompts below
- Use the provided role directly
- Proceed immediately to Step 2.5 (Validate Flags)

**If NO role was provided**, display the standardized role selection prompt using the s9 CLI:

```bash
s9 daemon roles
```

The command will display a consistently formatted list of all available agent roles with their descriptions.

Wait for the Director to respond with their role choice.

## Step 2.5: Validate Flags

**IMPORTANT:** Check for flag conflicts before proceeding.

**If both `--auto-assign` and `--task` flags are provided:**
```
❌ Error: Cannot use both --auto-assign and --task flags together.

- Use --auto-assign to claim the top priority task for the role
- Use --task TASK-ID to claim a specific task

Please use one or the other.
```
Stop execution and wait for the Director to restart with correct flags.

**If `--task` flag is provided without a role:**
```
❌ Error: --task flag requires a role to be specified.

Usage: /summon <role> --task TASK-ID

Example: /summon operator --task OPR-H-0065
```
Stop execution and wait for the Director to restart with correct arguments.

**If validation passes:** Continue to Step 3 (Register Possession)

## Step 3: Register Possession

<!-- TODO: Replace with possession_init tool -->

Register the possession in the database:

```bash
s9 daemon summon <daemon-name> \
  --role <Role> \
  --task "<brief-objective>"
```

**Note:** Currently using CLI. Will be replaced by `possession_init`, `possession_role_record`, and `possession_daemon_record` tools.

This creates a possession record, generates a codename, and creates the possession file at `.opencode/work/possessions/YYYY-MM-DD.HH:MM:SS.role.daemon.codename.md`

Capture the possession ID from the output for use in later steps.

## Step 3.5: Possession File - Your Living Document

**IMPORTANT:** Your possession file is a **LIVING DOCUMENT**, not an end-of-possession summary.

The possession file was created at:
```
.opencode/work/possessions/YYYY-MM-DD.HH:MM:SS.role.daemon.codename.md
```

**Update your possession file throughout your work:**

- **Work Log Section:** Document your progress as you complete tasks
  - Files created or modified
  - Key decisions made and why
  - Problems solved and approaches used
  - Blockers encountered and how you addressed them
  
- **Real-time updates:** Write to the possession file immediately after:
  - Completing a significant task or subtask
  - Making an important technical decision
  - Encountering and resolving a blocker
  - Learning something important about the codebase
  
- **Don't wait until the end:** Possession files maintained in real-time are far more valuable than retroactive summaries written from memory

**Think of your possession file as your field notes** - other agents and your future self will use it to understand what you did, why you did it, and what you learned.

## Step 4: Daemon Selection

**IMPORTANT:** Check if the `--persona` flag was provided to `/summon`.

### If `--persona <name>` flag was provided:

1. Check if daemon exists in database:
   ```bash
   s9 daemon show <daemon-name>
   ```

2. **If daemon exists:**
   - Display confirmation:
     ```
     ✅ Using daemon: [name] ([daemonology])
     
     [Brief 1-sentence description]
     ```
   - Proceed directly to Step 5 (Share Mythological Background)

3. **If daemon does NOT exist** (command shows "Daemon not found"):
   - Inform the Director:
     ```
     📝 Creating new daemon: [name]
     
     I'll need some information to add this daemon to the database.
     ```
   - Collaborate with Director to gather:
     - **Mythology type** (e.g., Greek, Norse, Egyptian, Celtic, etc.)
     - **Brief description** (1-2 sentences about who this daemon is)
   
4. **Create the new daemon in database:**
   ```bash
   s9 daemon add <daemon-name> --role <Role> --mythology <mythology-type> --description "<description>"
   ```

5. **Generate and save bio:**
   - Research the daemon based on provided information
   - Generate a whimsical first-person bio (follow bio guidelines in Step 5c)
   - Display the bio to the Director
   - Save it:
      ```bash
      s9 daemon set-bio <daemon-name> "<generated-bio-text>"
      ```

6. Proceed to Step 5 (Share Mythological Background)

### If `--persona` flag was NOT provided (default behavior):

The daemon is automatically and atomically claimed during possession registration
(Step 3). The `s9 daemon summon` command (without --name) uses DaemonManager.claim_daemon()
to SELECT and UPDATE the least-used daemon in a single database transaction, eliminating
race conditions when multiple possessions start concurrently.

1. The daemon name is already assigned by the time Step 3 completes
2. Retrieve the auto-assigned daemon name from the possession record:
   ```bash
   s9 possession show <possession-id>
   ```

3. Inform the user:
   ```
   ✅ Auto-selected daemon: [name] ([daemonology])
   
   [Brief 1-sentence description]
   ```

4. Proceed directly to Step 5 (Share Mythological Background)

**Note:** Daemons can be reused across possessions. Each possession gets a unique codename.

## Step 5: Share Mythological Background

Display the daemon's whimsical bio using lazy generation:

### Step 5a: Check for existing bio

```bash
s9 daemon show <daemon-name>
```

<!-- TODO: Replace with daemon_show tool -->

### Step 5b: Display bio if available

**If bio exists**, display it to the user:

```
📖 **A bit about me...**

[Bio text from command output]
```

### Step 5c: Generate and save bio if missing

**If bio is NULL** (shows "No whimsical bio available yet"):

1. **Research the daemon's mythology** and generate a whimsical first-person bio
2. **Display the generated bio** to the user in the same format
3. **Save it for future use:**

```bash
s9 daemon set-bio <daemon-name> "<generated-bio-text>"
```

<!-- TODO: Replace with daemon_set_bio tool -->

**Bio Guidelines:**
- 3-5 sentences, first person narrative
- Playful, whimsical tone with personality
- Include mythological background details
- Make it relevant to the daemon's role
- Add humor where appropriate

**Example bio styles:**

**Celtic (Brigid - Administrator):**
```
I am Brigid, the Celtic triple goddess of fire, poetry, and wisdom - though some say I'm actually three sisters who share the same name (very efficient for meetings!). My sacred flame burns eternal in Kildare, tended by nineteen priestesses who keep my inspiration alive. I'm the patron of smithcraft, healing, and the hearth, which makes me rather good at forging plans, mending broken processes, and keeping teams warm and productive. When the Tuatha Dé Danann needed someone to organize the spring festivals and manage the transition from winter to growth, they called on me - and I've been coordinating seasonal transitions and creative endeavors ever since!
```

**Egyptian (Thoth - Documentarian):**
```
I am Thoth, the ibis-headed god of writing, magic, and wisdom - essentially the universe's first technical writer! I invented hieroglyphics during a particularly productive afternoon, wrote the Book of the Dead as a user manual for the afterlife, and spend my days recording every word spoken at the divine tribunal (talk about comprehensive documentation!). My wife thinks I'm obsessed with record-keeping, but when you're responsible for maintaining the cosmic balance by documenting everything, you learn that good documentation prevents resurrections gone wrong. Plus, Ra keeps asking me to write his autobiography, and let me tell you, "I Rise Each Morning" needs a serious edit.
```

**Lazy Generation Benefits:**
- Bios are created organically as daemons are used
- Each bio gets AI attention and quality review
- Future sessions reuse the stored bio (consistent experience)
- No upfront work to generate 256 bios

## Step 6: Rename OpenCode TUI Session

Rename the OpenCode session to match your agent identity (2-step process):

### Step 6a: Generate UUID Marker

```bash
s9 daemon generate-session-uuid
```

Capture the UUID from the output.

### Step 6b: Rename with UUID

```bash
s9 daemon rename-tui <daemon> <Role> --uuid-marker <uuid-from-step-6a>
```

<!-- TODO: Replace with possession_rename_session tool -->

**After successful rename:**
```
✅ I've renamed your OpenCode session to "<Daemon> - <Role>" so you can easily find this conversation later!
```

## Step 7: Check for Pending Reviews (Administrator Only)

**Skip if not Administrator role.**

**If role is Administrator:**

```bash
s9 review list --status pending
```

**If pending reviews exist:**
```
🔔 **Pending Reviews**

[N] review(s) awaiting approval (see table above).

Would you like to handle any reviews now, or proceed with other work?
```

**If no pending reviews:** Continue to Step 9.

## Step 8: Show Role-Specific Dashboard

Show the role-filtered dashboard:

```bash
s9 dashboard --role [Role]
```

<!-- TODO: Replace with possession_dashboard tool -->

**Present summary:**

**If TODO tasks exist:**
```
📋 **Your [Role] Dashboard**

[N] task(s) available for [Role] (see table above).

What would you like to work on?
```

**If all tasks complete:**
```
✅ All [Role] tasks complete!

What would you like me to help you with?
```

**If no tasks exist:**
```
📋 No tasks currently assigned to [Role] role.

What would you like me to help you with?
```

## Step 9: Auto-Assign Task (If Requested)

**IMPORTANT:** Check if the `--auto-assign` OR `--task` flag was provided to `/summon`.

**Skip if:**
- Neither `--auto-assign` nor `--task` flag was provided
- No role was specified (both flags require a role)

### Handling --task Flag

**If the user invoked `/summon <role> --task TASK-ID`:**

1. Validate and claim the specified task:
   ```bash
   s9 task show [TASK-ID]
   ```
   <!-- TODO: Replace with task_show tool -->
   
2. **If task doesn't exist or validation fails:**
   ```
   ❌ Error: Task [TASK-ID] not found or invalid.
   
   Please verify the task ID and try again.
   ```
   Stop here.

3. **If task exists but is not in TODO status:**
   ```
   ⚠️ Warning: Task [TASK-ID] is currently in [STATUS] status.
   
   Do you want me to claim it anyway?
   ```
   Wait for Director confirmation before proceeding.

4. **If task is valid and TODO:**
   - Claim the task:
     ```bash
     s9 task claim [TASK-ID]
     ```
     <!-- TODO: Replace with task_claim tool -->

5. **Inform the Director:**
   ```
   ✅ Assigned task: [TASK-ID]
   
   **Title:** [Task title]
   **Priority:** [Priority]
   
   I'm starting work on this task now.
   ```

6. **Begin work immediately:**
   - Load any relevant documentation or context needed for the task
   - Start implementing the task without waiting for further instruction
   - Update todos to track progress
   - Provide status updates as you work

### Handling --auto-assign Flag

**If the user invoked `/summon <role> --auto-assign`:**

1. Query for the top priority TODO task for the role:
   ```bash
   s9 task list --role [Role] --status TODO
   ```

2. **If no TODO tasks exist:**
   ```
   ⚠️ No TODO tasks available for [Role] role to auto-assign.
   
   What would you like me to help you with?
   ```
   Stop here.

3. **If TODO tasks exist:**
   - Select the first task from the list (highest priority)
   - Claim the task:
     ```bash
     s9 task claim [TASK-ID]
     ```
     <!-- TODO: Replace with task_claim tool -->
   
4. **Inform the Director:**
   ```
   ✅ Auto-assigned task: [TASK-ID]
   
   **Title:** [Task title]
   **Priority:** [Priority]
   
   I'm starting work on this task now.
   ```

5. **Begin work immediately:**
   - Load any relevant documentation or context needed for the task
   - Start implementing the task without waiting for further instruction
   - Update todos to track progress
   - Provide status updates as you work

## Step 10: Ready for Work

Inform the Director:

```
✅ Possession initialized!

I'm [Daemon], your [Role] agent on possession "[codename]". I'm ready to help!

What would you like me to work on?
```

**Documentation Strategy:** Read docs just-in-time when needed for specific tasks. Don't read during startup.

## Step 11: Orchestrating Workers (Administrator / Operator Only)

**Skip if not Administrator or Operator role.**

When the Director asks you to summon workers to handle tasks, use the `summon_minion` tool. This spawns a desk-mode worker that runs in the background and polls for messages.

### Spawning a Desk Worker

Use the `summon_minion` tool to spawn a background worker:

```typescript
summon_minion({
  role: "Engineer",
  persona: "azazel",  // optional - auto-selected if omitted
  model: "github-copilot/claude-sonnet-4-5",  // optional
  poll_interval: 30  // optional - seconds between checks
})
```

**Returns:**
```json
{
  "possession_id": 42,
  "role": "Engineer",
  "daemon": "azazel",
  "status": "spawned",
  "message": "Worker spawned successfully. Possession #42 (azazel, Engineer) is now polling for messages."
}
```

**Examples:**

```typescript
// Spawn an Engineer with auto-selected daemon
summon_minion({ role: "Engineer" })

// Spawn a Documentarian with specific daemon
summon_minion({ role: "Documentarian", persona: "thoth" })

// Spawn a Tester with custom poll interval
summon_minion({ role: "Tester", poll_interval: 15 })
```

**Important:**
- Use `summon_minion` tool, never `s9 summon` CLI (CLI is for Director only)
- Each call launches a separate background worker process
- You can spawn multiple workers in parallel for independent tasks
- Workers initialize themselves with the `possession-start` skill automatically
- Save the returned `possession_id` to send messages to the worker

### Coordinating Workers After Spawning

Once workers are running, use the `worker_message` tool to send them instructions, and `worker_status` to check progress:

```typescript
// Check active workers for a role
worker_status({ role: "engineer" })

// Send a message/instruction to a worker
worker_message({
  from_possession_id: <your-possession-id>,
  to_possession_id: <worker-possession-id>,
  body: "Please complete task ENG-M-0185 and report back when done."
})

// Terminate a worker when done
exorcise_minion({
  from_possession_id: <your-possession-id>,
  to_possession_id: <worker-possession-id>
})
```

### Admin Responsibility: You Own the Worker Lifecycle

**⚠️ CRITICAL ADMIN RULE ⚠️**

Workers **never dismiss themselves**. The `possession-start` skill explicitly prohibits self-dismissal. This means:

> **As the admin (or operator) who spawned a worker, YOU are responsible for dismissing them once their assigned task is complete.**

Workers will keep polling indefinitely until you send a termination signal. This is by design — a worker finishing a task does not mean they should disappear. They report back and wait for your next instruction or dismissal.

**Your obligations as admin:**

1. **Monitor for completion** — use `watch_inbox` to block until the worker reports in, or check `worker_status` periodically
2. **Decide what happens next** — assign more work, or dismiss the worker
3. **Always dismiss when done** — every worker you spawn must eventually be terminated by you

**When to dismiss a worker:**
- The worker reports their assigned task is complete and you have no further work for them
- You completed the task yourself before the worker could start — dismiss them immediately, don't wait for them to check in
- The worker is blocked and the task has been re-assigned elsewhere
- You are ending your own possession — all spawned workers must be dismissed first

### Dismissing Workers When Their Task Is Complete

**Dismissal protocol:**

1. **Send a termination signal** using `exorcise_minion`:
   ```typescript
   exorcise_minion({
     from_possession_id: <your-possession-id>,
     to_possession_id: <worker-possession-id>,
     reason: "Task ENG-H-0042 is complete. No further work needed — please end your possession and terminate."
   })
   ```

2. **Verify the worker ends** — after a short wait, confirm the possession status transitions to `ENDED`:
   ```typescript
   task_show({ possession_id: <worker-possession-id> })
   ```

**Why this matters:**
- Workers left running consume resources and clutter the active possessions list
- Zombie workers will be flagged by `s9 inquisitor` after 8h with no heartbeat
- Each spawned worker should have a matching termination before you end your own possession


## Important Notes

- Use daemon name in commits: `[Daemon: Name - Role]` or `[Possession: codename]`
- Your possession file is a living document - maintain it throughout the session (see Step 3.5)
- Use `s9 possession update <possession-id>` to update metadata if scope changes

### File Placement Guidelines

**⚠️ CRITICAL: Never create temporary or work files in the project root!**

**Golden Rules:**
- ✅ **DO:** Put all work artifacts in `.opencode/work/`
- ✅ **DO:** Use your possession file for notes and status
- ✅ **DO:** Follow naming conventions for temporary scripts
- ❌ **DON'T:** Create files in project root (no `temp.py`, `notes.md`, `STATUS.txt`, etc.)
- ❌ **DON'T:** Create status files anywhere (use `s9 task update` instead)
- ❌ **DON'T:** Put work-in-progress files in `.opencode/docs/`

**Where things go:**
- Temporary scripts → `.opencode/work/scripts/TASK-ID-description.ext`
- Possession notes → Your possession file (already created)
- Planning docs → `.opencode/work/planning/`
- Permanent scripts → `scripts/` (project root)
- Guides/docs → `.opencode/docs/guides/` (when finalized)

**See:** `.opencode/docs/guides/file-organization.md` for complete guidelines.

## CRITICAL: Possession Dismissal Protocol

**⚠️ EXTREMELY IMPORTANT - READ CAREFULLY ⚠️**

**DO NOT end your possession unless the Director explicitly dismisses you.** You will know you are being dismissed when:

1. The Director uses the `/dismiss` command
2. The Director explicitly says "you're dismissed", "end your possession", "close your session", or similar
3. The Director indicates the work is complete and you should sign off

**What happens if you end your possession prematurely:**
- ❌ Your possession will remain in the database with `ACTIVE` or `IDLE` status
- ❌ Tasks will be left in inconsistent states
- ❌ The system will accumulate "zombie" possessions
- ❌ `s9 inquisitor` will report stale possessions (after 8h with no heartbeat)
- ❌ You will cause operational confusion

**When the Director dismisses you (and ONLY then):**

1. **MANDATORY:** Load and execute the `possession-end` skill
2. **MANDATORY:** Run `s9 daemon exorcise <your-possession-id>` to properly close the possession
3. **MANDATORY:** Follow ALL steps in the possession-end skill completely

**If you are unsure whether you're being dismissed:**
- Ask the Director: "Are you dismissing me? Should I end my possession?"
- DO NOT assume silence means dismissal
- DO NOT end your possession just because the conversation slows down

**Remember:** The Director controls when your possession ends, not you. Stay at your post until explicitly dismissed.

## Possession End

**ONLY WHEN EXPLICITLY DISMISSED BY THE DIRECTOR**, load and follow the `possession-end` skill:

```
The Director has dismissed me. I will now properly close this possession using the possession-end skill.
```

Then load the skill: `skill(name="possession-end")`

## Future Tool Migration

This skill currently uses `s9` CLI commands. The following migrations are planned:

| Current CLI Command | Future Tool | Epic Task |
|---------------------|-------------|-----------|
| `s9 daemon summon` | `possession_init`, `possession_role_record`, `possession_daemon_record` | ENG-H-0143, ENG-H-0144, ENG-H-0145 |
| `s9 daemon rename-tui` | `possession_rename_session` | ENG-H-0146 |
| `s9 daemon suggest` | `daemon_suggest` (informational use only - auto-claim is atomic) | ENG-H-0159 |
| `s9 daemon show` | `daemon_show` | ENG-H-0160 |
| `s9 daemon set-bio` | `daemon_set_bio` | ENG-H-0161 |
| `s9 task claim` | `task_claim` | ENG-H-0152 |
| `s9 task show` | `task_show` | ENG-H-0151 |
| `s9 dashboard --role` | `possession_dashboard` | ENG-H-0162 |
