# Development Guides

Essential guides for developing site-nine.

## Core Guides

### agents.md ⭐ **START HERE FOR DEVELOPMENT**
**Development patterns and best practices for working on site-nine**

This is THE most important document for agents. Contains:
- Development workflow
- Code patterns and conventions
- Technology stack details
- Testing requirements
- What worked, what didn't, and why

**Read this before starting any development work.**

---

### architecture.md
**System architecture and technical design**

Comprehensive technical overview:
- Technology stack (Python, Typer, SQLAlchemy, Jinja2)
- Component architecture (CLI, database, templates)
- Design decisions and rationale
- Project structure
- Extension points

**Read when understanding system design or making architectural changes.**

---

### design-philosophy.md
**Design principles and trade-offs**

Why we made the choices we made:
- Core principles (bootstrap not prescribe, agent-friendly, local-first)
- Key design decisions
- Trade-offs and rationale
- What we value and why

**Read when making design decisions or understanding project priorities.**

---

### tasks.md
**Task management system reference**

Essential reference for the s9 task system:
- Task ID format and structure
- Valid status values (TODO, UNDERWAY, BLOCKED, etc.)
- Priority levels (CRITICAL, HIGH, MEDIUM, LOW)
- Task lifecycle overview
- Role prefixes and values

**Read when working with tasks or learning the task system.**

---

## How to Use These Guides

### For New Contributors
1. **Start with agents.md** - Learn patterns and workflow
2. **Read architecture.md** - Understand the system
3. **Skim design-philosophy.md** - Understand design values

### For Specific Tasks
- **Adding features:** agents.md → architecture.md → design-philosophy.md
- **Fixing bugs:** agents.md → architecture.md
- **Architecture changes:** architecture.md → design-philosophy.md
- **Understanding "why":** design-philosophy.md

### For Understanding Context
- **"Why was it done this way?"** → design-philosophy.md
- **"How does X work?"** → architecture.md
- **"What patterns should I follow?"** → agents.md

---

## Quick Reference

| Task | Primary Guide | Supporting Guides |
|------|---------------|-------------------|
| Adding CLI features | agents.md | architecture.md |
| Database changes | agents.md | architecture.md |
| Architecture decisions | architecture.md | design-philosophy.md |
| Bug fixes | agents.md | architecture.md |
| Design decisions | design-philosophy.md | architecture.md |

---

## Related Documentation

- **Procedures:** `.opencode/docs/procedures/` - Step-by-step how-tos
- **Agent Roles:** `.opencode/docs/roles/` - Role definitions
- **Project Overview:** `.opencode/README.md` - Entry point
- **User Docs:** `docs/source/` - User-facing documentation
