# Implementation Roadmap: Multi-Tool Support

**Version:** 1.0  
**Date:** 2026-02-03  
**Author:** Ptah (Architect)  
**Timeline:** XXL (Epic-level multi-phase implementation)  
**Related Task:** ARC-H-0030

---

## Overview

This roadmap details the phased implementation of multi-tool support for site-nine, transforming it from an OpenCode-specific system to a universal AI coding workflow framework.

### Goals

- Implement adapter pattern with zero OpenCode regression
- Add Cursor MCP support as proof-of-concept
- Refactor skills system for tool-agnostic execution
- Maintain backward compatibility throughout

### Timeline Summary

| Phase | Size | Focus | Outcome |
|-------|------|-------|---------|
| Phase 1 | XL | Adapter Foundation | OpenCodeAdapter working, zero regression |
| Phase 2 | XL | Cursor MCP Integration | CursorAdapter working, MCP server live |
| Phase 3 | L | Configuration System | Unified ToolConfig, path resolution |
| Phase 4 | L | Skills Refactoring | New skill.yaml format, legacy support |
| Phase 5 | XL | Testing & Polish | Comprehensive tests, documentation |

---

## Phase 1: Adapter Foundation (XL)

**Goal**: Introduce adapter pattern without changing any user-facing behavior.

### Core Abstractions

#### Tasks

**1.1 Create ToolAdapter Protocol (M)**
- File: `src/site_nine/adapters/protocol.py`
- Define ToolAdapter protocol with all required methods
- Add comprehensive docstrings
- Include type hints for all methods

**Deliverables:**
- [ ] ToolAdapter protocol implemented
- [ ] Protocol validated with mypy
- [ ] Documentation generated

**Acceptance Criteria:**
- Protocol defines 20+ methods
- All methods have type hints
- Docstrings explain purpose and usage

---

**1.2 Implement OpenCodeAdapter (L)**
- File: `src/site_nine/adapters/opencode.py`
- Wrap existing OpenCode functionality
- Delegate to existing code (no rewrites)
- Implement all ToolAdapter methods

**Deliverables:**
- [ ] OpenCodeAdapter class
- [ ] All protocol methods implemented
- [ ] Unit tests (90%+ coverage)

**Acceptance Criteria:**
- OpenCodeAdapter passes all ToolAdapter protocol checks
- Delegates to existing `get_opencode_dir()`, etc.
- All tests pass

---

**1.3 Create ToolRegistry (M)**
- File: `src/site_nine/adapters/registry.py`
- Implement tool detection logic
- Implement adapter selection
- Add adapter registration system

**Deliverables:**
- [ ] ToolRegistry class
- [ ] Tool detection (environment, directory walking)
- [ ] Adapter registry
- [ ] Unit tests

**Acceptance Criteria:**
- `detect_tool()` finds `.opencode/` directories
- `get_adapter()` returns OpenCodeAdapter by default
- Detection works from any subdirectory

### Core Integration

**1.4 Refactor Core to Use Adapters (XL)**
- Files: `src/site_nine/cli/*.py`, `src/site_nine/tasks/*.py`, `src/site_nine/agents/*.py`
- Replace direct `get_opencode_dir()` calls with `ToolRegistry.get_adapter()`
- Update path resolution to use adapter methods
- Maintain exact same behavior

**Deliverables:**
- [ ] All CLI commands use adapters
- [ ] TaskManager uses adapters
- [ ] AgentSessionManager uses adapters
- [ ] Backward compatibility tests

**Acceptance Criteria:**
- All existing integration tests pass unchanged
- Manual testing shows identical behavior
- No performance regression (< 5% slower)

**Changes by file:**
```python
# Before
from site_nine.core.paths import get_opencode_dir
opencode_dir = get_opencode_dir()
db_path = opencode_dir / "data" / "project.db"

# After
from site_nine.adapters.registry import ToolRegistry
adapter = ToolRegistry.get_adapter()
db_path = adapter.get_database_path()
```

---

**1.5 Testing & Validation (L)**
- Run full test suite
- Manual testing of all CLI commands
- Performance benchmarking
- Fix any regressions

**Deliverables:**
- [ ] All tests passing
- [ ] Performance benchmarks
- [ ] Regression test report
- [ ] Bug fixes

**Acceptance Criteria:**
- 100% of existing tests pass
- Performance within 5% of baseline
- Zero user-facing changes

---

### Phase 1 Completion Criteria

- ✅ ToolAdapter protocol defined
- ✅ OpenCodeAdapter implemented and tested
- ✅ ToolRegistry working
- ✅ Core refactored to use adapters
- ✅ All existing tests pass
- ✅ Zero user-facing changes
- ✅ Code review complete

---

## Phase 2: Cursor MCP Integration (XL)

**Goal**: Implement CursorAdapter and MCP server, validate adapter pattern.

### CursorAdapter & MCP Server

**2.1 Implement CursorAdapter (L)**
- File: `src/site_nine/adapters/cursor.py`
- Implement ToolAdapter protocol for Cursor
- Handle `.cursor/` directory structure
- Map Cursor paths

**Deliverables:**
- [ ] CursorAdapter class
- [ ] All protocol methods
- [ ] Unit tests

**Acceptance Criteria:**
- CursorAdapter implements ToolAdapter
- Handles `.cursor/` paths correctly
- Tests pass

---

**2.2 Implement CursorConfigLoader (M)**
- File: `src/site_nine/adapters/config_loaders.py`
- Parse `cursor.json` (MCP format)
- Normalize to ToolConfig
- Handle MCP-specific fields

**Deliverables:**
- [ ] CursorConfigLoader class
- [ ] cursor.json parsing
- [ ] ToolConfig mapping
- [ ] Unit tests

**Acceptance Criteria:**
- Loads cursor.json correctly
- Maps to ToolConfig
- Tests pass

---

**2.3 Create MCP Server (L)**
- File: `src/site_nine/mcp/server.py`
- Implement JSON-RPC 2.0 server
- Handle MCP protocol messages
- Expose skills as MCP tools
- Add `s9 mcp server` CLI command

**Deliverables:**
- [ ] MCP server implementation
- [ ] JSON-RPC handler
- [ ] Tool registration
- [ ] CLI command
- [ ] Integration tests

**Acceptance Criteria:**
- Server handles MCP initialize
- Server lists site-nine skills as tools
- Server executes skills via tools/call
- Passes MCP protocol compliance tests

---

**2.4 Create cursor.json Template (S)**
- File: `src/site_nine/templates/cursor/cursor.json.jinja`
- Define Cursor MCP configuration
- Include site-nine MCP server
- Add Cursor rules

**Deliverables:**
- [ ] cursor.json template
- [ ] Template rendering
- [ ] Init command support (`s9 init --tool cursor`)

**Acceptance Criteria:**
- `s9 init --tool cursor` creates `.cursor/` structure
- cursor.json includes site-nine MCP server
- Cursor can connect to MCP server

### Integration & Testing

**2.5 Implement CursorMCPRenderer (M)**
- File: `src/site_nine/skills/renderers/cursor.py`
- Implement SkillRenderer for Cursor
- Handle MCP protocol output
- Format messages for Cursor

**Deliverables:**
- [ ] CursorMCPRenderer class
- [ ] MCP message formatting
- [ ] Unit tests

**Acceptance Criteria:**
- Renders skill output via MCP
- Handles questions via MCP
- Tests pass

---

**2.6 End-to-End Testing (L)**
- Test full workflow in Cursor
- Test task management
- Test agent sessions
- Test skills execution

**Deliverables:**
- [ ] E2E test suite for Cursor
- [ ] Test report
- [ ] Bug fixes

**Acceptance Criteria:**
- Session-start skill works in Cursor
- Task commands work in Cursor
- Agent sessions tracked
- Demo video recorded

---

**2.7 Register CursorAdapter (S)**
- Update ToolRegistry to include Cursor
- Update tool detection priority
- Update documentation

**Deliverables:**
- [ ] CursorAdapter registered
- [ ] Detection updated
- [ ] Documentation

**Acceptance Criteria:**
- ToolRegistry detects `.cursor/`
- Returns CursorAdapter for Cursor projects
- OpenCode still default

---

### Phase 2 Completion Criteria

- ✅ CursorAdapter implemented
- ✅ MCP server working
- ✅ Cursor can invoke site-nine skills
- ✅ E2E tests pass
- ✅ Demo completed
- ✅ Documentation updated

---

## Phase 3: Unified Configuration (L)

**Goal**: Implement unified configuration system across tools.

**3.1 Create ToolConfig Model (M)**
- File: `src/site_nine/core/tool_config.py`
- Define unified configuration dataclass
- Add helper methods
- Add template context generation

**Deliverables:**
- [ ] ToolConfig dataclass
- [ ] CommandConfig, FeaturesConfig classes
- [ ] Unit tests

---

**3.2 Implement Config Loaders (M)**
- File: `src/site_nine/adapters/config_loaders.py`
- OpenCodeConfigLoader (opencode.json → ToolConfig)
- CursorConfigLoader (cursor.json → ToolConfig)
- Config loader registry

**Deliverables:**
- [ ] Config loader protocol
- [ ] OpenCodeConfigLoader
- [ ] CursorConfigLoader
- [ ] Unit tests

---

**3.3 Refactor PathResolver (S)**
- File: `src/site_nine/core/paths.py`
- Create PathResolver class
- Add template-based path resolution
- Update adapters to use PathResolver

**Deliverables:**
- [ ] PathResolver class
- [ ] Path templates
- [ ] Unit tests

---

### Phase 3 Completion Criteria

- ✅ ToolConfig model complete
- ✅ Config loaders implemented
- ✅ PathResolver working
- ✅ Tests passing

---

## Phase 4: Skills Refactoring (L)

**Goal**: Introduce new skill format with legacy support.

**4.1 Create SkillDefinition Model (S)**
- File: `src/site_nine/skills/definition.py`
- Define skill.yaml schema
- Parse YAML format
- Validation

**Deliverables:**
- [ ] SkillDefinition dataclass
- [ ] SkillStep dataclass
- [ ] YAML parser

---

**4.2 Implement SkillExecutor (L)**
- File: `src/site_nine/skills/executor.py`
- Execute skill workflows
- Handle step types (command, output, question, conditional)
- State management

**Deliverables:**
- [ ] SkillExecutor class
- [ ] Step execution logic
- [ ] Unit tests

---

**4.3 Implement Legacy Converter (M)**
- File: `src/site_nine/skills/legacy.py`
- Parse SKILL.md format
- Convert to SkillDefinition
- Preserve exact behavior

**Deliverables:**
- [ ] Legacy skill converter
- [ ] Backward compatibility tests
- [ ] Conversion tests

---

**4.4 Convert One Skill (S)**
- Convert session-start to skill.yaml
- Test in OpenCode
- Test in Cursor
- Document migration pattern

**Deliverables:**
- [ ] session-start skill.yaml
- [ ] Migration guide
- [ ] Tests

---

### Phase 4 Completion Criteria

- ✅ Skills refactoring complete
- ✅ Legacy SKILL.md supported
- ✅ New skill.yaml format working
- ✅ session-start converted
- ✅ Backward compatibility maintained

---

## Phase 5: Testing & Polish (XL)

**Goal**: Comprehensive testing, documentation, and release preparation.

### Testing Phase

**5.1 Unit Test Coverage (M)**
- Achieve 90%+ coverage
- Add missing tests
- Fix flaky tests

**Deliverables:**
- [ ] Test coverage report
- [ ] Additional tests
- [ ] All tests stable

---

**5.2 Integration Tests (M)**
- Test all CLI commands
- Test OpenCode workflows
- Test Cursor workflows
- Test error cases

**Deliverables:**
- [ ] Integration test suite
- [ ] Test report
- [ ] Bug fixes

---

**5.3 Backward Compatibility Tests (S)**
- Test existing .opencode/ projects
- Compare outputs with v1.x.x
- Validate zero regression

**Deliverables:**
- [ ] Backward compat test suite
- [ ] Comparison report
- [ ] Fixes if needed

### Documentation & Release

**5.4 API Documentation (S)**
- Generate API docs
- Document ToolAdapter protocol
- Document SkillDefinition format

**Deliverables:**
- [ ] API documentation
- [ ] Protocol docs
- [ ] Format specs

---

**5.5 User Documentation (M)**
- Migration guide (OpenCode → v2.0.0)
- Cursor setup guide
- Skill migration guide
- Changelog

**Deliverables:**
- [ ] Migration guide
- [ ] Cursor guide
- [ ] Skill guide
- [ ] Changelog

---

**5.6 Release Preparation (M)**
- Version bump to v2.0.0
- Release notes
- GitHub release
- Announcement

**Deliverables:**
- [ ] v2.0.0 release
- [ ] Release notes
- [ ] Announcement post
- [ ] Community communication

---

### Phase 5 Completion Criteria

- ✅ 90%+ test coverage
- ✅ All tests passing
- ✅ Documentation complete
- ✅ v2.0.0 released
- ✅ Community informed

---

## Risk Management

### High-Risk Items

| Risk | Mitigation | Contingency |
|------|------------|-------------|
| OpenCode regression | Comprehensive tests, manual validation | Hotfix release, revert if needed |
| MCP protocol issues | Follow spec, test against reference | Phase 2 extended, seek Cursor support |
| Performance degradation | Benchmark at each phase, optimize | Profile hot paths, consider caching |
| Skill conversion complexity | Start with simple skill, iterate | Keep legacy format longer |

### Dependencies

- **Cursor**: Requires Cursor MCP documentation and testing environment
- **MCP Spec**: Follow Model Context Protocol specification
- **Community**: Beta testers for Cursor integration

---

## Success Metrics

**Phase 1:**
- All existing tests pass (100%)
- Performance within 5% of baseline
- Zero user bug reports

**Phase 2:**
- CursorAdapter implements ToolAdapter (100%)
- At least one skill works in Cursor
- Demo completed successfully

**Phase 3:**
- ToolConfig normalizes OpenCode + Cursor configs
- Path resolution works for both tools

**Phase 4:**
- session-start skill works in new format
- Legacy skills still execute
- Zero conversion errors

**Phase 5:**
- 90%+ test coverage achieved
- Documentation published
- v2.0.0 released on schedule

---

## Communication Plan

**Weekly Updates:**
- Progress report to stakeholders
- Blockers and risks identified
- Demo of completed features

**Phase Completion:**
- Phase review meeting
- Demo to community
- Gather feedback

**Release:**
- Blog post announcement
- GitHub release notes
- Discord/community announcement
- User migration support

---

## Handoff to Engineer

**This roadmap is ready for Engineer implementation.**

**Next Steps:**
1. Engineer reviews this roadmap
2. Engineer creates detailed implementation tasks for Phase 1
3. Engineer begins implementation starting with Task 1.1
4. Architect available for questions and clarifications

**Engineer Tasks File:**
Create tasks in database:
```bash
s9 task create "ENG-H-XXXX" --title "Implement ToolAdapter protocol" --role Engineer --priority HIGH
s9 task create "ENG-H-XXXY" --title "Implement OpenCodeAdapter" --role Engineer --priority HIGH
# ... etc.
```

**Handoff Complete** ✅

---

**End of Implementation Roadmap**
