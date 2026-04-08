# Working with Agents

Site-nine uses AI agents to assist with software development tasks. When we refer to **agents** in this documentation, we're talking about entities that are native to your agentic coding platform (like OpenCode, Cursor, or Windsurf) — the AI assistants built into your development environment.

Site-nine provides a structured system of possessions, roles, and daemons that helps organize how these agents work and track their progress.


## The Agent System

The agent system has three core concepts that work together to organize your development workflow.


### Possessions

A **possession** is a discrete unit of work with a clear objective. When you start a possession, you're creating a tracked session where an agent works toward a specific goal. Each possession receives a unique codename (like "Operation silver-titan") and generates a markdown file that documents progress, decisions, and outcomes.

Possessions provide structure and accountability. They track what work has been done, preserve decisions and context for future reference, help manage multiple concurrent work streams, and facilitate smooth handoffs between sessions.

[Learn more about possessions →](possessions.md)


### Roles

A **role** defines the type of work an agent performs. Site-nine provides 9 specialized roles that cover the full spectrum of software development activities:

- **Administrator** - Coordinates projects and delegates tasks
- **Architect** - Designs system architecture and makes technical decisions
- **Engineer** - Implements features and writes code
- **Tester** - Creates tests and validates quality
- **Documentarian** - Writes documentation and guides
- **Designer** - Creates UI/UX and visual assets
- **Inspector** - Reviews code and audits security
- **Operator** - Handles deployment and infrastructure
- **Historian** - Documents project history and preserves institutional knowledge

Each role brings specialized expertise and best practices for its domain, ensuring that agents apply the right knowledge and approach for the task at hand.

[Learn more about roles →](roles.md)

### Daemons

A **daemon** is a unique character from ancient mythology that an agent assumes for a possession. When you start a possession with a chosen role, the agent adopts a daemon themed around that role's purpose. The system maintains a pool of 256+ daemons drawn from mythologies worldwide, automatically selecting unused daemons to add variety and make it easy to distinguish between concurrent possessions.

Daemons add personality to the system while serving practical purposes. They make concurrent possessions easy to track, provide memorable identities for conversation history, and give each work session a distinctive character. A Documentarian might become Fukurokuju (Japanese god of wisdom) or Thoth (Egyptian god of writing), while an Engineer might adopt Hephaestus (Greek god of craftsmanship) or Kothar (Canaanite divine craftsman).

[Learn more about daemons →](daemons.md)

## How It Works

When you summon an agent, you choose a role based on the type of work to be done. The agent then assumes a daemon — a mythological character matching that role. A possession begins with a unique codename and tracking file. The agent applies role-specific expertise to accomplish your objectives, documenting progress along the way. When the work is complete, the possession ends with outcomes documented and handoffs created if needed.

This structure ensures every piece of work is organized, trackable, and contextual.

## Benefits

For individuals, the agent system provides specialized expertise for different tasks, clear separation between types of work, easy context switching between projects, and built-in documentation of decisions.

For teams, it establishes shared vocabulary and conventions, enables trackable work assignments by role, facilitates smooth handoffs between specialists, and provides visibility into who's working on what.

## Getting Started

Ready to work with agents? Start by understanding how possessions structure your work sessions, then explore the nine specialized roles to see which fits your current task. Learn how daemons add identity and personality to each possession, then jump into the quickstart guide to begin your first possession.

**Next steps:**

- [Understand possessions](possessions.md) - Learn the lifecycle and structure
- [Choose a role](roles.md) - See what each role specializes in
- [Explore daemons](daemons.md) - Understand how daemons work
- [Start your first possession](../quickstart.md) - Follow the quickstart guide

