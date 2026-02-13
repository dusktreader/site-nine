---
description: Display project status dashboard with epics, tasks, and mission overview
---

Display the site-nine project dashboard showing current status.

## What to Display

Run the dashboard command to show:
- Active epics with their subtasks
- Available individual tasks
- Open missions
- Quick statistics

## Command

```bash
s9 dashboard
```

## Optional: Filtering

If the user specifies a role (e.g., `/dashboard operator`), filter by that role:

```bash
s9 dashboard --role $1
```

If the user specifies an epic (e.g., `/dashboard EPC-H-0004`), filter by that epic:

```bash
s9 dashboard --epic $1
```

## Presentation

After running the command:

1. Let the output speak for itself - the dashboard is already well-formatted
2. If the user is currently on a mission, briefly highlight relevant items for their role
3. If asked about specific items, provide additional context

## Examples

**Basic usage:**
```
/dashboard
```
Shows full project dashboard.

**Role-filtered:**
```
/dashboard Administrator
```
Shows only Administrator-relevant tasks.

**Epic-filtered:**
```
/dashboard EPC-H-0004
```
Shows only tasks for the specified epic.
