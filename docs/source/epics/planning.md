# Planning Epics

Epics are typically created during planning sessions where Directors work with agents (usually Architects or Administrators) to break down larger initiatives into manageable tasks.


## Creating an Epic

The most natural way to create an epic is through the TUI (Text User Interface) while working with an agent. During planning discussions, the agent can help create epics based on the work you're describing. The TUI provides an interactive experience for defining the epic's title, priority, and description.

Alternatively, Directors can create epics directly through conversation with an agent:

```
Director: Let's create an epic for the user authentication system
Agent: I'll create a HIGH priority epic for that. What should the description be?
Director: Implement complete user authentication including login, registration, and password reset
Agent: Created epic EPC-H-0001: User Authentication System
```

The agent handles the database operations while the Director focuses on defining the work.


## Breaking Down Epics into Tasks

Once an epic exists, the next step is breaking it down into concrete tasks. This is where working with agents becomes particularly valuable - they can help identify all the work required and suggest appropriate roles and priorities.

A typical planning session might look like:

```
Director: Let's break down the authentication epic
Agent: I suggest these tasks:
  1. Design authentication architecture (Architect, HIGH)
  2. Implement login endpoint (Engineer, HIGH) 
  3. Implement registration endpoint (Engineer, HIGH)
  4. Write authentication tests (Tester, MEDIUM)
  5. Document authentication API (Documentarian, MEDIUM)
  Should I create these?
Director: Yes, create them all
```

The agent creates each task and automatically links them to the epic. Tasks created this way are properly sequenced and assigned to appropriate roles based on the agent's understanding of typical development workflows.


## Working with Architects

Architect agents are particularly helpful for epic planning. They can:

- Identify all the work needed to accomplish a goal
- Suggest task breakdown and sequencing
- Recommend priorities based on dependencies
- Identify which roles should handle each piece
- Point out potential risks or missing work

A planning session with an Architect might involve creating the epic, breaking it into tasks, identifying dependencies between tasks, and setting appropriate priorities based on the critical path.


## Linking Existing Tasks

Sometimes you realize that tasks you've already created should be grouped under an epic. Agents can help with this reorganization through conversation:

```
Director: Tasks ENG-H-0023, TST-M-0024, and DOC-M-0025 should all be part of the payment integration epic
Agent: I'll link those three tasks to EPC-H-0002: Payment Integration
```

This keeps your project organized even as you discover new relationships between existing work.


## Epic Naming Best Practices

Choose epic titles that clearly convey the business value or technical goal. Good epic names like "User Authentication System", "Database Migration to PostgreSQL", or "Customer Dashboard Redesign" immediately communicate what's being built. Less helpful names like "Sprint 3 Work", "Backend Tasks", or "Improvements" don't provide enough context about the actual goal.

Agents can help refine epic names during planning if you're not sure how to phrase something clearly.


## Determining Epic Priority

Epic priority helps everyone understand which initiatives are most important, though it doesn't automatically determine subtask priorities. You might have a HIGH priority epic with a mix of HIGH and MEDIUM tasks, or a CRITICAL epic with LOW priority documentation tasks.

When planning with an agent, discuss the overall importance of the initiative. The agent can then help assign individual task priorities based on when they need to be completed and their position in the dependency chain.


## Epic Size Guidelines

Aim for epics with 3-10 tasks. If you're planning an epic with more than 10 tasks, consider whether it should be split into multiple smaller epics, whether very small tasks could be grouped together, or whether you're being too granular in your task breakdown.

Agents can help identify when an epic is getting too large and suggest sensible ways to split it.


## Adding Goals and Success Criteria

After creating an epic, Directors can add goals and success criteria to the epic's markdown file. These sections help everyone understand what "done" looks like and provide context for agents working on the tasks.

Goals might describe what the initiative is trying to accomplish (e.g., "Secure user authentication with JWT tokens", "Password reset flow via email"). Success criteria define measurable outcomes (e.g., "All auth endpoints fully implemented and tested", "Security audit passed").

These sections live in the epic markdown file at `.opencode/work/epics/EPC-H-0001.md` and are preserved when the file auto-regenerates.


## Next Steps

Once planning is complete, learn how to [track progress](tracking.md) on active epics and understand the structure of [epic files](files.md) to see what information is available and what you can customize.
