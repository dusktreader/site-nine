# ADR-005: Backward Compatibility Strategy

**Status:** Proposed  
**Date:** 2026-02-03  
**Deciders:** Ptah (Architect)  
**Related Tasks:** ARC-H-0030, ADM-H-0029  
**Related ADRs:** ADR-001 (Adapter), ADR-002 (Cursor), ADR-003 (Config), ADR-004 (Skills)

## Context

Site-nine has existing users with `.opencode/` projects that work today. As we introduce multi-tool support through the adapter pattern (ADR-001), unified configuration (ADR-003), and skills refactoring (ADR-004), we must ensure **zero breaking changes** for these users.

### Compatibility Requirements

**Must work without changes**:
1. Existing `.opencode/` directory structure
2. Existing `opencode.json` configuration files
3. Existing skills in `SKILL.md` format
4. Existing commands in `.opencode/commands/*.md`
5. All `s9` CLI commands and workflows
6. OpenCode-specific integrations (TUI renaming, skill invocation)

**User expectations**:
- **Silent transition**: Refactoring invisible to users
- **No manual migration**: Projects work automatically post-upgrade
- **Same behavior**: Commands produce identical results
- **No performance regression**: Same or better performance

### Risk Analysis

**High-risk changes**:
- ❌ **Path resolution**: Changing from `get_opencode_dir()` to `ToolRegistry.detect_tool()`
- ❌ **Configuration loading**: Adding ToolConfig layer
- ❌ **Skills execution**: Refactoring skill system
- ❌ **Adapter injection**: Core code using adapters instead of direct calls

**Medium-risk changes**:
- ⚠️ **Database schema**: If any schema changes needed
- ⚠️ **File formats**: If skill/session formats change

**Low-risk changes**:
- ✅ **Adding new code**: New adapters, renderers (don't affect existing)
- ✅ **Documentation**: Updates don't break functionality

## Decision

We will implement a **comprehensive backward compatibility strategy** with the following principles:

### Principle 1: OpenCode is the Default

**OpenCodeAdapter is the fallback for everything.**

When no tool can be detected or specified, site-nine defaults to OpenCode mode:

```python
class ToolRegistry:
    @classmethod
    def detect_tool(cls, start_path: Path | None = None) -> str:
        """Detect active tool, default to opencode"""
        # Check env override
        if tool := os.getenv("SITE_NINE_TOOL"):
            return tool.lower()
        
        # Check for tool directories
        current = (start_path or Path.cwd()).resolve()
        while True:
            if (current / ".cursor").exists():
                return "cursor"
            if (current / ".aider").exists():
                return "aider"
            if (current / ".opencode").exists():
                return "opencode"  # OpenCode found
            
            parent = current.parent
            if parent == current:
                # Reached root, no tool found
                return "opencode"  # DEFAULT to OpenCode
            current = parent
```

**Rationale**: Existing users have `.opencode/` directories. Detection finds them and uses OpenCodeAdapter. New code paths identical to old behavior.

### Principle 2: OpenCodeAdapter Wraps Existing Behavior

**No behavior changes, only abstraction.**

OpenCodeAdapter delegates to existing code:

```python
class OpenCodeAdapter(ToolAdapter):
    """Adapter for OpenCode - wraps existing implementation"""
    
    def __init__(self, config: ToolConfig):
        self.config = config
        # Use existing implementations
        from site_nine.core.paths import get_opencode_dir
        self.opencode_dir = get_opencode_dir()
    
    def get_skills_dir(self) -> Path:
        """Return skills directory"""
        # Delegates to existing path resolution
        return self.opencode_dir / "skills"
    
    def load_skill(self, name: str) -> SkillDefinition:
        """Load skill - supports both old and new formats"""
        skill_dir = self.get_skills_dir() / name
        
        # Try new format first
        yaml_path = skill_dir / "skill.yaml"
        if yaml_path.exists():
            return SkillDefinition.from_yaml(yaml_path)
        
        # Fall back to old SKILL.md format (backward compat)
        md_path = skill_dir / "SKILL.md"
        if md_path.exists():
            return self._convert_legacy_skill(md_path)
        
        raise FileNotFoundError(f"Skill {name} not found")
    
    def _convert_legacy_skill(self, md_path: Path) -> SkillDefinition:
        """Convert old SKILL.md format to SkillDefinition"""
        # Parse SKILL.md, extract steps from markdown
        # Return SkillDefinition that preserves exact behavior
        ...
```

**Rationale**: OpenCodeAdapter is a **thin wrapper**, not a rewrite. Existing code still executes, just accessed through adapter interface.

### Principle 3: Gradual Deprecation (Not Removal)

**Old formats supported indefinitely, with deprecation warnings.**

**Timeline**:
- **Phase 1 (Weeks 1-2)**: Adapters introduced, OpenCode works unchanged
- **Phase 2 (Weeks 3-4)**: New tools added (Cursor), OpenCode still default
- **Phase 3 (Weeks 5-6)**: New skill format introduced, old format still works
- **Phase 4 (Weeks 7-8)**: Deprecation warnings added (optional `--strict` flag)
- **Phase 5 (Month 3+)**: Old formats remain supported, docs show new format

**Example deprecation warning**:
```python
def _convert_legacy_skill(self, md_path: Path) -> SkillDefinition:
    """Convert old SKILL.md format to SkillDefinition"""
    if os.getenv("SITE_NINE_STRICT") == "1":
        logger.warning(
            f"Legacy skill format detected: {md_path}. "
            f"Consider migrating to skill.yaml format. "
            f"See: https://site-nine.dev/docs/migration-guide"
        )
    # Continue executing normally
    ...
```

**Rationale**: No forced migration. Users migrate on their schedule. Advanced users can opt-in to strict mode for future-proofing.

### Principle 4: Semantic Versioning

**Breaking changes trigger major version bump.**

- **v1.x.x**: Current site-nine (OpenCode-only)
- **v2.0.0**: Multi-tool support (backward compatible via adapters)
- **v2.x.x**: Bug fixes, new tools, feature additions (no breaking changes)
- **v3.0.0**: Only if we must remove legacy support (years from now)

**Rationale**: Users know what to expect from version numbers. v2.0.0 signals "major new features" but not "breaking changes" thanks to backward compatibility.

### Principle 5: Testing Matrix

**Comprehensive regression testing for OpenCode.**

**Test suite structure**:
```
tests/
├── integration/
│   ├── test_opencode_backward_compat.py  # Tests for existing OpenCode behavior
│   ├── test_cursor_integration.py         # New Cursor tests
│   └── test_multi_tool_projects.py        # Multi-tool scenarios
├── unit/
│   ├── test_adapters.py                   # Adapter pattern tests
│   ├── test_config_loaders.py             # Config loading tests
│   └── test_skill_executor.py             # Skill execution tests
└── fixtures/
    ├── opencode_project/                  # Real .opencode/ project
    ├── cursor_project/                    # Real .cursor/ project
    └── legacy_skills/                     # Old SKILL.md files
```

**Backward compatibility test**:
```python
def test_existing_opencode_project_unchanged():
    """Verify existing .opencode/ project works identically"""
    # Setup: Copy real .opencode/ project
    project_dir = setup_opencode_fixture()
    
    # Execute: Run s9 commands
    result = run_command("s9 dashboard", cwd=project_dir)
    
    # Assert: Same output as v1.x.x
    assert result.exit_code == 0
    assert "Available Tasks" in result.stdout
    # Compare with baseline output from v1.x.x

def test_legacy_skill_execution():
    """Verify old SKILL.md skills execute identically"""
    skill_dir = setup_legacy_skill("session-start")
    
    # Load through new system
    adapter = OpenCodeAdapter(config)
    skill = adapter.load_skill("session-start")
    
    # Execute and verify behavior matches old system
    result = await executor.execute(skill)
    assert result.steps_completed == expected_steps
```

**Rationale**: Automated tests catch regressions before users do.

## Implementation Strategy

### Phase 1: Foundation (Weeks 1-2) - Zero User Impact

**Goal**: Add abstractions without changing behavior.

**Changes**:
1. **Create adapter interfaces** (`src/site_nine/adapters/protocol.py`)
2. **Implement OpenCodeAdapter** (wraps existing code)
3. **Refactor core to use adapters** (with OpenCode as default)
4. **Add ToolRegistry** (auto-detects `.opencode/`, returns OpenCodeAdapter)

**Testing**:
- All existing tests must pass unchanged
- Add new adapter tests
- Manual testing of all s9 commands

**User impact**: **NONE** - OpenCodeAdapter executes existing code

### Phase 2: Cursor Support (Weeks 3-4) - Opt-In for New Users

**Goal**: Add Cursor support without affecting OpenCode users.

**Changes**:
1. **Implement CursorAdapter**
2. **Add Cursor config loader**
3. **Update ToolRegistry to detect `.cursor/`**
4. **Add `s9 init --tool cursor`**

**Testing**:
- OpenCode tests still pass (no changes)
- New Cursor tests added
- Multi-tool detection tests

**User impact**: **NONE for OpenCode users** - Cursor is new feature

### Phase 3: Skills Refactoring (Weeks 5-6) - Gradual Migration

**Goal**: New skill format available, old format still works.

**Changes**:
1. **Create SkillExecutor** (supports both formats)
2. **Implement legacy skill converter** (SKILL.md → SkillDefinition)
3. **Convert one skill to new format** (demonstrate pattern)
4. **Document migration guide**

**Testing**:
- Test legacy skill loading
- Test new skill format
- Test both formats work identically
- Regression tests for all existing skills

**User impact**: **MINIMAL** - Existing skills work unchanged, new format available for new skills

### Phase 4: Deprecation Warnings (Weeks 7-8) - Optional Strictness

**Goal**: Inform users about new patterns without breaking anything.

**Changes**:
1. **Add `SITE_NINE_STRICT` environment variable**
2. **Add optional deprecation warnings** (only when strict mode enabled)
3. **Update documentation to show new patterns**

**Testing**:
- Test warnings appear in strict mode
- Test warnings don't appear by default
- Test functionality unchanged in both modes

**User impact**: **NONE by default** - Warnings opt-in via env var

## Compatibility Guarantees

### What We Guarantee

✅ **Projects work**: Existing `.opencode/` projects function identically  
✅ **Commands work**: All `s9 *` commands produce same results  
✅ **Skills work**: All existing skills execute unchanged  
✅ **Configs work**: `opencode.json` files load correctly  
✅ **Performance**: Same or better (no performance regressions)  
✅ **Data integrity**: Database schema backward compatible  

### What We Don't Guarantee

❌ **Internal APIs**: `src/site_nine/` internals may change (not public API)  
❌ **Undocumented features**: Behaviors not in docs may change  
❌ **Private functions**: Functions starting with `_` may change  

### Breaking Changes (Require Major Version)

Only these changes justify v3.0.0 (years from now):
- Removing legacy SKILL.md support entirely
- Removing OpenCode adapter
- Incompatible database schema changes
- Removing deprecated CLI commands

## Rollback Plan

**If regressions discovered post-release:**

1. **Hotfix release**: Fix bug, release v2.0.1 immediately
2. **Regression test**: Add test to prevent recurrence
3. **Communication**: Inform users of fix via changelog, GitHub issue
4. **Git revert**: If unfixable quickly, revert to v1.x.x, re-plan

**Monitoring**:
- GitHub issues for bug reports
- User feedback in Discord/community
- CI/CD catches test failures before release

## Communication Plan

### Pre-Release (Before v2.0.0)

1. **Blog post**: "Coming Soon: Multi-Tool Support"
2. **Migration guide**: Step-by-step for interested users
3. **Beta testing**: Invite community to test release candidate
4. **Changelog**: Detailed v2.0.0 changes and guarantees

### Release (v2.0.0)

1. **GitHub release notes**: Highlight backward compatibility
2. **Announcement**: "v2.0.0 Released - Now Supports Cursor!"
3. **Upgrade guide**: "How to Upgrade (No Changes Required)"
4. **FAQ**: "Common Questions About v2.0.0"

### Post-Release

1. **Monitor issues**: Quick response to bug reports
2. **Hotfix cycle**: Fast fixes for any regressions
3. **User support**: Help users with questions
4. **Feedback loop**: Collect feedback for future improvements

## Consequences

### Positive

- ✅ **Zero user disruption**: Existing projects work unchanged
- ✅ **Confidence in upgrade**: Users trust v2.0.0 won't break things
- ✅ **Gradual migration**: Users adopt new features at their pace
- ✅ **Community trust**: Demonstrates commitment to stability
- ✅ **Long-term support**: Legacy formats supported indefinitely

### Negative

- ⚠️ **Maintenance burden**: Must maintain legacy format support
- ⚠️ **Code complexity**: Backward compatibility adds code paths
- ⚠️ **Testing overhead**: More test cases (old + new formats)

### Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Subtle behavior change in OpenCodeAdapter | High | Comprehensive regression tests, manual testing |
| Legacy skill converter produces incorrect SkillDefinition | High | Unit tests for converter, compare outputs |
| Performance regression from abstraction layer | Medium | Benchmark critical paths, optimize if needed |
| User confusion about old vs new formats | Low | Clear documentation, migration guide |

## Success Criteria

**v2.0.0 successful if**:
- ✅ Zero GitHub issues about broken .opencode/ projects
- ✅ All existing integration tests pass unchanged
- ✅ Performance benchmarks within 5% of v1.x.x
- ✅ Positive community feedback on upgrade smoothness
- ✅ Cursor users successfully onboard with new adapter

## Compliance

This ADR ensures:
- **ADR-001**: Adapter pattern doesn't break existing users
- **ADR-002**: Cursor support is additive, not disruptive
- **ADR-003**: ToolConfig maintains OpenCode path resolution
- **ADR-004**: Skills refactoring preserves legacy format
- **Project Goal**: Multi-tool support achieved without casualties

## References

- ADR-001: Adapter Pattern for Tool Abstraction
- ADR-002: Cursor MCP as First Multi-Tool Target
- ADR-003: Unified Configuration System Design
- ADR-004: Skills System Refactoring
- Semantic Versioning: https://semver.org/
- Current codebase: `src/site_nine/` (all modules)

## Notes

This ADR establishes **backward compatibility as a first-class requirement**, not an afterthought. Every design decision in ADR-001 through ADR-004 was made with backward compatibility in mind.

**Key Principle**: **Abstractions should be invisible to existing users.** OpenCodeAdapter, ToolConfig, and SkillExecutor are implemented as wrappers around existing code, not replacements.

**Testing Philosophy**: "If it worked in v1.x.x, it must work identically in v2.0.0."

**User Experience**: Upgrade from v1.x.x to v2.0.0 should be:
```bash
$ pip install --upgrade site-nine
$ s9 dashboard  # Works exactly as before
```

That's the gold standard.
