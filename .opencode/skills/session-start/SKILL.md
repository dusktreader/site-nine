---
name: session-start
description: Initialize a new mission with role selection and persona naming
license: MIT
compatibility: opencode
metadata:
  audience: all-agents
  workflow: mission-initialization
---

## Important: CLI Tool Usage

**CRITICAL:** This project uses the `s9` CLI executable throughout these instructions.
- **CLI executable:** `s9` (use in bash commands)
- **Python module:** `site_nine` (use in Python imports: `from site_nine import ...`)

All commands in this skill use the `s9` executable via bash. You should NOT attempt to import an `s9` module in Python code.

### Installation Check

Before running any `s9` commands, verify it's properly installed:

```bash
s9 --help
```

**If this command fails with "command not found" or "ModuleNotFoundError":**

The most common cause is a stale `uv tool` installation. Fix it with:

```bash
uv tool uninstall site-nine
uv tool install --editable .
```

Then verify:
```bash
s9 --help
```

**Why this happens:** If site-nine was previously installed with the old module name `s9`, the entry point script may still reference the old import path. Reinstalling with `uv tool install --editable .` fixes this.

**Alternative if s9 is not available:** You can also use:
```bash
uv run s9 --help
```

This runs s9 using the project's virtual environment instead of the globally installed tool.

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

**If validation passes:** Continue to Step 3 (Persona Selection)

## Step 3: Persona Selection

**IMPORTANT:** Check if the `--persona` flag was provided to `/summon`.

### If `--persona <name>` flag was provided:

1. Check if persona exists in database:
   ```bash
   s9 name show <persona-name>
   ```

2. **If persona exists:**
   - Display confirmation:
     ```
     ✅ Using persona: [name] ([mythology])
     
     [Brief 1-sentence description]
     ```
   - Proceed directly to Step 4 (Register Mission)

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
   s9 name add <persona-name> --role <Role> --mythology <mythology-type> --description "<description>"
   ```

5. **Generate and save bio:**
   - Research the persona based on provided information
   - Generate a whimsical first-person bio (follow bio guidelines in Step 5c)
   - Display the bio to the Director
   - Save it:
     ```bash
     s9 name set-bio <persona-name> "<generated-bio-text>"
     ```

6. Proceed to Step 4 (Register Mission)

### If `--persona` flag was NOT provided (default behavior):

Automatically select the first unused persona name:

1. Get suggestions:
   ```bash
   s9 name suggest <Role> --count 3
   ```

2. Select the first unused name from the suggestions

3. Inform the user:
   ```
   ✅ Auto-selected persona: [name] ([mythology])
   
   [Brief 1-sentence description from suggestion]
   ```

4. Proceed directly to Step 4 (Register Mission)

**Note:** Personas can be reused across missions. Each mission gets a unique codename.

## Step 4: Register Mission

Register the mission in the database:

```bash
s9 mission start <persona-name> \
  --role <Role> \
  --task "<brief-objective>"
```

This creates a mission record, generates a codename, and creates the mission file at `.opencode/work/missions/YYYY-MM-DD.HH:MM:SS.role.persona.codename.md`

## Step 5: Share Mythological Background

Display the persona's whimsical bio using lazy generation:

### Step 5a: Check for existing bio

```bash
s9 name show <persona-name>
```

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
s9 name set-bio <persona-name> "<generated-bio-text>"
```

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

**After successful rename:**
```
✅ I've renamed your OpenCode session to "<Persona> - <Role>" so you can easily find this conversation later!
```

## Step 7: Check for Pending Handoffs

Check if there are pending handoffs for your role:

```bash
s9 handoff list --role [Role] --status pending
```

**If pending handoffs exist:**

1. **Show details of a handoff:**
   ```bash
   s9 handoff show <id>
   ```

2. **If user wants to accept it:**
   ```bash
   s9 handoff accept <id>
   ```
   
   This command requires an active mission (already done in Step 4).

3. **Summarize to user:**
   ```
   ✅ Handoff accepted!
   
   **From:** [From persona and role from handoff details]
   **Task:** [Task ID and title]
   **Priority:** [Priority]
   
   [Brief summary of what was handed off]
   
   Ready to start work on this task.
   ```

**If no pending handoffs:**
- Continue to Step 8

## Step 8: Check for Pending Reviews (Administrator Only)

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

## Step 9: Ready for Work

Inform the Director:

```
✅ Mission initialized!

I'm [Persona], your [Role] agent on mission "[codename]". I'm ready to help!

What would you like me to work on?
```

**Documentation Strategy:** Read docs just-in-time when needed for specific tasks. Don't read during startup.

## Step 10: Show Role-Specific Dashboard

Show the role-filtered dashboard:

```bash
s9 dashboard --role [Role]
```

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

## Step 11: Auto-Assign Task (If Requested)

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

## Important Notes

- Use persona name in commits: `[Persona: Name - Role]` or `[Mission: codename]`
- Update mission file throughout the session
- Use `s9 mission update <mission-id>` to update metadata if scope changes

## Mission End

When the Director indicates the mission is ending, load and follow the `session-end` skill:

```
Load the session-end skill to properly close this mission.
```
