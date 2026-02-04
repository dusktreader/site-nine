# Tracking Epic Progress

Once an epic is created and tasks are underway, Directors can monitor progress through various tools and views. Epic status updates automatically as agents complete tasks, providing real-time visibility into project health.


## Viewing Epic Status

The primary way to check on an epic is through the dashboard. Agents can show epic details during conversations:

```
Director: Show me the status of the authentication epic
Agent: [displays epic dashboard showing progress, subtasks, and status]
```

The dashboard displays the epic's current status (TODO, UNDERWAY, COMPLETE, or ABORTED), priority level, progress as both percentage and task count (e.g., "3/5 tasks complete (60%)"), and a detailed table of all subtasks with their current statuses, assigned roles, and priorities.


## Understanding Progress Indicators

Epic progress is computed automatically from subtask states. The progress percentage represents the ratio of completed tasks to total tasks. A progress bar provides visual feedback, making it easy to assess completion at a glance. Task counts show exactly how many tasks remain (e.g., "3/5 complete" means 2 tasks still need work).

This automatic calculation means Directors never need to manually update epic progress - it always reflects the current reality based on what agents have actually completed.


## Monitoring Active Work

When an epic is in UNDERWAY status, the dashboard shows which tasks are actively being worked on, which are blocked or waiting for review, and which haven't been started yet. This visibility helps Directors understand where attention is needed and whether work is progressing smoothly.

If you notice tasks stuck in BLOCKED status, that's a signal to investigate what's blocking progress. If multiple tasks remain in TODO while one task is UNDERWAY, that might indicate a dependency chain or simply that agents are working sequentially.


## Epic Status Transitions

Epics automatically transition between states as agents work on tasks. When an agent claims their first task from an epic and moves it to UNDERWAY, the epic automatically transitions from TODO to UNDERWAY. When agents complete the last remaining task, the epic automatically transitions to COMPLETE. If agents move all active tasks back to TODO (perhaps due to blocked work being abandoned), the epic returns to TODO status.

These transitions happen behind the scenes through database triggers, so Directors see accurate status without any manual updates.


## Viewing Epic Lists

Directors can ask agents to show lists of epics filtered by various criteria:

```
Director: Show me all active epics
Agent: [displays list of UNDERWAY epics with progress]

Director: Show me high priority epics
Agent: [displays filtered list]
```

This helps Directors understand the overall project landscape and identify where attention is needed.


## Epic-Specific Dashboards

For detailed focus on a particular initiative, Directors can request epic-specific dashboards that show only the tasks belonging to that epic. This filtered view helps during planning sessions, status updates, or when coordinating work across multiple agents working on related tasks.


## Completion and Closure

When an agent completes the final task in an epic, the system automatically marks the epic as COMPLETE and sets the completion timestamp. Directors don't need to manually close epics - the automatic status management handles it.

Completed epics remain in the database and their markdown files are preserved, providing historical records of what was accomplished and when.


## Aborting Epics

Sometimes project requirements change or an initiative becomes obsolete. In these cases, Directors can work with an agent to abort an epic:

```
Director: We need to abort the authentication epic - requirements changed to use OAuth instead
Agent: Aborting epic EPC-H-0001 will also abort all 5 subtasks. Should I proceed?
Director: Yes
Agent: Epic EPC-H-0001 aborted. All subtasks marked as ABORTED with reason: "Requirements changed to use OAuth instead"
```

Aborting an epic cascades to all its subtasks and locks the epic to prevent future auto-updates. This ensures organizational consistency - if an initiative is cancelled, all its work items reflect that decision.


## Using Epic Data in Planning

Historical epic data helps with future planning. Directors can review completed epics to understand how long similar work took, what challenges emerged during execution, and how accurate initial task breakdowns were. This retrospective information improves future planning sessions.


## Next Steps

Learn about the structure of [epic files](files.md) to understand what information is generated automatically versus what Directors can customize for their team's needs.
