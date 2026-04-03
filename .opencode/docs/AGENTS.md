# Site-Nine Agent Guide

> **⛔ AGENTS: NEVER USE THE `s9` CLI ⛔**
>
> The `s9` command-line tool is **for the Director (human) only**. Agents must **never** invoke it under any
> circumstances — not for task management, not for possessions, not for any reason.
>
> **Every site-nine operation has a dedicated OpenCode tool.** Use those tools exclusively:
> - Task work → `task_claim`, `task_update`, `task_close`, `task_show`
> - Possession lifecycle → `possession_init`, `possession_end`, `possession_dashboard`
> - Daemons → `daemon_show`, `daemon_set_bio`
> - Workers → `summon_minion`, `worker_message`, `exorcise_minion`
>
> Running `s9` commands causes real side effects (unintended summons, duplicate records, session noise) and will
> be treated as a serious error. If you see `s9` used in an example below, it describes what the **Director**
> does from the terminal — **you do not run those commands**.

Welcome to site-nine! This guide explains how to work as an agent in the site-nine development environment.


## Quick start

As an agent, your workflow is simple:

1. **Director summons you** via `s9 summon <role>` or `s9 summon <role> --daemon <name>`
2. **You initialize** by running the `possession-start` skill (happens automatically)
3. **You work** on tasks using custom tools (not CLI commands)
4. **Director dismisses you** via `/dismiss`, and you run the `possession-end` skill

**Key principle:** You use **OpenCode tools** to interact with site-nine. The `s9` CLI is for the Director only.


## Possession lifecycle


### Starting a possession

When the Director summons you, you'll receive an instruction like:

```
Your role is documentarian. Initialize your possession with the possession-start skill.
```

Or:

```
Your role is operator, your daemon is andromalius. Initialize your possession with the possession-start skill.
```

The `possession-start` skill handles all initialization:

- Creates your possession record (using `possession_init` tool)
- Records your role (using `possession_role_record` tool)
- Selects or confirms your daemon (using `possession_daemon_record` tool)
- Renames the session (using `possession_rename_session` tool)
- Shows your role-specific task dashboard

**You don't need to track your possession ID** — all tools automatically know which possession you're on via the
session context.


### Possession statuses

Your possession progresses through these states:

- **ROLE_PENDING** — Possession created, waiting for role selection
- **DAEMON_PENDING** — Role recorded, waiting for daemon selection
- **ACTIVE** — Fully initialized and working
- **SUSPENDED** — Session closed unexpectedly, possession paused
- **EXORCISED** — Possession ended


### Suspending and resuming

If your session closes unexpectedly, the Director can resume your possession with:

```bash
s9 possession resume <id>
```

**Note:** You don't need to worry about this — the automation handles it.


## Working with tasks


### Claiming tasks

Use the `task_claim` tool to claim tasks:

```typescript
task_claim({ task_id: "DOC-M-0106" })
```

The tool automatically:

- Associates the task with your current possession
- Updates the task status to UNDERWAY
- Records the claim timestamp


### Updating progress

Use the `task_update` tool to record progress notes:

```typescript
task_update({
  task_id: "DOC-M-0106",
  notes: "Created communication channels section in possession-start skill"
})
```


### Completing tasks

Use the `task_close` tool to close tasks:

```typescript
task_close({
  task_id: "DOC-M-0106",
  status: "COMPLETE",
  notes: "Added step explaining three communication channels with examples"
})
```

**Available statuses:**

- `COMPLETE` — Task finished successfully
- `ABORTED` — Task cancelled or no longer needed


## Using custom tools

Site-nine provides OpenCode custom tools for all operations. **Never use `s9` CLI commands** — they're for the
Director only.


### Possession tools

| Tool                      | Purpose                        | When used                          |
|---------------------------|--------------------------------|------------------------------------|
| `possession_init`         | Initialize new possession      | Auto-called by possession-start    |
| `possession_role_record`  | Set possession role            | Auto-called by possession-start    |
| `possession_daemon_record`| Set possession daemon          | Auto-called by possession-start    |
| `possession_rename_session` | Rename OpenCode session      | Auto-called by possession-start    |
| `possession_end`          | End current possession         | Called by possession-end skill     |
| `possession_summary`      | Get possession summary         | For status reporting               |
| `possession_dashboard`    | Get role-filtered dashboard    | See available tasks                |


### Task tools

| Tool           | Purpose                        | Example                                       |
|----------------|--------------------------------|-----------------------------------------------|
| `task_create`  | Create new task                | `task_create({ title: "...", role: "..." })`  |
| `task_show`    | Get task details               | `task_show({ task_id: "DOC-M-0106" })`        |
| `task_claim`   | Claim task for current possession | `task_claim({ task_id: "DOC-M-0106" })`    |
| `task_update`  | Update progress notes          | `task_update({ task_id: "...", notes: "..." })` |
| `task_close`   | Close task with status         | `task_close({ task_id: "...", status: "COMPLETE" })` |
| `task_release` | Release claimed task           | `task_release({ task_id: "..." })`            |


### Daemon tools

| Tool             | Purpose                  | Example                                      |
|------------------|--------------------------|----------------------------------------------|
| `daemon_suggest` | Get daemon suggestions   | `daemon_suggest({ role: "Documentarian" })`  |
| `daemon_show`    | Get daemon details       | `daemon_show({ name: "andromalius" })`       |
| `daemon_set_bio` | Save daemon bio          | `daemon_set_bio({ name: "...", bio: "..." })` |


### Messaging and coordination tools

Agents use messages to coordinate work and communicate explicitly:

| Tool               | Purpose                             | Example                                              |
|--------------------|-------------------------------------|------------------------------------------------------|
| `summon_minion`    | Spawn a desk-mode worker for a role | `summon_minion({ role: "Engineer" })`                |
| `worker_message`   | Send message to another possession  | `worker_message({ to_possession_id: 42, body: "..." })` |
| `worker_status`    | Check active workers for a role     | `worker_status({ role: "Engineer" })`                |
| `exorcise_minion`  | Signal a worker to end gracefully   | `exorcise_minion({ to_possession_id: 42 })`          |

**Key principles:**

- Admin orchestrates workers via `summon_minion` tool (never use `s9 summon` CLI)
- Admin assigns work explicitly via `worker_message` (not discovery patterns)
- Workers receive work assignments directly from Admin
- No polling or discovery — coordination is explicit and deterministic

**See:** `.opencode/docs/guides/desk-mode-orchestration.md` for complete orchestration patterns.


## Agent coordination

Site-nine uses a **Director → Admin → Workers** hierarchy for multi-agent work:

- **Director** (human) — summons agents, gives high-level goals, dismisses agents
- **Admin agent** — orchestrates workers, assigns tasks via messages, monitors progress
- **Worker agents** — run in desk mode, receive work assignments, report status back to Admin

Workers are invisible to the Director. The Admin manages them autonomously using tools.


### Admin orchestration

When the Director delegates complex work to you as Admin, you coordinate workers via tools:

1. **Spawn workers** with `summon_minion` — launches headless background sessions
2. **Assign work** with `worker_message` — send task instructions with full context
3. **Monitor progress** with `worker_status` — check active workers by role
4. **Wait for updates** with `watch_inbox` — block until a worker sends a response
5. **Terminate workers** with `exorcise_minion` — clean up when work is done

**See:** `.opencode/docs/guides/desk-mode-orchestration.md` for complete orchestration patterns.


### Finding other agents

Use the messaging system to coordinate with other agents asynchronously.

**Discovery pattern:**

1. Check for available agents using `worker_status`
2. Send message if agent is in desk mode via `worker_message`
3. Ask Director to summon agent if none available

**See:** `.opencode/docs/guides/agent-discovery.md` for complete patterns.


### Desk mode

Desk mode workers are headless background agents spawned by Admin:

- Workers process messages asynchronously
- Admin assigns work via `worker_message`
- Workers send status updates back to Admin
- Admin monitors via `worker_status` and `watch_inbox`

**See:** `.opencode/docs/guides/desk-mode-orchestration.md` for usage guide.


### Communication channels

You have three communication channels:

1. **OpenCode Chat (Agent ↔ Director)** — For immediate guidance, requesting agent summons, reporting blockers
2. **Messaging System (Agent ↔ Agent)** — For async technical questions, epic coordination, worker status updates
3. **Director Observation** — Director can view all messages but doesn't participate

**See:** `possession-start` skill for when to use each channel.


## Skills vs. tools

Understanding the difference is important:

### Skills

- Markdown documents with instructions
- Handle interactive, context-dependent decisions
- Guide you through multi-step workflows
- Located in `.opencode/skills/`

**Example skills:**

- `possession-start` — Initialize your possession
- `possession-end` — End your possession properly
- `task-claim` — Claim and start work on tasks
- `task-update` — Update task progress and notes


### Tools

- TypeScript functions you invoke
- Handle deterministic, repeatable operations
- Called directly as function invocations
- Located in `.opencode/tools/`

**Example tools:**

- `possession_init()` — Create possession record
- `task_claim({ task_id: "..." })` — Claim a task
- `possession_dashboard()` — Get task list

**Rule of thumb:** Skills tell you **what to do**, tools do the **actual work**.


## Workflow examples


### Standard task workflow

```
1. Director: s9 summon documentarian
2. You: Run possession-start skill
   → possession_init creates possession
   → possession_role_record sets role
   → possession_daemon_record sets daemon (auto-selected)
   → possession_rename_session renames session
   → possession_dashboard shows available tasks
3. You: Claim task
   → task_claim({ task_id: "DOC-M-0106" })
4. You: Work on task
5. You: Update progress
   → task_update({ task_id: "DOC-M-0106", notes: "..." })
6. You: Complete task
   → task_close({ task_id: "DOC-M-0106", status: "COMPLETE", notes: "..." })
7. Director: /dismiss
8. You: Run possession-end skill
   → possession_end() closes possession
```


### Admin orchestration workflow

```
1. Director: s9 summon administrator
2. Admin: Run possession-start skill
3. Admin: Spawn workers for needed roles
   → summon_minion({ role: "Engineer" })
   → summon_minion({ role: "Tester" })
   → Returns { possession_id: 83 } and { possession_id: 84 }
4. Admin: Assign work to Engineer
   → worker_message({ to_possession_id: 83, body: "Claim and complete ENG-H-0150" })
5. Admin: Wait for completion
   → watch_inbox()  # blocks until Engineer sends update
6. Admin: Engineer reports done → assign testing
   → worker_message({ to_possession_id: 84, body: "Validate ENG-H-0150 implementation" })
7. Admin: Wait for test results
   → watch_inbox()
8. Admin: Terminate workers when done
   → exorcise_minion({ to_possession_id: 83 })
   → exorcise_minion({ to_possession_id: 84 })
9. Director: /dismiss Admin
10. Admin: Run possession-end skill
```


### Coordination workflow (peer-to-peer)

```
1. You (Engineer): Need Architect input
2. You: Check for available Architects
   → worker_status({ role: "Architect" })
3a. If Architect in desk mode:
    → worker_message({ to_possession_id: <id>, body: "Question about X..." })
    → Continue working while waiting for response
3b. If no Architect available:
    → Ask Director in chat: "Should I wait or would you like to summon an Architect?"
    → Director summons Architect
4. You: Coordinate via messaging or chat as needed
```


## Important notes


### What you should NOT do

❌ **Don't use `s9` CLI commands** — Use tools instead (e.g., `task_claim()` not `s9 task claim`)
❌ **Don't track possession IDs manually** — Tools automatically know your possession from session context
❌ **Don't send heartbeats** — The OpenCode plugin tracks activity automatically
❌ **Don't manually suspend possessions** — Plugin handles this when sessions close
❌ **Don't end possession without dismissal** — Wait for Director to dismiss you


### What you SHOULD do

✅ **Use tools for all operations** — They're designed for agents
✅ **Follow skills for guidance** — They orchestrate complex workflows
✅ **Check your task dashboard** — possession-start skill shows available work
✅ **Update task progress** — Use task_update tool to document work
✅ **Ask Director when unclear** — Use OpenCode chat for guidance
✅ **Coordinate with other agents** — Use messaging for async communication


## Documentation


### Essential guides

- **Task Management**: `.opencode/docs/guides/tasks.md`
- **Agent Discovery**: `.opencode/docs/guides/agent-discovery.md`
- **Desk Mode Orchestration**: `.opencode/docs/guides/desk-mode-orchestration.md`
- **JSON Output Usage**: `.opencode/docs/guides/json-output-usage.md`
- **Commit Guidelines**: `.opencode/docs/guides/commit-guidelines.md`
- **Markdown Style**: `.opencode/docs/guides/markdown-style.md` (REQUIRED for all markdown edits)


### Architecture

- **ADR-013**: Site-nine as OpenCode Integration Platform (this architecture)
- **ADR-009**: Agent Coordination Patterns
- **ADR-008**: Agent Messaging System
- **All ADRs**: `.opencode/docs/adrs/`


### Quick reference

- **All guides**: `.opencode/docs/guides/README.md`
- **Skills**: `.opencode/skills/`
- **Roles**: `.opencode/docs/roles/`


## Getting help

**During a possession:**

1. Check relevant guides in `.opencode/docs/guides/`
2. Ask the Director in OpenCode chat
3. Check ADRs for architecture decisions
4. Use agent discovery to find other agents

**If confused about workflow:**

- Re-read this guide (AGENTS.md)
- Check the possession-start skill for initialization steps
- Ask Director for clarification


## Summary

You are an agent working in the site-nine development environment. Your workflow is:

1. **Initialize** with possession-start skill (automatic when summoned)
2. **Work** using OpenCode custom tools (not CLI commands)
3. **Coordinate** via messaging system or Director chat
4. **End** with possession-end skill (when Director dismisses you)

The system automates lifecycle management, activity tracking, and possession persistence. You focus on the work —
the tools and skills handle the coordination.

**Remember:** Tools for operations, skills for guidance, Director for decisions.
