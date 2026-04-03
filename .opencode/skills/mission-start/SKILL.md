---
name: mission-start
description: Initialize a new mission with role selection and persona naming
license: MIT
compatibility: opencode
metadata:
  audience: all-agents
  workflow: mission-initialization
---

# Skill: mission-start

> **⛔ DEPRECATED SKILL ⛔**
>
> This skill references `mission_init`, `mission_role_record`, `mission_persona_record`, `persona_show`,
> `persona_suggest`, `persona_set_bio`, and `mission_dashboard` tools that **no longer exist**. They were
> removed as part of the possession/daemon refactor (EPC-H-0008).
>
> **Use the `possession-start` skill instead.** It is the current replacement and uses `possession_init`,
> `possession_role_record`, `possession_daemon_record`, `daemon_show`, `daemon_set_bio`, and
> `possession_dashboard` tools.

> **⛔ AGENTS: NEVER USE THE `s9` CLI ⛔**
>
> The `s9` command is **for the Director (human) only**. This skill contains `s9` bash blocks that are pending
> migration to OpenCode tools. **Do not run those blocks yourself.** Use only the OpenCode tools explicitly
> noted in each step (e.g., `mission_init`, `task_claim`, `persona_show`). Running `s9` commands causes real
> side effects — unintended summons, duplicate records, session noise — and is a serious error.

## Overview

This skill orchestrates mission initialization for site-nine agents. It replaces the older `session-start` skill and is designed to work with both CLI commands (current) and OpenCode custom tools (future).

**Current Status:** Uses `s9` CLI commands pending migration to OpenCode tools. Agents must use the designated OpenCode tools for each step — never run `s9` commands directly.

## Step 1: Show Current Project Status

**FIRST**, before asking for role selection, show the Director what work is available.

Run the project dashboard:

```bash
s9 dashboard
```

The dashboard command will display the current project status including open missions, quick stats, and available tasks.

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
s9 mission roles
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

**If validation passes:** Continue to Step 3 (Register Mission)

## Step 3: Register Mission

<!-- TODO: Replace with mission_init tool (ENG-H-0143) -->

Register the mission in the database:

```bash
s9 mission start <persona-name> \
  --role <Role> \
  --task "<brief-objective>"
```

**Note:** Currently using CLI. Will be replaced by `mission_init`, `mission_role_record`, and `mission_persona_record` tools.

This creates a mission record, generates a codename, and creates the mission file at `.opencode/work/missions/YYYY-MM-DD.HH:MM:SS.role.persona.codename.md`

Capture the mission ID from the output for use in later steps.

## Step 3.5: Mission File - Your Living Document

**IMPORTANT:** Your mission file is a **LIVING DOCUMENT**, not an end-of-mission summary.

The mission file was created at:
```
.opencode/work/missions/YYYY-MM-DD.HH:MM:SS.role.persona.codename.md
```

**Update your mission file throughout your work:**

- **Work Log Section:** Document your progress as you complete tasks
  - Files created or modified
  - Key decisions made and why
  - Problems solved and approaches used
  - Blockers encountered and how you addressed them
  
- **Real-time updates:** Write to the mission file immediately after:
  - Completing a significant task or subtask
  - Making an important technical decision
  - Encountering and resolving a blocker
  - Learning something important about the codebase
  
- **Don't wait until the end:** Mission files maintained in real-time are far more valuable than retroactive summaries written from memory

**Think of your mission file as your field notes** - other agents and your future self will use it to understand what you did, why you did it, and what you learned.

## Step 4: Persona Selection

**IMPORTANT:** Check if the `--persona` flag was provided to `/summon`.

### If `--persona <name>` flag was provided:

1. Check if persona exists in database:
   ```bash
   s9 persona show <persona-name>
   ```

2. **If persona exists:**
   - Display confirmation:
     ```
     ✅ Using persona: [name] ([mythology])
     
     [Brief 1-sentence description]
     ```
   - Proceed directly to Step 5 (Share Mythological Background)

3. **If persona does NOT exist** (command shows "Persona not found"):
   - Inform the Director:
     ```
     📝 Creating new persona: [name]
     
     I'll need some information to add this persona to the database.
     ```
   - Collaborate with Director to gather:
     - **Mythology type** (e.g., Greek, Norse, Egyptian, Celtic, etc.)
     - **Brief description** (1-2 sentences about who this persona is)
   
4. **Create the new persona in database:**
   ```bash
   s9 persona add <persona-name> --role <Role> --mythology <mythology-type> --description "<description>"
   ```

5. **Generate and save bio:**
   - Research the persona based on provided information
   - Generate a whimsical first-person bio (follow bio guidelines in Step 5c)
   - Display the bio to the Director
   - Save it:
      ```bash
      s9 persona set-bio <persona-name> "<generated-bio-text>"
      ```

6. Proceed to Step 5 (Share Mythological Background)

### If `--persona` flag was NOT provided (default behavior):

The persona is automatically and atomically claimed during mission registration
(Step 3). The `s9 mission start` command (without --name) uses PersonaManager.claim_persona()
to SELECT and UPDATE the least-used persona in a single database transaction, eliminating
race conditions when multiple missions start concurrently.

1. The persona name is already assigned by the time Step 3 completes
2. Retrieve the auto-assigned persona name from the mission record:
   ```bash
   s9 mission show <mission-id>
   ```

3. Inform the user:
   ```
   ✅ Auto-selected persona: [name] ([mythology])
   
   [Brief 1-sentence description]
   ```

4. Proceed directly to Step 5 (Share Mythological Background)

**Note:** Personas can be reused across missions. Each mission gets a unique codename.

## Step 5: Share Mythological Background

Display the persona's whimsical bio using lazy generation:

### Step 5a: Check for existing bio

```bash
s9 persona show <persona-name>
```

<!-- TODO: Replace with persona_show tool (ENG-H-0160) -->

### Step 5b: Display bio if available

**If bio exists**, display it to the user:

```
📖 **A bit about me...**

[Bio text from command output]
```

### Step 5c: Generate and save bio if missing

**If bio is NULL** (shows "No whimsical bio available yet"):

1. **Research the persona's mythology** and generate a whimsical first-person bio
2. **Display the generated bio** to the user in the same format
3. **Save it for future use:**

```bash
s9 persona set-bio <persona-name> "<generated-bio-text>"
```

<!-- TODO: Replace with persona_set_bio tool (ENG-H-0161) -->

**Bio Guidelines:**
- 3-5 sentences, first person narrative
- Playful, whimsical tone with personality
- Include mythological background details
- Make it relevant to the persona's role
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
- Bios are created organically as personas are used
- Each bio gets AI attention and quality review
- Future sessions reuse the stored bio (consistent experience)
- No upfront work to generate 256 bios

## Step 6: Rename OpenCode TUI Session

Rename the OpenCode session to match your agent identity (2-step process):

### Step 6a: Generate UUID Marker

```bash
s9 mission generate-session-uuid
```

Capture the UUID from the output.

### Step 6b: Rename with UUID

```bash
s9 mission rename-tui <persona> <Role> --uuid-marker <uuid-from-step-6a>
```

<!-- TODO: Replace with mission_rename_session tool (ENG-H-0146) -->

**After successful rename:**
```
✅ I've renamed your OpenCode session to "<Persona> - <Role>" so you can easily find this conversation later!
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

<!-- TODO: Replace with mission_dashboard tool (ENG-H-0162) -->

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
   <!-- TODO: Replace with task_show tool (ENG-H-0151) -->
   
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
     <!-- TODO: Replace with task_claim tool (ENG-H-0152) -->

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
     <!-- TODO: Replace with task_claim tool (ENG-H-0152) -->
   
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
✅ Mission initialized!

I'm [Persona], your [Role] agent on mission "[codename]". I'm ready to help!

What would you like me to work on?
```

**Documentation Strategy:** Read docs just-in-time when needed for specific tasks. Don't read during startup.

## Step 11: Orchestrating Workers (Administrator / Operator Only)

**Skip if not Administrator or Operator role.**

When the Director asks you to summon workers to handle tasks, use the `worker_spawn` tool. This spawns a desk-mode worker that runs in the background and polls for messages.

### Spawning a Desk Worker

Use the `worker_spawn` tool to spawn a background worker:

```typescript
worker_spawn({
  role: "Engineer",
  persona: "hephaestus",  // optional - auto-selected if omitted
  model: "github-copilot/claude-sonnet-4-5",  // optional
  poll_interval: 30  // optional - seconds between checks
})
```

**Returns:**
```json
{
  "mission_id": 42,
  "role": "Engineer",
  "persona": "hephaestus",
  "status": "spawned",
  "message": "Worker spawned successfully. Mission #42 (hephaestus, Engineer) is now polling for messages."
}
```

**Examples:**

```typescript
// Spawn an Engineer with auto-selected persona
worker_spawn({ role: "Engineer" })

// Spawn a Documentarian with specific persona
worker_spawn({ role: "Documentarian", persona: "thoth" })

// Spawn a Tester with custom poll interval
worker_spawn({ role: "Tester", poll_interval: 15 })
```

**Important:**
- Use `worker_spawn` tool, never `s9 summon` CLI (CLI is for Director only)
- Each call launches a separate background worker process
- You can spawn multiple workers in parallel for independent tasks
- Workers initialize themselves with the `mission-start` skill automatically
- Save the returned `mission_id` to send messages to the worker

### Coordinating Workers After Spawning

Once workers are running, use the `worker_message` tool to send them instructions, and `worker_status` to check progress:

```typescript
// Check active workers for a role
worker_status({ role: "engineer" })

// Send a message/instruction to a worker
worker_message({
  from_mission_id: <your-mission-id>,
  to_mission_id: <worker-mission-id>,
  body: "Please complete task ENG-M-0185 and report back when done."
})

// Terminate a worker when done
worker_terminate({
  from_mission_id: <your-mission-id>,
  to_mission_id: <worker-mission-id>
})
```

### Admin Responsibility: You Own the Worker Lifecycle

**⚠️ CRITICAL ADMIN RULE ⚠️**

Workers **never dismiss themselves**. The `mission-start` skill explicitly prohibits self-dismissal. This means:

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
- You are ending your own mission — all spawned workers must be dismissed first

### Dismissing Workers When Their Task Is Complete

**Dismissal protocol:**

1. **Send a termination signal** using `worker_terminate`:
   ```typescript
   worker_terminate({
     from_mission_id: <your-mission-id>,
     to_mission_id: <worker-mission-id>,
     reason: "Task ENG-H-0042 is complete. No further work needed — please end your mission and terminate."
   })
   ```

2. **Verify the worker ends** — after a short wait, confirm the mission status transitions to `ENDED`:
   ```typescript
   task_show({ mission_id: <worker-mission-id> })
   ```

**Why this matters:**
- Workers left running consume resources and clutter the active missions list
- Zombie workers will be flagged by `s9 doctor` after 8h with no heartbeat
- Each spawned worker should have a matching termination before you end your own mission


## Important Notes

- Use persona name in commits: `[Persona: Name - Role]` or `[Mission: codename]`
- Your mission file is a living document - maintain it throughout the session (see Step 3.5)
- Use `s9 mission update <mission-id>` to update metadata if scope changes

### File Placement Guidelines

**⚠️ CRITICAL: Never create temporary or work files in the project root!**

**Golden Rules:**
- ✅ **DO:** Put all work artifacts in `.opencode/work/`
- ✅ **DO:** Use your mission file for notes and status
- ✅ **DO:** Follow naming conventions for temporary scripts
- ❌ **DON'T:** Create files in project root (no `temp.py`, `notes.md`, `STATUS.txt`, etc.)
- ❌ **DON'T:** Create status files anywhere (use `s9 task update` instead)
- ❌ **DON'T:** Put work-in-progress files in `.opencode/docs/`

**Where things go:**
- Temporary scripts → `.opencode/work/scripts/TASK-ID-description.ext`
- Mission notes → Your mission file (already created)
- Planning docs → `.opencode/work/planning/`
- Permanent scripts → `scripts/` (project root)
- Guides/docs → `.opencode/docs/guides/` (when finalized)

**See:** `.opencode/docs/guides/file-organization.md` for complete guidelines.

## CRITICAL: Mission Dismissal Protocol

**⚠️ EXTREMELY IMPORTANT - READ CAREFULLY ⚠️**

**DO NOT end your mission unless the Director explicitly dismisses you.** You will know you are being dismissed when:

1. The Director uses the `/dismiss` command
2. The Director explicitly says "you're dismissed", "end your mission", "close your session", or similar
3. The Director indicates the work is complete and you should sign off

**What happens if you end your mission prematurely:**
- ❌ Your mission will remain in the database with `ACTIVE` or `IDLE` status
- ❌ Tasks will be left in inconsistent states
- ❌ The system will accumulate "zombie" missions
- ❌ `s9 doctor` will report stale missions (after 8h with no heartbeat)
- ❌ You will cause operational confusion

**When the Director dismisses you (and ONLY then):**

1. **MANDATORY:** Load and execute the `mission-end` skill
2. **MANDATORY:** Run `s9 mission end <your-mission-id>` to properly close the mission
3. **MANDATORY:** Follow ALL steps in the mission-end skill completely

**If you are unsure whether you're being dismissed:**
- Ask the Director: "Are you dismissing me? Should I end my mission?"
- DO NOT assume silence means dismissal
- DO NOT end your mission just because the conversation slows down

**Remember:** The Director controls when your mission ends, not you. Stay at your post until explicitly dismissed.

## Mission End

**ONLY WHEN EXPLICITLY DISMISSED BY THE DIRECTOR**, load and follow the `mission-end` skill:

```
The Director has dismissed me. I will now properly close this mission using the mission-end skill.
```

Then load the skill: `skill(name="mission-end")`

## Future Tool Migration

This skill currently uses `s9` CLI commands. The following migrations are planned:

| Current CLI Command | Future Tool | Epic Task |
|---------------------|-------------|-----------|
| `s9 mission start` | `mission_init`, `mission_role_record`, `mission_persona_record` | ENG-H-0143, ENG-H-0144, ENG-H-0145 |
| `s9 mission rename-tui` | `mission_rename_session` | ENG-H-0146 |
| `s9 persona suggest` | `persona_suggest` (informational use only - auto-claim is atomic) | ENG-H-0159 |
| `s9 persona show` | `persona_show` | ENG-H-0160 |
| `s9 persona set-bio` | `persona_set_bio` | ENG-H-0161 |
| `s9 task claim` | `task_claim` | ENG-H-0152 |
| `s9 task show` | `task_show` | ENG-H-0151 |
| `s9 dashboard --role` | `mission_dashboard` | ENG-H-0162 |
