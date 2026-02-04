# Epics Overview

Epics are organizational containers that help Directors manage complex projects by grouping related tasks under larger initiatives. They provide visibility into overall progress while breaking down work into manageable pieces.


## What is an Epic?

An epic represents a high-level project or initiative composed of multiple related tasks. For example, "User Authentication System" might be an epic containing tasks for architecture design, API implementation, frontend integration, testing, and documentation.

Epics are purely organizational tools. They group tasks together for planning and tracking purposes, but aren't directly assigned to agents or worked on during missions. Instead, agents work on the individual tasks that belong to an epic, and the epic automatically tracks progress as those tasks are completed.


## Key Characteristics

Epics in site-nine have several important properties that distinguish them from tasks. Each task belongs to at most one epic (or remains standalone), keeping organizational structure simple. Epic status updates automatically based on subtask states - Directors never manually mark epics complete. The database serves as the source of truth, while markdown files in `.opencode/work/epics/` are generated artifacts that provide human-readable views. Progress tracking shows completion percentages and task counts at a glance, making it easy to understand project health.


## When to Use Epics

Epics work best for features requiring multiple roles working in sequence (architect → engineer → tester → documentarian), projects spanning multiple weeks, work requiring coordination across three or more tasks, and initiatives with clear milestones and deliverables.

They're not necessary for single-task work items, quick fixes or small changes, or tasks that naturally complete in isolation. If you find yourself creating an epic with only one or two tasks, consider whether the epic adds organizational value or just creates unnecessary overhead.


## Epic Lifecycle at a Glance

An epic begins when a Director creates it with a title and priority, typically during planning sessions with an Architect or Administrator agent. As tasks are created and linked to the epic, it automatically transitions to "TODO" status. When agents start working on tasks (moving them to "UNDERWAY"), the epic status automatically updates to reflect active work. Once all subtasks reach "COMPLETE" status, the epic automatically transitions to "COMPLETE" as well - no manual intervention needed.

If project requirements change or an initiative becomes obsolete, Directors can abort an epic, which cascades to all its subtasks and locks the epic to prevent future auto-updates.


## Epic Statuses

Epics move through four possible states, all automatically managed based on subtask progress:

**TODO** - All subtasks are either TODO or ABORTED. No active work has started yet.

**UNDERWAY** - At least one subtask is actively being worked on (in UNDERWAY, BLOCKED, REVIEW, or PAUSED status).

**COMPLETE** - All subtasks have been completed. This is a terminal state - completed epics don't transition to other statuses.

**ABORTED** - Manually aborted by a Director. All subtasks are also marked aborted. This is a protected terminal state that never auto-updates, even if subtask statuses change.


## Epic IDs

Epics use a structured ID format that encodes priority: `EPC-[P]-[NNNN]`, where `EPC` is the constant epic prefix, `[P]` is a single-letter priority code (C for CRITICAL, H for HIGH, M for MEDIUM, L for LOW), and `[NNNN]` is a sequential four-digit number padded with zeros.

For example, `EPC-H-0001` is the first HIGH priority epic, while `EPC-C-0015` is epic #15 with CRITICAL priority. This format makes it easy to identify critical work at a glance when scanning task lists or dashboards.


## How Epics Track Progress

Epic status and progress are computed automatically from subtask states. When all subtasks are complete, the epic becomes complete. When any subtask moves to active status, the epic shows as underway. This automatic tracking means Directors can focus on planning and monitoring rather than manually updating epic metadata.

Progress is shown as both a percentage and a task count (e.g., "3/5 tasks complete (60%)"), giving Directors quick insight into how much work remains.


## Next Steps

Learn how to [plan epics](planning.md) with agents using the TUI, understand how to [track progress](tracking.md) on active epics, and explore the structure of [epic files](files.md) to see what gets generated automatically versus what Directors can customize.
