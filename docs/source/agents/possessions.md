# Possessions

A **possession** is a tracked work session where an agent pursues a specific objective. Possessions provide structure, accountability, and historical context for all work done through site-nine.

## What is a Possession?

When you summon an agent, you're starting a possession: a discrete unit of work that defines the objective you're working toward, the role expertise needed, and the daemon (mythological character) the agent assumes. Each possession gets a unique codename like "Operation silver-titan" for easy reference, and creates a markdown documentation file at `.opencode/work/possessions/` to track progress. The possession's status moves through an explicit lifecycle as work progresses.

Possessions create a clear boundary around work: when you start, what you're trying to accomplish, and when you're done.

## Possession Lifecycle

Possessions move through a defined sequence of states from initialization to completion:

```
ROLE_PENDING → DAEMON_PENDING → ACTIVE → SUSPENDED → EXORCISED
```

### Starting a Possession

The Director summons an agent using `s9 summon <role>`, which launches OpenCode and triggers the `possession-start` skill. The skill handles role selection, daemon selection, possession registration in the database, session renaming, and the initial task dashboard display.

Example:
```bash
s9 summon documentarian
```

This results in something like:
- Daemon: **fukurokuju** (Japanese god of wisdom)
- Codename: **Operation silver-titan**
- Session renamed to: "Operation silver-titan: Fukurokuju - Documentarian"

### During a Possession

While a possession is active, the agent works on tasks, updates the possession file to document decisions and progress, and creates commits attributed to the daemon name or possession codename. The possession file serves as the working journal: capture important context, decisions, and notes as you go.

### Ending a Possession

When work is done, the `possession-end` skill handles proper closure. It updates the possession status to EXORCISED, documents what was accomplished, and ensures task status reflects reality.

Properly ending possessions ensures clean handoffs and accurate project history.

## Possession Codenames

Every possession gets a unique codename following the pattern:

**"Operation [adjective]-[noun]"**

Examples:

- Operation silver-titan
- Operation crimson-phoenix
- Operation quiet-thunder

Codenames are memorable (easier to reference than IDs), unique (no two possessions share one), and distinctive (helpful for differentiating concurrent work streams). Use codenames in commit messages, notes, and conversations to clearly identify which work stream you're referencing.

## Possession Files

Each possession creates a markdown file at:

```
.opencode/work/possessions/YYYY-MM-DD.HH-MM-SS.role.Daemon.md
```

Example:
```
.opencode/work/possessions/2026-02-04.14-16-24.documentarian.Fukurokuju.md
```

!!! warning "Agent Documentation Only"
    Possession files are maintained by agents, not humans. Don't manually edit these files — they serve as agent-to-agent documentation and historical records of work sessions.

### File Structure

Possession files contain:

```markdown
# Possession: Operation silver-titan

**Daemon:** Fukurokuju - Documentarian
**Started:** 2026-02-04 14:16:24
**Status:** ACTIVE
**Objective:** Document adapter pattern implementation and usage

## Context

[Background information and requirements]

## Progress

- [x] Task 1 completed
- [ ] Task 2 in progress
- [ ] Task 3 pending

## Decisions

### 2026-02-04 14:30 - Decision Title

[Important decisions made during the possession]

## Notes

[Ongoing notes, blockers, observations]
```

### Agent Documentation

Possession files are maintained by agents as they work. The agent updates the file throughout the session to document decisions made, track blockers and dependencies, note important context, and capture information that won't fit in commit messages. Think of the possession file as the agent's working journal — it provides historical context for future possessions and helps other agents understand what happened during a particular work session.

## Possession Status

Possessions move through these states:

### ROLE_PENDING

The possession has been initialized but no role has been selected yet. This is the initial state immediately after `s9 summon` is invoked.

### DAEMON_PENDING

A role has been selected but no daemon has been assigned yet. The system is about to select or invent a daemon name.

### ACTIVE

Currently working. The OpenCode session is open and the agent is engaged.

### SUSPENDED

The possession exists in the database but is not actively being worked on. Can be resumed later.

### EXORCISED

The possession has been properly closed via the `possession-end` skill. Work is documented and the session is done.

## Working with Multiple Possessions

Site-nine supports multiple concurrent possessions, whether you're running different roles (a documentation possession alongside an engineering possession), working on different features, or just want distinct work streams in history. Each possession maintains its own independent OpenCode session, possession file, progress tracking, and task assignments. Use possession codenames and daemon names to keep them straight.

## Best Practices

### Clear Objectives

Start possessions with specific, achievable objectives:

**Good objectives:**
- "Implement user authentication API endpoints"
- "Write documentation for adapter pattern"
- "Fix bug in payment processing flow"

**Less helpful:**
- "Work on the project"
- "Various improvements"
- "Sprint 3 tasks"

### Document as You Go

Update the possession file throughout your work session. Note important decisions when made, document blockers as they arise, capture context while it's fresh, and link to relevant issues, PRs, or docs. Future you (and other team members) will thank you.

### Proper Closure

Always end possessions properly using the `possession-end` skill: update status in the database, document outcomes in the possession file, create handoffs if needed, and close associated tasks. Don't leave possessions dangling — complete the loop.

### Use Codenames

Reference possession codenames in commit messages (`[Operation: silver-titan] Add adapter documentation`), pull request descriptions, task updates, and team communication. Codenames make it easy to trace work back to its context.

## Possession vs Task

Possessions and tasks serve different purposes in site-nine. A possession represents a work session (lasting anywhere from a few minutes to a few hours) where a daemon pursues a specific objective, tracked via possession files for session context. A task represents a discrete work item (lasting days to weeks) assigned to a role for project management, tracked in the task database. One possession might complete multiple tasks, and one task might span multiple possessions across handoffs. Tasks persist in your backlog while possessions are time-bound sessions. Think of possessions as "how work gets done" and tasks as "what needs to be done."

| Aspect | Possession | Task |
|--------|-----------|------|
| **Scope** | Work session | Discrete work item |
| **Duration** | Minutes to hours | Days to weeks |
| **Assignment** | Daemon | Role |
| **Tracking** | Possession file | Task database |
| **Purpose** | Session context | Project management |

## Next Steps

Learn more about the agent system by exploring the different [agent roles](roles.md) and how [daemon selection](daemons.md) works. Ready to get started? Follow the [quickstart guide](../quickstart.md) to launch your first possession, or master the command-line tools in the [CLI reference](../cli/overview.md).
