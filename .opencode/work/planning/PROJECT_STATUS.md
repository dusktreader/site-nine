# s9 - Project Status

**Project:** s9
**Type:** Python CLI Tool / Framework
**Initialized:** 2026-02-01

---

## 🎯 Project Goals

Build a generic orchestration framework for AI-assisted software development that:
- Bootstraps `.opencode` project structures with agent roles and workflows
- Provides task management via SQLite database
- Tracks agent sessions and daemon name usage
- Standardizes commit formats with agent attribution
- Offers customizable Jinja2 templates for all project files

**Target Users:** Software development teams using AI agents (Claude, ChatGPT, etc.)

---

## 🏗️ Current Phase

**Phase:** Core Implementation & Documentation

**Status:** Core CLI framework functional. Documentation cleanup in progress to ensure all references are up-to-date and generic.

**Focus Areas:**
- Finalize documentation updates
- Port missing infrastructure (data/README.md)
- Fix broken skill workflows
- Initialize task database with project tasks

---

## 🔑 Key Decisions

- 2026-01-30: Renamed from `s9` to `hq` (cleaner package name)
- 2026-01-31: Chose Python CLI over bash scripts (better testing, type safety)
- 2026-01-31: Adopted Jinja2 templates (flexibility, customization)
- 2026-01-31: SQLite for task/agent/name management (simplicity, no external deps)
- 2026-02-01: PROJECT_STATUS.md as lightweight strategic doc + dashboard for metrics (hybrid approach)

---

## 🚧 External Blockers

None currently.

---

## 📊 Real-Time Metrics

For current task status, active agents, and recent activity:

```bash
# Show comprehensive project overview
s9 dashboard

# List active tasks
s9 task list --active-only

# Show active agent sessions
s9 mission list --active-only

# Create/claim/update tasks
s9 task --help
```

---

## 📝 Notes

This file captures strategic context and high-level project state.
For operational details and real-time metrics, use the `s9` CLI commands above.

**Update this file when:**
- ✅ Project goals change
- ✅ Major architectural decisions are made
- ✅ Phase transitions occur
- ✅ External blockers are added/removed

**Don't update this file for:**
- ❌ Daily task status changes (use dashboard)
- ❌ Individual task progress (use task commands)
- ❌ Agent session tracking (use agent commands)

---

**Last updated:** 2026-02-01
