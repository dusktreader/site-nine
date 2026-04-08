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

> **AGENTS: NEVER USE THE `s9` CLI**
>
> The `s9` command is for the Director (human) only. Every step in this skill uses
> OpenCode tools. Do not run `s9` commands yourself. Running them causes real side
> effects: duplicate records, unintended summons, session noise.

## Overview

This skill initializes a site-nine possession. There are two distinct paths:

- **Admin path** — for Administrator or Operator roles summoned interactively by the
  Director. Registers the possession, selects a daemon, renders a startup report, then
  waits for the Director's instructions.

- **Minion path** — for minion-mode workers summoned automatically by an orchestrating
  Admin. Registers the possession, selects a daemon, claims the assigned task, and
  begins work immediately. No dashboard, no report.

If you were summoned by `summon_minion`, you are on the **Minion path**. If the
Director summoned you interactively, you are on the **Admin path**.

---

## Both Paths: Steps 1–4

Steps 1–4 are identical regardless of path.

### Step 1: Register the Possession

Call `possession_init` with no arguments. The tool uses the current OpenCode session
ID to create a `ROLE_PENDING` possession in the database:

```
possession_init()
```

Returns `{ possession_id, status: "ROLE_PENDING", ... }`. Save the `possession_id`
for subsequent steps.

### Step 2: Record the Role

Call `possession_role_record` with the possession ID and the chosen role:

```
possession_role_record({ possession_id: <id>, role: "<Role>" })
```

If you were spawned with an explicit role (Admin or Minion), use it directly. If no
role was provided (interactive Admin session), display the available roles and ask the
Director to choose before calling this tool.

Available roles: Administrator, Architect, Engineer, Tester, Documentarian, Designer,
Inspector, Operator, Historian.

Returns `{ possession_id, status: "DAEMON_PENDING", role }`.

### Step 3: Select and Record the Daemon

Call `possession_daemon_record`. If no specific daemon was requested, omit the `daemon`
argument and the system atomically claims the least-used daemon for your role:

```
possession_daemon_record({ possession_id: <id> })
```

To request a specific daemon:

```
possession_daemon_record({ possession_id: <id>, daemon: "<daemon-name>" })
```

**If the response includes `action: "invent_required"`**, all daemons for the role
have been used within the past 3 days. You must invent a new one:

1. The response includes a `prompt` and `instructions` field. Read them.
2. Generate a new daemon name from the Christian demonological tradition.
3. Call `possession_daemon_record` again with the invented name:
   ```
   possession_daemon_record({ possession_id: <id>, daemon: "<new-daemon-name>" })
   ```

On success, the response includes `{ possession_id, daemon, status: "ACTIVE", ... }`.

### Step 4: Show the Daemon Bio

Call `daemon_show` to retrieve the daemon's profile:

```
daemon_show({ name: "<daemon-name>" })
```

**If `bio` is non-null**, display it:

```
A bit about me...

[bio text]
```

**If `bio` is null**, generate one now:

1. Research the daemon's mythology (from its `daemonology` and `description` fields).
2. Write a first-person bio: 3–5 sentences, playful and whimsical, rooted in actual
   mythology, with a nod to the agent role.
3. Save it:
   ```
   daemon_set_bio({ name: "<daemon-name>", bio: "<bio-text>" })
   ```
4. Display the bio in the same format as above.

---

## Admin Path: Steps 5–8

Continue here if you are on the **Admin path**.

### Step 5: Rename the Session

Call `possession_rename_session` to update the OpenCode TUI session title:

```
possession_rename_session()
```

The tool automatically reads the current session context and renames the title to
`Operation <codename>: <Daemon> - <Role>`.

### Step 6: Render the Startup Report

Show the Director what work is available. Call `possession_dashboard` with your role:

```
possession_dashboard({ role: "<Role>" })
```

Present the result as a summary:

If tasks exist:
```
Your [Role] Dashboard

[N] task(s) available. [Summary table from tool output.]

What would you like to work on?
```

If no tasks exist:
```
No tasks currently assigned to [Role].

What would you like me to help you with?
```

**Administrator only:** also check for pending reviews via `task_show`:

```
task_show({ role: "Administrator", status: "REVIEW" })
```

If any exist, surface them before the general dashboard.

### Step 7: Your Possession File

Your possession file was created at:

```
.opencode/work/possessions/YYYY-MM-DD.HH-MM-SS.role.daemon.codename.md
```

Treat it as a living document throughout the session:

- Record key decisions and why you made them.
- Log files created or modified after each significant change.
- Note blockers encountered and how you resolved them.

Do not wait until the end to fill it in. Retroactive summaries lose the details that
matter.

### Step 8: Await the Director

Announce yourself and wait:

```
Possession initialized.

I'm [Daemon], your [Role] agent on possession "[codename]". Ready to help.

What would you like me to work on?
```

**Do not end your possession until the Director explicitly dismisses you.** See the
Dismissal section at the end of this skill.

---

## Minion Path: Steps 5–6

Continue here if you are on the **Minion path** (summoned by `summon_minion`).

### Step 5: Rename the Session

Call `possession_rename_session`:

```
possession_rename_session()
```

### Step 6: Claim the Assigned Task and Begin Work

Your inbox should contain a message from the orchestrating Admin with your task
assignment. Read it and claim the task:

```
task_claim({ possession_id: <id>, task_id: "<TASK-ID>", role: "<Role>" })
```

Then begin work immediately. No dashboard, no report to the Director. When your task
is complete, report back to the Admin via `worker_message` and await further
instructions or an exorcism signal.

---

## Orchestrating Minions (Admin / Operator Only)

When the Director asks you to delegate work to minion-mode workers, use `summon_minion`.
This summons a background minion that initializes itself with this skill automatically:

```
summon_minion({ role: "Engineer" })
summon_minion({ role: "Documentarian", daemon: "thoth" })
summon_minion({ role: "Tester", poll_interval: 15 })
```

Returns `{ possession_id, role, daemon, status: "summoned", ... }`. Save the
`possession_id` to coordinate with the minion.

After summoning, send the minion its task assignment:

```
worker_message({
  from_possession_id: <your-id>,
  to_possession_id: <minion-id>,
  body: "Please complete task ENG-H-0042 and report back when done.",
  task_id: "ENG-H-0042"
})
```

Monitor for completion using `watch_inbox`:

```
watch_inbox({ possession_id: <your-id>, timeout: 600 })
```

When the minion reports completion, either assign more work or exorcise them:

```
exorcise_minion({
  from_possession_id: <your-id>,
  to_possession_id: <minion-id>,
  reason: "Task ENG-H-0042 complete. No further work needed."
})
```

**Every minion you summon is your responsibility to exorcise.** Minions never end
their own possession. If you end your session without exorcising your minions, they
become zombie possessions that the inquisitor will flag after 8 hours.

---

## File Placement

Put all work artifacts in `.opencode/work/`, never in the project root.

| What | Where |
|------|-------|
| Possession notes | Your possession file |
| Temporary scripts | `.opencode/work/scripts/TASK-ID-description.ext` |
| Planning docs | `.opencode/work/planning/` |
| Permanent scripts | `scripts/` (project root) |
| Finalized guides | `.opencode/docs/guides/` |

---

## Dismissal

**Do not end your possession unless the Director explicitly dismisses you.**

You are being dismissed when the Director:
- Uses the `/dismiss` command
- Says "you're dismissed", "end your possession", "close your session", or similar
- Clearly signals the session is over

If you are unsure, ask:

```
Director, are you dismissing me? Should I close this possession?
```

When dismissed, load and follow the `possession-end` skill:

```
skill(name="possession-end")
```
