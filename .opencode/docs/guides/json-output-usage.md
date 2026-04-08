# Structured Data from Tools

This guide explains how agents access structured site-nine data using OpenCode tools.

> **Note for Directors:** The `s9` CLI supports a `--json` flag for scripting and automation from the
> terminal. That is a Director-only feature. Agents must never run `s9` commands — they call OpenCode
> tools directly instead.


## Overview

Agents never parse shell output. Every site-nine operation has a dedicated OpenCode tool that returns
structured data as a typed result. There is no need for `--json` flags, `jq` parsing, or shell
variable capture.


## Querying Tasks

Use `task_show` to get task data. The tool accepts filters and returns authoritative database values.

```typescript
// All TODO tasks for your role
task_show({ role: "Engineer", status: "TODO" })

// A specific task by ID
task_show({ task_id: "ENG-H-0037" })

// Narrow by priority
task_show({ role: "Engineer", status: "TODO", priority: "HIGH" })
```

**Result shape (single task):**

```json
{
  "id": "ENG-H-0037",
  "title": "Implement ToolRegistry",
  "status": "TODO",
  "priority": "HIGH",
  "role": "Engineer",
  "epic_id": "EPC-H-0004",
  "description": "...",
  "possession_id": null
}
```

**Useful fields:**
- `status` — authoritative enum: `TODO`, `UNDERWAY`, `COMPLETE`, `ABORTED`. Report it verbatim.
- `possession_id` — non-null means the task is already claimed
- `priority` — for prioritization logic

**Do not re-categorize tool results.** If `task_show` returns a task with `status: "COMPLETE"`, it is
complete — do not move it to a different list because you expected otherwise.


## Checking Minion Status

Use `worker_status` to find active minions for a role:

```typescript
// Find active Engineer minions
worker_status({ role: "Engineer" })
```

**Result shape:**

```json
[
  {
    "possession_id": 62,
    "daemon": "daedalus",
    "role": "Engineer",
    "status": "ACTIVE"
  }
]
```

**Useful fields:**
- `possession_id` — use this to send messages via `worker_message`
- `status` — `ACTIVE` means the minion is running and available for messages

**Discovery pattern:**

```typescript
const minions = await worker_status({ role: "Architect" })

if (minions.length > 0) {
  // Minion is available — send a message
  worker_message({ to_possession_id: minions[0].possession_id, body: "..." })
} else {
  // Ask Director to summon an Architect
}
```


## Getting Your Task Dashboard

`possession_dashboard` is called once at possession start by the `possession-start` skill. It returns
your role-filtered view of available tasks.

```typescript
possession_dashboard({ role: "Engineer" })
```

Do not call `possession_dashboard` again during a session to find work. Use `task_show` with filters
instead — it queries the database directly and is faster.


## Generating Reports

Use `task_show` with `report: true` to get a summary report:

```typescript
task_show({ report: true })
```

**Use report mode only for presenting an overview to the Director.** Do not use it to find your next
task — use filtered `task_show` queries for that.


## Presenting Data to the Director

When the Director asks for a status update, present tool results naturally in prose or a table. You do
not need special formatting — just describe what the tool returned.

**Example:**

> `task_show({ role: "Engineer", status: "TODO" })` returned 3 tasks: ENG-H-0037 (HIGH), ENG-H-0041
> (MEDIUM), and ENG-H-0045 (LOW). I'll claim ENG-H-0037 first.


## Summary

| Need                        | Tool                                            |
|-----------------------------|-------------------------------------------------|
| Find available tasks        | `task_show({ role, status: "TODO" })`           |
| Get a specific task         | `task_show({ task_id: "..." })`                 |
| Find active minions         | `worker_status({ role: "..." })`                |
| Get possession dashboard    | `possession_dashboard({ role: "..." })`         |
| Generate a summary report   | `task_show({ report: true })`                   |


## See Also

- **Agent Discovery Guide**: `agent-discovery.md` — patterns for finding and messaging other agents
- **Admin Orchestration Guide**: `admin-orchestration.md` — coordinating minions via tools
- **Tasks Guide**: `tasks.md` — full task lifecycle workflow
