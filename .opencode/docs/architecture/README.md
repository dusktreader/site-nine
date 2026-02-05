# Site-Nine Multi-Tool Architecture

## Overview

This directory contains the complete architecture design for making site-nine compatible with multiple AI coding tools (OpenCode, Cursor, Aider, etc.).

**Status**: Architecture design COMPLETE (Task ARC-H-0030)  
**Next Phase**: Ready for Engineer implementation (Phase 1: Adapter Foundation)

## Architecture Documents

### 1. Architecture Decision Records (ADRs)

Located in `.opencode/docs/adrs/`:

- **[ADR-001: Adapter Pattern Abstraction](../adrs/ADR-001-adapter-pattern-abstraction.md)**
  - **Decision**: Use Adapter Pattern with 3-layer architecture
  - **Alternatives Considered**: Plugin architecture, tool-specific forks, config templating, monolithic conditionals
  - **Rationale**: Right-sized abstraction for 20% tool-coupled code
  - **Key Insight**: Core depends on ToolAdapter protocol (Dependency Inversion)

- **[ADR-002: Cursor MCP First Target](../adrs/ADR-002-cursor-mcp-first-target.md)**
  - **Decision**: Cursor MCP as first multi-tool target
  - **Alternatives Considered**: Aider, GitHub Copilot CLI, Claude Code
  - **Rationale**: MCP is open standard, strong API, large market, validates adapter pattern
  - **Key Insight**: Aider too simple (not representative), Copilot too closed

- **[ADR-003: Unified Configuration System](../adrs/ADR-003-unified-configuration-system.md)**
  - **Decision**: Tool-specific configs (opencode.json, cursor.json) normalized to ToolConfig
  - **Alternatives Considered**: Unified .s9.json, environment variables only, symlinks
  - **Rationale**: Respects tool conventions, clear mental model, extensible
  - **Key Insight**: ToolRegistry auto-detects active tool via directory markers

- **[ADR-004: Skills Refactoring Approach](../adrs/ADR-004-skills-refactoring-approach.md)**
  - **Decision**: 3-layer skills architecture (Definition → Executor → Renderer)
  - **Alternatives Considered**: Tool-specific skill duplication, embedded conditionals, Python-only skills
  - **Rationale**: Separates "what to do" from "how to present"
  - **Key Insight**: skill.yaml for logic, tool-specific renderers for presentation

- **[ADR-005: Backward Compatibility Strategy](../adrs/ADR-005-backward-compatibility-strategy.md)**
  - **Decision**: Zero breaking changes, OpenCode is default, gradual migration
  - **Alternatives Considered**: Clean break (v2.0 incompatible), parallel packages, feature flags
  - **Rationale**: Respect existing users, reduce migration friction, maintain trust
  - **Key Insight**: OpenCodeAdapter wraps existing code (thin wrapper, not rewrite)

### 2. Technical Design Documents

- **[Technical Design Document (Part 1)](./technical-design-document.md)**
  - System architecture (4-layer: CLI → Application → Abstraction → Tool Adapter)
  - Complete ToolAdapter protocol specification (30+ methods with signatures, types, docstrings)
  - OpenCodeAdapter implementation example
  - ToolConfig unified model specification
  - Config loaders for OpenCode, Cursor, Aider

- **[Technical Design Document (Part 2)](./technical-design-document-part2.md)**
  - Skills system architecture (skill.yaml format)
  - SkillExecutor implementation (executes tool-agnostic workflows)
  - SkillRenderer protocol (tool-specific output)
  - ToolRegistry implementation (auto-detection, adapter selection)
  - Data flow diagrams (skill execution, config loading)
  - Sequence diagrams (task management with adapters)
  - Error handling strategy (exception hierarchy)
  - Testing strategy (test pyramid: 70% unit, 25% integration, 5% E2E)

### 3. Proof of Concept Specification

- **[Cursor MCP PoC Specification](./cursor-mcp-poc-spec.md)**
  - Complete CursorAdapter implementation spec
  - MCP server implementation (JSON-RPC 2.0 over stdio)
  - MCP protocol integration (initialize, tools/list, tools/call)
  - cursor.json template with MCP server configuration
  - Demo scenario walkthrough
  - PoC validation tests and success criteria

### 4. Implementation Roadmap

- **[Implementation Roadmap](./implementation-roadmap.md)**
  - Detailed 6-8 week timeline broken into 5 phases
  - **Phase 1 (Weeks 1-2)**: Adapter Foundation - protocols, OpenCodeAdapter, ToolRegistry
  - **Phase 2 (Weeks 3-4)**: Cursor MCP Integration - CursorAdapter, MCP server, E2E tests
  - **Phase 3 (Week 5)**: Unified Configuration - ToolConfig, config loaders, PathResolver
  - **Phase 4 (Week 6)**: Skills Refactoring - skill.yaml format, executor, legacy converter
  - **Phase 5 (Weeks 7-8)**: Testing & Polish - 90% coverage, docs, v2.0.0 release
  - Each phase has detailed tasks, deliverables, acceptance criteria
  - Risk management and success metrics

## Quick Start for Engineers

### Reading Order

If you're implementing this architecture, read these documents in this order:

1. **[ADR-001](../adrs/ADR-001-adapter-pattern-abstraction.md)** - Understand why adapter pattern (5 min)
2. **[ADR-005](../adrs/ADR-005-backward-compatibility-strategy.md)** - Understand backward compatibility requirements (5 min)
3. **[Technical Design Part 1](./technical-design-document.md)** - Learn ToolAdapter protocol (20 min)
4. **[Implementation Roadmap](./implementation-roadmap.md)** - See task breakdown (15 min)
5. **Current Codebase** - Review `src/site_nine/core/paths.py` to understand existing path resolution (10 min)

Total reading time: ~1 hour

### Implementation Start

**Phase 1, Week 1, Task 1.1: Create ToolAdapter Protocol**

```bash
# Create the adapter protocol
touch src/site_nine/adapters/__init__.py
touch src/site_nine/adapters/protocol.py

# Refer to technical-design-document.md for complete ToolAdapter protocol specification
```

See [Implementation Roadmap](./implementation-roadmap.md) for detailed task breakdown.

## Key Architecture Decisions

### 1. Adapter Pattern (3-Layer Architecture)

```
┌─────────────────────────────────────────────┐
│ Core (tool-agnostic business logic)        │
│ - Task management, agent orchestration     │
│ - Session tracking, work logs              │
└─────────────────┬───────────────────────────┘
                  │ depends on
┌─────────────────▼───────────────────────────┐
│ ToolAdapter Protocol (abstraction layer)   │
│ - Interface with 30+ methods                │
│ - Tool-agnostic contract                    │
└─────────────────┬───────────────────────────┘
                  │ implemented by
┌─────────────────▼───────────────────────────┐
│ Concrete Adapters (tool-specific)           │
│ - OpenCodeAdapter (wraps existing code)    │
│ - CursorAdapter (MCP protocol)             │
│ - AiderAdapter (future)                    │
└─────────────────────────────────────────────┘
```

**Key Principle**: Core depends on abstractions (ToolAdapter), not concrete implementations.

### 2. Tool Detection & Configuration

- **Auto-detection**: ToolRegistry detects active tool via directory markers
  - `.opencode/` → OpenCodeAdapter (default)
  - `.cursor/` → CursorAdapter
  - `.aider/` → AiderAdapter
- **Unified Config**: Tool-specific configs normalized to ToolConfig model
- **Backward Compatible**: No config required for existing OpenCode users

### 3. Skills Refactoring (3-Layer)

```
skill.yaml (Definition)
    ↓
SkillExecutor (Execution)
    ↓
SkillRenderer (Presentation)
    ├─ OpenCodeSkillRenderer → SKILL.md format
    ├─ CursorSkillRenderer → MCP format
    └─ AiderSkillRenderer → Aider format
```

**Key Principle**: Separate workflow logic (what to do) from presentation (how to format).

### 4. Backward Compatibility Strategy

- **OpenCode is Default**: Existing `.opencode/` projects work unchanged
- **Zero Breaking Changes**: All existing tests must pass (100%)
- **Gradual Migration**: Legacy formats supported indefinitely
- **Semantic Versioning**: v2.0.0 = multi-tool support (backward compatible, not breaking)

## Success Criteria

### Architecture Phase (COMPLETE ✅)

- ✅ All 8 deliverables completed
- ✅ 5 ADRs documenting key decisions
- ✅ 2-part technical design document (50+ pages)
- ✅ Cursor MCP PoC specification ready for implementation
- ✅ 6-8 week implementation roadmap with task breakdown
- ✅ Engineer can start Phase 1 without architectural blockers

### Implementation Phase (Next)

**Phase 1 Acceptance Criteria:**
- [ ] ToolAdapter protocol created with all 30+ methods
- [ ] OpenCodeAdapter implemented (wraps existing code)
- [ ] ToolRegistry implemented (auto-detects OpenCode)
- [ ] All existing tests pass (100%)
- [ ] New unit tests for adapters (90%+ coverage)
- [ ] Performance within 5% of v1.x.x baseline

See [Implementation Roadmap](./implementation-roadmap.md) for complete acceptance criteria.

## Timeline

- **Architecture Design**: 1 week (COMPLETE ✅)
- **Phase 1 Implementation**: 2 weeks (Adapter Foundation)
- **Phase 2 Implementation**: 2 weeks (Cursor MCP Integration)
- **Phase 3 Implementation**: 1 week (Unified Configuration)
- **Phase 4 Implementation**: 1 week (Skills Refactoring)
- **Phase 5 Implementation**: 2 weeks (Testing & Polish)

**Total**: 7-9 weeks from architecture start to v2.0.0 release

## Related Tasks

- **ADM-H-0029**: Research findings (80% of codebase already tool-agnostic) - COMPLETE
- **ARC-H-0030**: Architecture design (this work) - COMPLETE ✅
- **Next**: Phase 1 implementation tasks (to be created by Engineer)

## Contact & Questions

If you have questions about this architecture:

1. Review the ADRs - they explain the "why" behind decisions
2. Check the Technical Design Documents for detailed specifications
3. Refer to the Implementation Roadmap for task-level guidance
4. Review existing codebase in `src/site_nine/` to understand current patterns

## Document Index

### By Topic

**Getting Started:**
- [ADR-001: Adapter Pattern](../adrs/ADR-001-adapter-pattern-abstraction.md) - Why this architecture?
- [ADR-005: Backward Compatibility](../adrs/ADR-005-backward-compatibility-strategy.md) - Zero breaking changes
- [Implementation Roadmap](./implementation-roadmap.md) - Where to start?

**Technical Specifications:**
- [Technical Design Part 1](./technical-design-document.md) - ToolAdapter protocol
- [Technical Design Part 2](./technical-design-document-part2.md) - Skills, Registry, Testing
- [Cursor MCP PoC Spec](./cursor-mcp-poc-spec.md) - First concrete adapter

**Design Decisions:**
- [ADR-002: Cursor MCP Target](../adrs/ADR-002-cursor-mcp-first-target.md) - Why Cursor first?
- [ADR-003: Configuration System](../adrs/ADR-003-unified-configuration-system.md) - How configs work?
- [ADR-004: Skills Refactoring](../adrs/ADR-004-skills-refactoring-approach.md) - How skills work?

### By Phase

**Phase 1 (Weeks 1-2): Adapter Foundation**
- [Technical Design Part 1](./technical-design-document.md) - ToolAdapter protocol spec
- [ADR-001](../adrs/ADR-001-adapter-pattern-abstraction.md) - Adapter pattern rationale
- [ADR-005](../adrs/ADR-005-backward-compatibility-strategy.md) - OpenCodeAdapter requirements

**Phase 2 (Weeks 3-4): Cursor MCP Integration**
- [Cursor MCP PoC Spec](./cursor-mcp-poc-spec.md) - CursorAdapter specification
- [ADR-002](../adrs/ADR-002-cursor-mcp-first-target.md) - Why Cursor MCP?
- [Technical Design Part 2](./technical-design-document-part2.md) - ToolRegistry for detection

**Phase 3 (Week 5): Unified Configuration**
- [ADR-003](../adrs/ADR-003-unified-configuration-system.md) - Configuration design
- [Technical Design Part 1](./technical-design-document.md) - ToolConfig specification

**Phase 4 (Week 6): Skills Refactoring**
- [ADR-004](../adrs/ADR-004-skills-refactoring-approach.md) - Skills architecture
- [Technical Design Part 2](./technical-design-document-part2.md) - SkillExecutor & SkillRenderer

**Phase 5 (Weeks 7-8): Testing & Polish**
- [Technical Design Part 2](./technical-design-document-part2.md) - Testing strategy
- [Implementation Roadmap](./implementation-roadmap.md) - Release criteria

---

**Architecture Status**: COMPLETE ✅  
**Ready for**: Engineer implementation (Phase 1)  
**Task**: ARC-H-0030 (COMPLETE)  
**Architect**: Ptah  
**Date**: 2026-02-03
