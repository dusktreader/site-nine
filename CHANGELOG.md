# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## v0.3.0 - 2026-02-28

Major architectural refactoring introducing message-driven coordination and removing the handoff system.
This release represents a fundamental shift in how agents coordinate work, moving from sequential
handoffs to explicit message-based orchestration.

### Added

**Message-Driven Architecture (ADR-014):**
- Message-driven coordination system replacing handoffs
- Director → Admin → Workers coordination pattern
- Admin agents orchestrate desk-mode workers via messaging
- Worker spawning via `worker_spawn()` tool (agents never use CLI)
- Worker coordination tools: `worker_message()`, `worker_status()`, `worker_terminate()`

**Mission System Enhancements:**
- Complete mission lifecycle management via OpenCode tools
- Mission tools: `mission_init()`, `mission_role_record()`, `mission_persona_record()`
- Session management: `mission_rename_session()`, `mission_rename_dismissed()`
- Mission monitoring: `mission_dashboard()`, `mission_summary()`
- Mission state machine: ROLE_PENDING → PERSONA_PENDING → ACTIVE → SUSPENDED/COMPLETE/ABANDONED
- Automatic mission suspension/resumption on session close/reopen
- OpenCode plugin for activity tracking and session lifecycle management

**Agent Coordination:**
- Comprehensive agent discovery patterns
- Desk mode orchestration for background workers
- Message-based work assignment (self-contained, stateless messages)
- Task claiming and release mechanisms
- Persona management tools: `persona_suggest()`, `persona_show()`, `persona_set_bio()`

**Documentation:**
- AGENTS.md: Complete agent onboarding guide (389 lines)
- ADR-014: Message-Driven Coordination Architecture (309 lines)
- Agent discovery guide with JSON output patterns (192 lines)
- Desk mode orchestration guide (485 lines)
- Epic missions and desk mode guide (381 lines)
- JSON output usage guide (304 lines)
- System architecture guide (470 lines)
- Tool adapters design guide (583 lines)

**Skills Refactoring:**
- Renamed session-start → mission-start (comprehensive mission initialization)
- Renamed session-end → mission-end (proper cleanup and documentation)
- Updated all skills to use new mission terminology
- Enhanced task-claim, task-close, task-create, task-update, task-query skills
- Updated tasks-report skill with mission integration

**Developer Tools:**
- Complete OpenCode custom tool suite (20+ tools)
- Python worker module: `src/site_nine/workers/desk_worker.py`
- Comprehensive test coverage for missions, messaging, tools, desk workers
- Migration scripts for mission system fields

### Changed

**Breaking Changes:**
- Removed handoff system entirely (handoff-workflow skill, handoff tools, handoff CLI commands)
- Agents use tools exclusively (CLI is Director-only)
- Mission lifecycle now managed via tools, not CLI commands
- Persona selection now automated (auto-select least-used persona)

**Refactorings:**
- Moved Python scripts from `scripts/` to proper `src/site_nine/workers/` package
- Updated worker_spawn to reference new module location
- Removed sys.path manipulation (proper Python package structure)
- Enhanced MessagingManager with mission-aware methods
- Enhanced MissionManager with state machine and scoping
- Enhanced PersonaManager with bio management and suggestions

**Command Updates:**
- `/summon` command now triggers mission-start skill
- `/dismiss` command now triggers mission-end skill
- Updated summon flags: --persona, --auto-assign, --task, --desk

### Removed

**Handoff System (ADR-014):**
- Deleted handoff-workflow skill
- Removed handoff CLI commands (`s9 handoff`)
- Removed handoff tools: `handoff_create()`, `handoff_list()`, `handoff_delete()`
- Removed HandoffManager class and handoff models
- Removed 228 lines of handoff tests
- Deleted 297 lines of handoff workflow documentation

**Cleanup:**
- Removed 1,673 obsolete mission log files
- Removed deprecated effective_status tests

### Technical Details

**Database:**
- Handoff table marked deprecated (data preserved for migration)
- Added mission state fields (mission_status_updated_at, etc.)
- Enhanced messaging schema for mission coordination

**Testing:**
- 1,047 lines of new tool tests (test_tools_phase2.py)
- 654 lines of desk worker tests
- 561 lines of mission initialization E2E tests
- 425 lines of mission CLI tests
- 190 lines of enhanced summon tests
- 130 lines of messaging manager tests
- 98 lines of concurrent mission tests

**Architecture:**
- Core principle: Agents use OpenCode tools, Director uses CLI
- Worker spawning only via `worker_spawn()` tool (never `s9 summon`)
- Messages carry full context (self-contained, stateless)
- Explicit addressing (no polling, no discovery race conditions)

### Migration Notes

**For Existing Workflows:**
- Replace `handoff_create()` with `worker_spawn()` + `worker_message()`
- Replace `handoff_list()` with explicit worker status checking
- Replace `task_release()` + handoff with direct message to specific worker
- Use Admin agents to orchestrate multi-agent work
- Follow new coordination patterns in desk-mode-orchestration.md guide

**For Agents:**
- Use tools exclusively (mission_init, task_claim, etc.)
- Never use `s9` CLI commands directly
- Follow mission-start skill for initialization
- Use agent-discovery.md patterns for finding other agents
- Check desk_mode_active status before messaging

### See Also

- ADR-014: Complete architectural rationale and migration plan
- AGENTS.md: Agent onboarding and workflow guide
- desk-mode-orchestration.md: Admin orchestration patterns
- agent-discovery.md: Finding and coordinating with agents

## v0.2.0 - 2026-02-02

Built out the site-nine project, a comprehensive Python-based framework for managing AI agent
workflows with specialized roles, task management, session tracking, and documentation generation.

Core Features:
- Multi-role agent system (administrator, architect, builder, designer, documentarian, inspector, operator, tester)
- SQLite-based task tracking with priority-based ID system
- Session management with handoff workflows between agents
- Jinja2 template system for .opencode configuration generation
- CLI commands for agent, task, config, and session management

Technical Implementation:
- Built with Typer for CLI, SQLAlchemy for database ORM
- Comprehensive test suite with pytest (13 test modules, 85% coverage threshold)
- CI/CD with GitHub Actions for tests, docs, and deployment
- MkDocs-based documentation with Material theme
- Migration scripts for schema updates and legacy data

Project Structure:
- src/s9/cli: Command-line interface modules
- src/s9/core: Configuration, database, paths, templates
- src/s9/tasks: Task management and ID generation
- src/s9/templates: Jinja2 templates for agent docs and workflows
- tests/: Comprehensive test coverage
- docs/: MkDocs documentation site

## v0.1.0 - 2026-01-30
- Generated project from template
