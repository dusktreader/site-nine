# ADR-001: Adapter Pattern for Tool Abstraction

**Status:** Proposed  
**Date:** 2026-02-03  
**Deciders:** Ptah (Architect)  
**Related Tasks:** ARC-H-0030, ADM-H-0029

## Context

Site-nine is currently tightly coupled to OpenCode as its primary AI coding tool. To make site-nine a universal AI coding workflow system that works with multiple tools (Cursor, Aider, GitHub Copilot CLI, etc.), we need to introduce an abstraction layer.

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

1. **Multi-tool support**: Enable site-nine to work with OpenCode, Cursor MCP, Aider, and future tools
2. **Zero regression**: Existing OpenCode users must continue working without changes
3. **Minimal coupling**: New abstractions should be clean and maintainable
4. **Extensibility**: Community should be able to add new tool adapters
5. **Gradual migration**: Refactoring should happen in phases without breaking existing functionality

## Decision

We will use the **Adapter Pattern** with **dependency injection** to abstract tool-specific functionality.

### Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│                  site-nine Core                       │
│  (CLI, Tasks, Database, Agents - 80% of codebase)   │
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
         ┌─────────┴──────────┐
         │                    │
┌────────▼────────┐  ┌───────▼────────┐
│ OpenCodeAdapter │  │ CursorAdapter  │
│  (Default)      │  │   (MCP)        │
└─────────────────┘  └────────────────┘
         │                    │
         ▼                    ▼
  ┌────────────┐      ┌──────────────┐
  │  OpenCode  │      │ Cursor MCP   │
  │    API     │      │     API      │
  └────────────┘      └──────────────┘
```

### Key Components

1. **ToolAdapter Protocol** (`src/site_nine/adapters/protocol.py`)
   - Defines interface that all tool adapters must implement
   - Methods: `load_skill()`, `execute_command()`, `get_config_path()`, `rename_session()`, etc.

2. **ToolRegistry** (`src/site_nine/adapters/registry.py`)
   - Auto-detects which tool is active (by checking for `.opencode/`, `.cursor/`, `.aider/` etc.)
   - Loads appropriate adapter
   - Provides fallback to OpenCode for backward compatibility

3. **Concrete Adapters** (`src/site_nine/adapters/opencode.py`, `cursor.py`, etc.)
   - Implement ToolAdapter protocol for specific tools
   - Handle tool-specific API calls and configuration

4. **Config Abstraction** (`src/site_nine/core/tool_config.py`)
   - Unified configuration model that maps to tool-specific configs
   - Handles path resolution (`.opencode/` vs `.cursor/` vs `.aider/`)

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

**Approach**: Fork site-nine for each tool (s9-opencode, s9-cursor, s9-aider).

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

**Approach**: Add `if tool == "opencode"` / `elif tool == "cursor"` throughout codebase.

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
4. **Backward compatibility**: OpenCodeAdapter is default, zero breaking changes
5. **Community-friendly**: Clear interface for community adapters
6. **Industry standard**: Well-understood pattern with proven track record

### Implementation Strategy

**Phase 1: Foundation (Weeks 1-2)**
- Create ToolAdapter protocol
- Implement OpenCodeAdapter (wraps existing behavior)
- Add ToolRegistry with auto-detection
- Update core to use adapter (with OpenCode as default)
- **No user-facing changes** - pure refactoring

**Phase 2: Cursor MCP Adapter (Weeks 3-4)**
- Implement CursorAdapter
- Add Cursor MCP server integration
- Test with Cursor users
- Document Cursor setup

**Phase 3: Configuration System (Week 5)**
- Unified ToolConfig abstraction
- Path mapping system
- Multi-tool project support

**Phase 4: Skills Refactoring (Week 6)**
- Separate skill logic from presentation
- Generic skill execution engine
- Tool-specific skill renderers

## Consequences

### Positive

- ✅ **Extensibility**: Easy to add new tools (Aider, Claude Code, etc.)
- ✅ **Maintainability**: Single source of truth for core logic
- ✅ **Testability**: Adapters can be mocked/tested independently
- ✅ **Community growth**: Clear path for community contributions
- ✅ **Zero regression**: OpenCode users unaffected

### Negative

- ⚠️ **Initial complexity**: Adding abstraction layer requires upfront work
- ⚠️ **Adapter maintenance**: Each tool needs its adapter kept up-to-date
- ⚠️ **Learning curve**: Contributors need to understand adapter pattern

### Risks & Mitigation

| Risk | Mitigation |
|------|------------|
| Adapter API becomes bloated | Start minimal, extend only when needed (YAGNI) |
| Tool APIs change breaking adapters | Version adapters, adapter compatibility matrix |
| Performance overhead from abstraction | Benchmark, optimize hot paths, lazy loading |
| Community doesn't adopt | Excellent docs, example adapter, support |

## Compliance

This decision supports:
- **Project Goal**: Making site-nine a universal AI coding workflow system
- **Research Findings**: 80% of codebase already tool-agnostic (ADM-H-0029)
- **User Requirement**: Backward compatibility for existing OpenCode users

## References

- Task ADM-H-0029: Research findings on tool-agnostic architecture
- Task ARC-H-0030: This architecture design task
- Current codebase: `src/site_nine/` (especially `core/paths.py`, `cli/agent.py`)
- Design Patterns: GoF Adapter Pattern
- SOLID Principles: Open/Closed, Dependency Inversion

## Notes

This ADR focuses on **why** we chose the adapter pattern. Detailed **how** specifications (interface methods, class diagrams, sequence diagrams) are in the Technical Design Document.

Next ADRs will cover:
- ADR-002: Cursor MCP vs Aider as first target
- ADR-003: Configuration system design
- ADR-004: Skills refactoring approach
- ADR-005: Backward compatibility strategy
