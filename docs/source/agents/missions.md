# Missions

A **mission** is a tracked work session where an agent pursues a specific objective. Missions provide structure, accountability, and historical context for all work done through site-nine.

## What is a Mission?

When you summon an agent, you're starting a mission - a discrete unit of work that defines the objective you're working toward, the role expertise needed, and the persona (mythological character) the agent assumes. Each mission gets a unique codename like "Operation silver-titan" for easy reference, and creates a markdown documentation file at `.opencode/work/missions/` to track progress. The mission's status moves through ACTIVE, IDLE, or COMPLETE as work progresses.

Missions create a clear boundary around work: when you start, what you're trying to accomplish, and when you're done.

## Mission Lifecycle

### Starting a Mission

When you summon an agent (using `/summon <role>` or the CLI), site-nine selects an unused persona for the role, generates a unique mission codename, creates a mission file with metadata, registers the mission in the database, and renames your OpenCode session for easy identification.

Example:
```bash
/summon documentarian
```

Results in:
- Persona: **fukurokuju** (Japanese god of wisdom)
- Codename: **Operation silver-titan**
- Session renamed to: "Operation silver-titan: Fukurokuju - Documentarian"

### During a Mission

While a mission is active, you work on tasks, update the mission file to document decisions and progress, create commits tagged with your persona name or mission codename, and hand off work to other roles if needed. The mission file serves as your working journal - capture important context, decisions, and notes as you go.

### Ending a Mission

When you're done with your work, use `/dismiss` to properly close the mission. This updates the mission status to COMPLETE, documents what was accomplished, and ensures task status reflects reality.

If you need to pass work to another role, use `/handoff` instead. This creates a handoff document for the target role before ending your mission. When you later start a new mission with `/summon` for that role, the agent will detect the pending handoff and offer to pick it up upon confirmation.

Properly ending missions ensures clean handoffs and accurate project history.

## Mission Codenames

Every mission gets a unique codename following the pattern:

**"Operation [adjective]-[noun]"**

Examples:

- Operation silver-titan
- Operation crimson-phoenix
- Operation quiet-thunder

Codenames are memorable (easier to reference than IDs), unique (no two missions share one), distinctive (helping differentiate concurrent work), and fun (adding personality to your workflow). Use codenames in commit messages, notes, and conversations to clearly identify which work stream you're referencing.

## Mission Files

Each mission creates a markdown file at:

```
.opencode/work/missions/YYYY-MM-DD.HH:MM:SS.role.persona.codename.md
```

Example:
```
.opencode/work/missions/2026-02-04.14:16:24.documentarian.fukurokuju.silver-titan.md
```

!!! warning "Agent Documentation Only"
    Mission files are maintained by agents, not humans. Don't manually edit these files - they serve as agent-to-agent documentation and historical records of work sessions.

### File Structure

Mission files contain:

```markdown
# Mission: Operation silver-titan

**Persona:** Fukurokuju - Documentarian
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

[Important decisions made during the mission]

## Notes

[Ongoing notes, blockers, observations]

## Handoffs

[Any handoffs created to other roles]
```

### Agent Documentation

Mission files are maintained by agents as they work. The agent updates the file throughout the session to document decisions made, track blockers and dependencies, note important context, and capture information that won't fit in commit messages. Think of the mission file as the agent's working journal - it provides historical context for future missions and helps other agents understand what happened during a particular work session.

## Mission Status

Missions have three states:

### ACTIVE

Currently working on the mission. OpenCode session is open and agent is engaged.

### IDLE

Mission paused or session closed, but not completed. Can be resumed later.

### COMPLETE

Mission objectives accomplished and session properly closed.

## Working with Multiple Missions

Site-nine supports multiple concurrent missions, whether you're running different roles (a documentation mission alongside an engineering mission), working on different projects (frontend and backend work), or just need to distinguish work in history using different personas. Each mission maintains its own independent OpenCode session (if active), mission file, progress tracking, and task assignments. Use mission codenames and persona names to keep them straight.

## Best Practices

### Clear Objectives

Start missions with specific, achievable objectives:

**Good objectives:**
- "Implement user authentication API endpoints"
- "Write documentation for adapter pattern"
- "Fix bug in payment processing flow"

**Less helpful:**
- "Work on the project"
- "Various improvements"
- "Sprint 3 tasks"

### Document as You Go

Update the mission file throughout your work session. Note important decisions when made, document blockers as they arise, capture context while it's fresh, and link to relevant issues, PRs, or docs. Future you (and other team members) will thank you.

### Proper Closure

Always end missions properly: update status in the database, document outcomes in the mission file, create handoffs if needed, and close associated tasks. Don't leave missions dangling - complete the loop.

### Use Codenames

Reference mission codenames in commit messages (`[Mission: silver-titan] Add adapter documentation`), pull request descriptions, task updates, and team communication. Codenames make it easy to trace work back to its context.

## Mission vs Task

Missions and tasks serve different purposes in site-nine. A mission represents a work session (lasting anywhere from a few minutes to a few hours) where a persona pursues a specific objective, tracked via mission files for session context. A task represents a discrete work item (lasting days to weeks) assigned to a role for project management, tracked in the task database. One mission might complete multiple tasks, and one task might span multiple missions across handoffs. Tasks persist in your backlog while missions are time-bound sessions. Think of missions as "how work gets done" and tasks as "what needs to be done."

| Aspect | Mission | Task |
|--------|---------|------|
| **Scope** | Work session | Discrete work item |
| **Duration** | Minutes to hours | Days to weeks |
| **Assignment** | Persona | Role |
| **Tracking** | Mission file | Task database |
| **Purpose** | Session context | Project management |

## Next Steps

Learn more about the agent system by exploring the different [agent roles](roles.md) and how [persona selection](personas.md) works. Ready to get started? Follow the [quickstart guide](../quickstart.md) to launch your first mission, or master the command-line tools in the [CLI reference](../cli/overview.md).
