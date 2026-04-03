# Architecture Guide

Architectural overview of site-nine, including core components, patterns, and planned abstractions.


## Overview

Site-nine is a universal AI coding workflow system that manages tasks, possessions, and agent coordination. The 
architecture is designed to be tool-agnostic while currently optimized for OpenCode integration.


### Core principles

- **Tool independence**: Core logic (80%) works independently of any specific AI coding tool
- **Clean separation**: Business logic separated from tool integrations
- **Extensibility**: New tools can be added without modifying core code
- **Zero regression**: Changes preserve all existing functionality


## System architecture

### High-level layers

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Layer                                │
│  s9 init, s9 task, s9 possession, s9 dashboard, s9 summon, etc.  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ uses
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Application Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ TaskManager  │  │ AgentSession │  │ SkillExecutor│          │
│  │              │  │  Manager     │  │              │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                  │                   │
│         │ depends on abstractions (not tools)│                   │
│         └─────────────────┴──────────────────┘                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ uses
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Abstraction Layer                              │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │  ToolAdapter      │  │  ToolConfig      │                     │
│  │  (Protocol)       │  │  (Unified Model) │                     │
│  └──────────────────┘  └──────────────────┘                     │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │  PathResolver     │  │  SkillRenderer   │                     │
│  │                   │  │  (Protocol)      │                     │
│  └──────────────────┘  └──────────────────┘                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ implemented by
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Tool Adapter Layer                            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │ OpenCodeAdapter  │  │  CursorAdapter   │  │ AiderAdapter  │ │
│  │   (Current)      │  │   (Planned)      │  │  (Planned)    │ │
│  └────────┬─────────┘  └────────┬─────────┘  └───────┬───────┘ │
│           │                     │                     │          │
└───────────┼─────────────────────┼─────────────────────┼──────────┘
            │                     │                     │
            ▼                     ▼                     ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  OpenCode API    │  │  Cursor MCP API  │  │  Aider CLI       │
│  (.opencode/)    │  │  (.cursor/)      │  │  (.aider/)       │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```


### Layer responsibilities

#### CLI layer
- Parse command-line arguments
- Validate user input
- Delegate to application layer
- Format output for terminal


#### Application layer
- **Tool-agnostic** business logic (task management, agent sessions, etc.)
- No knowledge of specific tools
- Uses abstractions (ToolAdapter, ToolConfig)
- Manages core data (database, files)


#### Abstraction layer
- Defines protocols/interfaces for tools
- Provides unified models (ToolConfig)
- Path resolution across tools
- Skill rendering abstraction


#### Tool adapter layer
- Implements protocols for specific tools
- Handles tool-specific APIs
- Manages tool-specific configurations
- Maps tool formats to unified models


## Core components

### Database

**Location:** `.opencode/data/project.db`

SQLite database storing:
- Tasks (id, title, status, priority, role, etc.)
- Possessions (id, daemon, role, objective, start/end times)
- Daemons (name, role, mythology, bio)
- Messages (agent-to-agent coordination)
- Epics (larger bodies of work)

**See:** Database schema in `src/site_nine/db/schema.sql`


### Task management

Tasks are work items assigned to agent roles with statuses tracking progress.

**Statuses:**
- `TODO` - Ready to be claimed
- `UNDERWAY` - Actively being worked
- `COMPLETE` - Finished successfully
- `BLOCKED` - Waiting on dependency
- `WONTDO` - Cancelled or obsolete

**See:** `.opencode/docs/guides/tasks.md`


### Possession system

Possessions track agent work sessions with daemon, role, and lifecycle management.

**States:**
- `ROLE_PENDING` - Possession created, waiting for role
- `DAEMON_PENDING` - Role set, waiting for daemon
- `ACTIVE` - Working on tasks
- `SUSPENDED` - Session closed unexpectedly
- `EXORCISED` - Ended successfully

**Scopes:**
- **Task-scoped** - Single task focus
- **Epic-scoped** - Work through related tasks in epic
- **General** - Flexible coordination work

**See:** `.opencode/docs/AGENTS.md`, ADR-013


### Agent coordination

Three communication channels:

1. **Agent ↔ Director (OpenCode chat)** - Synchronous, for immediate guidance
2. **Agent ↔ Agent (messaging)** - Asynchronous, for technical coordination
3. **Director observing messages** - Read-only monitoring

**See:** `.opencode/docs/guides/agent-discovery.md`, ADR-009


### Skills system

Skills are workflow guides for agents, providing instructions for complex multi-step processes.

**Location:** `.opencode/skills/`

**Format:** Markdown documents with instructions

**Examples:**
- `possession-start` - Initialize possessions
- `possession-end` - End possessions properly
- `task-claim` - Claim and start tasks
- `task-update` - Update task progress and notes

**See:** Skills in `.opencode/skills/` directory


## Adapter pattern (planned)

**Status:** Proposed (not yet implemented)

The adapter pattern will abstract tool-specific functionality to support multiple AI coding tools.


### Motivation

Site-nine is currently tightly coupled to OpenCode. To become a universal workflow system supporting OpenCode, Cursor, 
Aider, and other tools, we need an abstraction layer.

**Current state:**
- **80% tool-agnostic** - Core functionality works independently
- **20% tool-coupled** - Integration points in paths, config, skills, commands, session TUI

**See:** ADR-001 for complete context and decision rationale


### Design overview

The adapter pattern uses protocols and dependency injection to abstract tool-specific functionality:

```
┌──────────────────────────────────────────────────────────┐
│                  site-nine Core                          │
│  (CLI, Tasks, Database, Agents - 80% of codebase)        │
└──────────────────┬───────────────────────────────────────┘
                   │
                   │ depends on
                   ▼
        ┌──────────────────────┐
        │   ToolAdapter API    │  ◄── Protocol/Interface
        │   (Abstract)         │
        └──────────────────────┘
                   △
                   │ implements
         ┌─────────┴──────────┬─────────────┐
         │                    │             │
┌────────▼────────┐  ┌───────▼────────┐  ┌▼──────────┐
│ OpenCodeAdapter │  │ CursorAdapter  │  │ AiderAdapter│
│  (Default)      │  │   (Planned)    │  │  (Planned)  │
└─────────────────┘  └────────────────┘  └──────────────┘
         │                    │                  │
         ▼                    ▼                  ▼
  ┌────────────┐      ┌─────────────┐    ┌────────────┐
  │  OpenCode  │      │Cursor MCP   │    │Aider CLI   │
  │    API     │      │    API      │    │    API     │
  └────────────┘      └─────────────┘    └────────────┘
```


### Key components

#### ToolAdapter protocol

**Planned location:** `src/site_nine/adapters/protocol.py`

Defines interface that all tool adapters must implement:

**Configuration & metadata:**
- `tool_name` - Tool identifier (opencode, cursor, aider)
- `tool_version` - Tool version string
- `config` - Unified configuration model

**Path resolution:**
- `get_tool_dir()` - Tool base directory (.opencode/, .cursor/, etc.)
- `get_data_dir()` - Data directory (database, caches)
- `get_docs_dir()` - Documentation directory
- `get_work_dir()` - Work directory (sessions, tasks, planning)
- `get_skills_dir()` - Skills directory
- `get_commands_dir()` - Commands directory
- `get_database_path()` - Database file path

**Configuration loading:**
- `load_config()` - Load and parse tool configuration file
- `get_config_path()` - Get path to tool's config file

**Skills system:**
- `load_skill(name)` - Load skill definition by name
- `list_skills()` - List all available skill names
- `get_skill_renderer()` - Get tool-specific skill renderer

**Commands system:**
- `load_command(name)` - Load command definition by name
- `list_commands()` - List all available command names

**Session management (optional):**
- `supports_session_api()` - Check if tool supports programmatic session management
- `rename_session(session_id, new_title)` - Rename tool session (if supported)
- `list_tool_sessions()` - List active tool sessions (if supported)

**Initialization:**
- `initialize_project(project_dir, config)` - Initialize new project with tool-specific structure

**Tool-specific features:**
- `get_capabilities()` - Return set of tool-specific capabilities
- `execute_tool_specific(feature, **kwargs)` - Execute tool-specific features not in protocol

**See:** Technical Design Document lines 138-356 for complete protocol specification


#### ToolRegistry

**Planned location:** `src/site_nine/adapters/registry.py`

Auto-detects which tool is active and loads appropriate adapter:

1. Checks for tool-specific directories (.opencode/, .cursor/, .aider/)
2. Checks for tool-specific marker files
3. Loads corresponding adapter
4. Provides fallback to OpenCode for backward compatibility

**See:** ADR-001 lines 75-78


#### OpenCodeAdapter

**Planned location:** `src/site_nine/adapters/opencode.py`

Implements ToolAdapter protocol for OpenCode. Wraps existing OpenCode-specific implementation to preserve exact 
behavior for backward compatibility.

**Example methods:**
- `get_tool_dir()` → Returns `.opencode/` directory
- `load_config()` → Parses `opencode.json` to unified ToolConfig model
- `get_database_path()` → Returns `.opencode/data/project.db`
- `supports_session_api()` → Returns `True` (OpenCode has TUI API)
- `rename_session()` → Calls existing session TUI integration

**See:** Technical Design Document lines 358-599 for implementation example


#### ToolConfig (unified model)

**Planned location:** `src/site_nine/core/tool_config.py`

Unified configuration model that abstracts over tool-specific config formats:

**Fields:**
- Tool identification (tool_name, tool_dir)
- Project metadata (project_name, project_type, description)
- Directory structure (data_dir, docs_dir, work_dir, skills_dir, commands_dir)
- Skills configuration (skills_paths)
- Commands configuration (commands dict)
- Features and roles (agent roles, feature flags)
- Custom variables

**Benefits:**
- Core code uses single ToolConfig model instead of tool-specific configs
- Each adapter maps tool config format to ToolConfig
- Enables tool-agnostic configuration handling

**See:** Technical Design Document lines 604-731


### Detection mechanism

The ToolRegistry auto-detects the active tool using this cascade:

1. Check for environment variable override (e.g., `S9_TOOL=cursor`)
2. Look for `.opencode/` directory → OpenCodeAdapter
3. Look for `.cursor/` directory → CursorAdapter
4. Look for `.aider/` directory → AiderAdapter
5. Check for tool-specific marker files
6. Default to OpenCodeAdapter for backward compatibility

**Note:** Detection mechanism not yet implemented. Design in ADR-001 lines 75-78.


### Implementation phases

**Phase 1: Foundation**
- Create ToolAdapter protocol
- Implement OpenCodeAdapter (wraps existing behavior)
- Add ToolRegistry with auto-detection
- Update core to use adapter (with OpenCode as default)

**Phase 2: Alternative tool adapters**
- Implement CursorAdapter (Cursor MCP)
- Implement AiderAdapter
- Test with each tool
- Document setup for each tool

**Phase 3: Configuration system**
- Unified ToolConfig abstraction
- Path mapping system
- Multi-tool project support

**Phase 4: Skills refactoring**
- Separate skill logic from presentation
- Generic skill execution engine
- Tool-specific skill renderers

**Phase 5: Documentation & reference update**
- Audit all files for outdated references
- Update documentation (README, ADRs, guides, API docs)
- Update bootstrapping/init templates
- Update .opencode/ agent directions and skills
    - Update all open tasks and possessions
- Verify no broken references remain

**See:** ADR-001 lines 180-211


### Benefits

- **Extensibility** - Easy to add new tools (Cursor, Aider, etc.)
- **Maintainability** - Single source of truth for core logic
- **Testability** - Adapters can be mocked/tested independently
- **Community growth** - Clear path for community contributions
- **Zero regression** - All current functionality retained

**See:** ADR-001 lines 213-222


### Trade-offs

**Costs:**
- Initial complexity from adding abstraction layer
- Each tool needs its adapter kept up-to-date
- Learning curve for contributors (adapter pattern)
- Cannot run integration tests (can't run coding agent from within another agent)
- Versioning complexity between site-nine, adapters, and external tools

**Mitigations:**
- Start minimal, extend only when needed (YAGNI principle)
- Version adapters, maintain compatibility matrix
- Manual testing protocol per adapter with smoke test checklist
- Excellent documentation and example adapters

**See:** ADR-001 lines 224-240


## Current implementation

**As of 2026-02-03**, the adapter pattern is **designed but not yet implemented**. Site-nine currently uses direct 
OpenCode integration:

**OpenCode session management:**
- Location: `src/site_nine/opencode/manager.py`
- Class: `OpenCodeSessionManager`
- Session detection via multiple methods (DB UUID, recency, diff correlation)
- Session renaming via OpenCode TUI API
- Database path: `~/.local/share/opencode/opencode.db`

**Path resolution:**
- Location: `src/site_nine/core/paths.py`
- Functions: `find_opencode_dir()`, `get_opencode_dir()`, `get_db_path()`
- Walks up directory tree to find `.opencode/`
- Security validation for paths within project

**Configuration:**
- File: `.opencode/opencode.json`
- OpenCode-specific format
- No unified ToolConfig model yet


## References

### Architecture decision records

- **ADR-001** - Adapter Pattern for Tool Abstraction (primary design)
- **ADR-008** - Agent Messaging System
- **ADR-009** - Agent Coordination Patterns
- **ADR-013** - Site-nine as OpenCode Integration Platform

### Technical documentation

- **Technical Design Document** - Complete adapter pattern specification (`.opencode/docs/architecture/technical-design-document.md`)
- **Implementation Roadmap** - Phased implementation plan (`.opencode/docs/architecture/implementation-roadmap.md`)

### Guides

- **Tasks** - `.opencode/docs/guides/tasks.md`
- **Agent Discovery** - `.opencode/docs/guides/agent-discovery.md`
- **Epic Possessions & Desk Mode** - `.opencode/docs/guides/epic-possessions-and-desk-mode.md`
- **Tool Adapters** - `.opencode/docs/guides/tool-adapters.md` (planned)

### Code locations

- **Database schema** - `src/site_nine/db/schema.sql`
- **OpenCode session management** - `src/site_nine/opencode/manager.py`
- **Path utilities** - `src/site_nine/core/paths.py`
- **CLI commands** - `src/site_nine/cli/`
- **Skills** - `.opencode/skills/`
