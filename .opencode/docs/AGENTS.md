# Site-Nine Agent Guide

Welcome to site-nine! This guide explains how to work as an agent in the site-nine development environment.

## Quick Start

As an agent, your workflow is simple:

1. **Director summons you** via `s9 summon <role>` or `s9 summon <role> <persona>`
2. **You initialize** by running the `mission-start` skill (happens automatically)
3. **You work** on tasks using custom tools (not CLI commands)
4. **Director dismisses you** via `/dismiss`, and you run the `mission-end` skill

**Key principle:** You use **OpenCode tools** to interact with site-nine. The `s9` CLI is for the Director only.

## Mission Lifecycle

### Starting a Mission

When the Director summons you, you'll receive an instruction like:

```
Your role is documentarian. Initialize your mission with the mission-start skill.
```

Or:

```
Your role is operator, your persona is pontus. Initialize your mission with the mission-start skill.
```

The `mission-start` skill handles all initialization:
- Creates your mission record (using `mission_init` tool)
- Records your role (using `mission_role_record` tool)
- Selects or confirms your persona (using `mission_persona_record` tool)
- Renames the session (using `mission_rename_session` tool)
- Shows your role-specific task dashboard

**You don't need to track your mission ID** - all tools automatically know which mission you're on via the session
context.

### Mission Statuses

Your mission progresses through these states:

- **ROLE_PENDING** - Mission created, waiting for role selection
- **PERSONA_PENDING** - Role recorded, waiting for persona selection
- **ACTIVE** - Fully initialized and working
- **SUSPENDED** - Session closed unexpectedly, mission paused
- **COMPLETE** - Mission ended successfully
- **ABANDONED** - Mission ended without completion

### Suspending and Resuming

**What happens if your session closes unexpectedly?**

The site-nine OpenCode plugin automatically detects session closures and suspends your mission. Your work is not lost!

The Director can resume your mission with:

```bash
s9 mission resume <codename>
```

This reopens your session exactly where you left off.

**Note:** You don't need to worry about this - the automation handles it.

## Working with Tasks

### Claiming Tasks

Use the `task_claim` tool to claim tasks:

```typescript
task_claim({ task_id: "DOC-M-0106" })
```

The tool automatically:
- Associates the task with your current mission
- Updates the task status to UNDERWAY
- Records the claim timestamp

### Updating Progress

Use the `task_update` tool to record progress notes:

```typescript
task_update({ 
  task_id: "DOC-M-0106",
  notes: "Created communication channels section in session-start skill"
})
```

### Completing Tasks

Use the `task_close` tool to close tasks:

```typescript
task_close({ 
  task_id: "DOC-M-0106",
  status: "COMPLETE",
  notes: "Added Step 7.5 explaining three communication channels with examples"
})
```

**Available statuses:**
- `COMPLETE` - Task finished successfully
- `BLOCKED` - Cannot proceed (explain why in notes)
- `WONTDO` - Task cancelled or no longer needed

### Auto-Claiming Next Task

For epic-scoped missions, use `task_next` to automatically claim the next TODO task in your epic:

```typescript
task_next()
```

This is useful when working through a series of related tasks.

## Using Custom Tools

Site-nine provides OpenCode custom tools for all operations. **Never use `s9` CLI commands** - they're for the Director
only.

### Mission Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `mission_init` | Initialize new mission | Auto-called by mission-start skill |
| `mission_role_record` | Set mission role | Auto-called by mission-start skill |
| `mission_persona_record` | Set mission persona | Auto-called by mission-start skill |
| `mission_rename_session` | Rename OpenCode session | Auto-called by mission-start skill |
| `mission_end` | End current mission | Called by mission-end skill |
| `mission_summary` | Get mission summary | For status reporting |
| `mission_dashboard` | Get role-filtered dashboard | See available tasks |

### Task Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `task_create` | Create new task | `task_create({ title: "...", role: "..." })` |
| `task_show` | Get task details | `task_show({ task_id: "DOC-M-0106" })` |
| `task_claim` | Claim task for current mission | `task_claim({ task_id: "DOC-M-0106" })` |
| `task_update` | Update progress notes | `task_update({ task_id: "...", notes: "..." })` |
| `task_close` | Close task with status | `task_close({ task_id: "...", status: "COMPLETE" })` |
| `task_release` | Release claimed task | `task_release({ task_id: "..." })` |

### Persona Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `persona_suggest` | Get persona suggestions | `persona_suggest({ role: "Documentarian" })` |
| `persona_show` | Get persona details | `persona_show({ name: "nabu" })` |
| `persona_set_bio` | Save persona bio | `persona_set_bio({ name: "...", bio: "..." })` |

### Messaging and Coordination Tools

Agents use messages to coordinate work and communicate explicitly:

| Tool | Purpose | Example |
|------|---------|---------|
| `worker_spawn` | Spawn a desk-mode worker for a role | `worker_spawn({ role: "Engineer", persona: "hephaestus" })` |
| `worker_message` | Send message to another mission | `worker_message({ to_mission_id: 42, body: "..." })` |
| `worker_status` | Check active workers for a role | `worker_status({ role: "Engineer" })` |
| `worker_terminate` | Signal a worker to end gracefully | `worker_terminate({ to_mission_id: 42 })` |

**Key principles:**
- Admin orchestrates workers via `worker_spawn` tool (never use `s9 summon` CLI)
- Admin assigns work explicitly via `worker_message` (not discovery patterns)
- Workers receive work assignments directly from Admin
- No polling or discovery - coordination is explicit and deterministic

**See:** `.opencode/docs/guides/desk-mode-orchestration.md` for complete orchestration patterns.

## Epic Missions

For larger bodies of work, you can scope your mission to an epic:

```bash
# Director summons you for epic work
s9 summon documentarian --epic EPC-H-0005
```

**Benefits of epic missions:**
- Use `task_next` to auto-claim next task in sequence
- Other agents can discover you via mission list
- Desk mode coordination with other agents on same epic
- Mission continuity across multiple related tasks

**See:** `.opencode/docs/guides/epic-missions-and-desk-mode.md` for complete guide.

## Agent Coordination

### Finding Other Agents

Use the messaging system to coordinate with other agents asynchronously.

**Discovery pattern:**
1. Check for available agents using mission discovery
2. Send message if agent is in desk mode
3. Ask Director to summon agent if none available

**See:** `.opencode/docs/guides/agent-discovery.md` for complete patterns.

### Desk Mode

Desk mode makes you available for async coordination while you work:

```bash
# Director summons you in desk mode
s9 summon operator --desk
```

In desk mode:
- Your mission monitors for incoming messages
- Other agents can discover you're available
- You can respond to questions while working
- Enables background worker patterns

**See:** `.opencode/docs/guides/epic-missions-and-desk-mode.md` for usage guide.

### Communication Channels

You have three communication channels:

1. **OpenCode Chat (Agent ↔ Director)** - For immediate guidance, requesting agent summons, reporting blockers
2. **Messaging System (Agent ↔ Agent)** - For async technical questions, epic coordination, role-wide announcements
3. **Director Observation** - Director can view all messages but doesn't participate

**See:** `mission-start` skill Step 7.5 for when to use each channel.

## Skills vs. Tools

Understanding the difference is important:

### Skills
- Markdown documents with instructions
- Handle interactive, context-dependent decisions
- Guide you through multi-step workflows
- Located in `.opencode/skills/`

**Example skills:**
- `mission-start` - Initialize your mission
- `mission-end` - End your mission properly
- `task-claim` - Claim and start work on tasks
- `task-update` - Update task progress and notes

### Tools
- TypeScript functions you invoke
- Handle deterministic, repeatable operations
- Called directly as function invocations
- Located in `.opencode/tools/`

**Example tools:**
- `mission_init()` - Create mission record
- `task_claim({ task_id: "..." })` - Claim a task
- `mission_dashboard()` - Get task list

**Rule of thumb:** Skills tell you **what to do**, tools do the **actual work**.

## Workflow Examples

### Standard Task Workflow

```
1. Director: s9 summon documentarian
2. You: Run mission-start skill
   → mission_init creates mission
   → mission_role_record sets role
   → mission_persona_record sets persona (auto-selected)
   → mission_rename_session renames session
   → mission_dashboard shows available tasks
3. You: Claim task
   → task_claim({ task_id: "DOC-M-0106" })
4. You: Work on task
5. You: Update progress
   → task_update({ task_id: "DOC-M-0106", notes: "..." })
6. You: Complete task
   → task_close({ task_id: "DOC-M-0106", status: "COMPLETE", notes: "..." })
7. Director: /dismiss
8. You: Run mission-end skill
   → mission_end() closes mission
```

### Epic Workflow

```
1. Director: s9 summon architect --epic EPC-H-0004
2. You: Run mission-start skill (mission is epic-scoped)
3. You: Claim first task
   → task_claim({ task_id: "ARC-H-0057" })
4. You: Complete first task
   → task_close({ task_id: "ARC-H-0057", status: "COMPLETE" })
5. You: Auto-claim next task
   → task_next()
6. You: Continue through epic tasks...
7. Director: /dismiss when epic work complete
8. You: Run mission-end skill
```

### Coordination Workflow

```
1. You (Engineer): Need Architect input
2. You: Check for available Architects
   → Read .opencode/docs/guides/agent-discovery.md
   → Use discovery patterns to find agents
3a. If Architect in desk mode:
    → Send message via messaging system
    → Continue working while waiting for response
3b. If no Architect available:
    → Ask Director in chat: "Should I wait or would you like to summon an Architect?"
    → Director summons Architect
4. You: Coordinate via messaging or chat as needed
```

## Important Notes

### What You Should NOT Do

❌ **Don't use `s9` CLI commands** - Use tools instead (e.g., `task_claim()` not `s9 task claim`)  
❌ **Don't track mission IDs manually** - Tools automatically know your mission from session context  
❌ **Don't send heartbeats** - The OpenCode plugin tracks activity automatically  
❌ **Don't manually suspend missions** - Plugin handles this when sessions close  
❌ **Don't end mission without dismissal** - Wait for Director to dismiss you

### What You SHOULD Do

✅ **Use tools for all operations** - They're designed for agents  
✅ **Follow skills for guidance** - They orchestrate complex workflows  
✅ **Check your task dashboard** - mission-start skill shows available work  
✅ **Update task progress** - Use task_update tool to document work  
✅ **Ask Director when unclear** - Use OpenCode chat for guidance  
✅ **Coordinate with other agents** - Use messaging for async communication

## Documentation

### Essential Guides

- **Task Management**: `.opencode/docs/guides/tasks.md`
- **Agent Discovery**: `.opencode/docs/guides/agent-discovery.md`
- **Epic Missions & Desk Mode**: `.opencode/docs/guides/epic-missions-and-desk-mode.md`
- **JSON Output Usage**: `.opencode/docs/guides/json-output-usage.md`
- **Commit Guidelines**: `.opencode/docs/guides/commit-guidelines.md`
- **Markdown Style**: `.opencode/docs/guides/markdown-style.md` (REQUIRED for all markdown edits)

### Architecture

- **ADR-013**: Site-nine as OpenCode Integration Platform (this architecture)
- **ADR-009**: Agent Coordination Patterns
- **ADR-008**: Agent Messaging System
- **All ADRs**: `.opencode/docs/adrs/`

### Quick Reference

- **All guides**: `.opencode/docs/guides/README.md`
- **Skills**: `.opencode/skills/`
- **Roles**: `.opencode/docs/roles/`

## Getting Help

**During a mission:**
1. Check relevant guides in `.opencode/docs/guides/`
2. Ask the Director in OpenCode chat
3. Check ADRs for architecture decisions
4. Use agent discovery to find other agents

**If confused about workflow:**
- Re-read this guide (AGENTS.md)
- Check the mission-start skill for initialization steps
- Ask Director for clarification

## Summary

You are an agent working in the site-nine development environment. Your workflow is:

1. **Initialize** with mission-start skill (automatic when summoned)
2. **Work** using OpenCode custom tools (not CLI commands)
3. **Coordinate** via messaging system or Director chat
4. **End** with mission-end skill (when Director dismisses you)

The system automates lifecycle management, activity tracking, and mission persistence. You focus on the work - the
tools and skills handle the coordination.

**Remember:** Tools for operations, skills for guidance, Director for decisions.

Welcome to the team! 🚀
