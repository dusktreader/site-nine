# ADR-001: Adapter Pattern for Tool Abstraction

**Status:** Proposed
**Date:** 2026-02-03
**Deciders:** Ptah (Architect)
**Related Tasks:** ARC-H-0030, ADM-H-0029

## Context

Site-nine is currently tightly coupled to OpenCode as its primary AI coding tool. To make site-nine a universal AI
coding workflow system that works with multiple tools (GitHub Copilot CLI, Claude Code, Crush, etc.), we need to
introduce an abstraction layer.

### Current State

Based on codebase analysis:
- **80% tool-agnostic**: Core functionality (task management, database, CLI) works independently
- **20% tool-coupled**: Integration points in:
  - `.opencode/` directory structure (hardcoded paths)
  - `opencode.json` configuration file
  - Skills system (OpenCode-specific skill invocation via `skill(name="...")`)
  - Commands system (`.opencode/commands/*.md` templates for OpenCode)
  - Session TUI integration (renaming OpenCode sessions via API)

### Requirements

1. **Multi-tool support**: Enable site-nine to work with OpenCode, GitHub Copilot CLI, Claude Code, Crush, and future
   tools
2. **Zero regression**: All current site-nine features and functionality must be retained
3. **Minimal coupling**: New abstractions should be clean and maintainable
4. **Extensibility**: Community should be able to add new tool adapters
5. **Complete documentation update**: ALL documentation, bootstrapping files, .opencode/ agent directions, open tasks,
   open missions, and any other references must be updated to reflect changes. No outdated references left behind.

## Decision

We will use the **Adapter Pattern** with **dependency injection** to abstract tool-specific functionality.

### Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│                  site-nine Core                      │
│  (CLI, Tasks, Database, Agents - 80% of codebase)    │
└──────────────────┬───────────────────────────────────┘
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
│ OpenCodeAdapter │  │ CopilotAdapter │  │ ClaudeCode│
│  (Default)      │  │   (CLI)        │  │  Adapter  │
└─────────────────┘  └────────────────┘  └───────────┘
         │                    │                  │
         ▼                    ▼                  ▼
  ┌────────────┐      ┌─────────────┐    ┌────────────┐
  │  OpenCode  │      │ Copilot CLI │    │Claude Code │
  │    API     │      │     API     │    │    API     │
  └────────────┘      └─────────────┘    └────────────┘
```

### Key Components

1. **ToolAdapter Protocol** (`src/site_nine/adapters/protocol.py`)
   - Defines interface that all tool adapters must implement
   - Methods: `load_skill()`, `execute_command()`, `get_config_path()`, `rename_session()`, etc.

2. **ToolRegistry** (`src/site_nine/adapters/registry.py`)
   - Auto-detects which tool is active (by checking for `.opencode/`, tool-specific markers, etc.)
   - Loads appropriate adapter
   - Provides fallback to OpenCode for backward compatibility

3. **Concrete Adapters** (`src/site_nine/adapters/opencode.py`, `copilot.py`, `claude_code.py`, `crush.py`, etc.)
   - Implement ToolAdapter protocol for specific tools
   - Handle tool-specific API calls and configuration

4. **Config Abstraction** (`src/site_nine/core/tool_config.py`)
   - Unified configuration model that maps to tool-specific configs
   - Handles path resolution (`.opencode/` vs tool-specific directories)

## Alternatives Considered

### Alternative 1: Plugin Architecture

**Approach**: Make site-nine a plugin system where each tool is a plugin.

**Pros**:
- Maximum flexibility for tool integrations
- Clear separation of concerns
- Easy to add/remove tools

**Cons**:
- **Over-engineered** for our needs (only ~20% of code needs abstraction)
- Higher complexity overhead (plugin discovery, loading, lifecycle management)
- Harder to maintain backward compatibility
- Risk of breaking existing users with plugin system refactor

**Rejected because**: Too much complexity for the problem size.

### Alternative 2: Tool-Specific Forks

**Approach**: Fork site-nine for each tool (s9-opencode, s9-copilot, s9-claude-code, s9-crush).

**Pros**:
- Simple implementation
- No abstraction complexity
- Each fork optimized for its tool

**Cons**:
- **Maintenance nightmare** (bug fixes need N updates)
- Feature divergence across forks
- User confusion about which version to use
- Defeats the goal of a "universal" system

**Rejected because**: Violates DRY principle and creates long-term maintenance burden.

### Alternative 3: Configuration-Based Templating

**Approach**: Use configuration files and templates to support multiple tools without code abstraction.

**Pros**:
- No code changes needed
- Simple for basic differences

**Cons**:
- **Limited flexibility** for tool-specific behaviors (e.g., session TUI renaming, MCP server integration)
- Templates become complex with conditionals
- Hard to extend for future tools with different APIs
- Doesn't handle runtime tool detection

**Rejected because**: Insufficient for actual tool API differences.

### Alternative 4: Monolithic Conditional Logic

**Approach**: Add `if tool == "opencode"` / `elif tool == "copilot"` / `elif tool == "claude_code"` throughout
codebase.

**Pros**:
- Simple to understand
- Easy to start

**Cons**:
- **Violates Open/Closed Principle** (not open for extension)
- Code becomes littered with conditionals
- Hard to test
- High coupling
- Difficult for community to add new tools

**Rejected because**: Poor software engineering practice, not extensible.

## Rationale for Adapter Pattern

### Why Adapter Pattern Wins

1. **Right-sized abstraction**: Only abstracts the 20% that needs it
2. **Open/Closed Principle**: New tools added without modifying existing code
3. **Testability**: Each adapter can be tested independently
4. **Zero regression**: All site-nine features retained across tools
5. **Community-friendly**: Clear interface for community adapters
6. **Industry standard**: Well-understood pattern with proven track record

### Implementation Strategy

**Focused Migration Approach:**

This will be implemented as a coordinated effort with Operators in a focused migration period. During this time, no
other agents will be actively working on the system, eliminating backwards compatibility concerns.

**Critical Requirement:** Every reference to changed concepts must be updated - documentation, bootstrapping, agent
directions, open tasks, open missions, skills, templates, and any other artifacts. A comprehensive audit checklist
must be completed before the migration is considered done.

**Phase 1: Foundation**
- Create ToolAdapter protocol
- Implement OpenCodeAdapter (wraps existing behavior)
- Add ToolRegistry with auto-detection
- Update core to use adapter (with OpenCode as default)

**Phase 2: Initial Alternative Tool Adapters**
- Implement CopilotAdapter (GitHub Copilot CLI)
- Implement ClaudeCodeAdapter
- Implement CrushAdapter
- Test with each tool
- Document setup for each tool

**Phase 3: Configuration System**
- Unified ToolConfig abstraction
- Path mapping system
- Multi-tool project support

**Phase 4: Skills Refactoring**
- Separate skill logic from presentation
- Generic skill execution engine
- Tool-specific skill renderers

**Phase 5: Comprehensive Documentation & Reference Update**
- Audit ALL files for outdated references (grep/search for old terms)
- Update documentation (README, ADRs, guides, API docs)
- Update bootstrapping/init templates
- Update .opencode/ agent directions and skills
- Update all open tasks and missions
- Update CLI help text and error messages
- Update code comments
- Verify no broken references remain

## Consequences

### Positive

- ✅ **Extensibility**: Easy to add new tools (Copilot CLI, Claude Code, Crush, etc.)
- ✅ **Maintainability**: Single source of truth for core logic
- ✅ **Testability**: Adapters can be mocked/tested independently
- ✅ **Community growth**: Clear path for community contributions
- ✅ **Zero regression**: All current functionality retained across tool adapters

### Negative

- ⚠️ **Initial complexity**: Adding abstraction layer requires upfront work
- ⚠️ **Adapter maintenance**: Each tool needs its adapter kept up-to-date
- ⚠️ **Learning curve**: Contributors need to understand adapter pattern
- ⚠️ **Testing limitations**: Cannot run integration tests (can't run coding agent from within another agent)
- ⚠️ **Versioning complexity**: Tracking compatibility between site-nine, adapters, and external tools could become 
  complex; need to keep versioning strategy simple or risk maintenance burden

### Risks & Mitigation

| Risk                                                                           | Mitigation                                                                                                                                                                  |
|--------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Adapter API becomes bloated                                                    | Start minimal, extend only when needed (YAGNI)                                                                                                                              |
| Tool APIs change breaking adapters                                             | Version adapters, maintain adapter compatibility matrix with supported tool versions                                                                                        |
| Adapters can't be integration tested (can't run coding agent from within another) | Manual testing protocol per adapter with comprehensive smoke test checklist; real-world validation with each tool before release; document expected behavior per adapter |
| Performance overhead from abstraction                                          | Benchmark critical paths, optimize hot paths, lazy loading                                                                                                                  |
| Community doesn't adopt                                                        | Excellent docs, example adapter, support                                                                                                                                    |

## Compliance

This decision supports:
- **Project Goal**: Making site-nine a universal AI coding workflow system
- **Research Findings**: 80% of codebase already tool-agnostic (ADM-H-0029)
- **Zero Regression**: All current site-nine features retained across tools
- **Migration Strategy**: Focused effort with Operators during coordinated transition period

## References

- Task ADM-H-0029: Research findings on tool-agnostic architecture
- Task ARC-H-0030: This architecture design task
- Current codebase: `src/site_nine/` (especially `core/paths.py`, `cli/agent.py`)
- Design Patterns: GoF Adapter Pattern
- SOLID Principles: Open/Closed, Dependency Inversion

## Notes

This ADR focuses on **why** we chose the adapter pattern. Detailed **how** specifications (interface methods, class diagrams, sequence diagrams) are in the Technical Design Document.

Next ADRs will cover:
- ADR-002: Target tools prioritization (Copilot CLI, Claude Code, Crush)
- ADR-003: Configuration system design
- ADR-004: Skills refactoring approach
- ADR-005: Backward compatibility strategy
