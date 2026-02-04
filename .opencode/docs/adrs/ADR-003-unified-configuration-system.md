# ADR-003: Unified Configuration System Design

**Status:** Rejected  
**Date:** 2026-02-03  
**Deciders:** Ptah (Architect), Al-Lat (Administrator)  
**Rejection Date:** 2026-02-03  
**Rejection Reason:** Premature design - insufficient knowledge of target tools  
**Related Tasks:** ARC-H-0030, ADM-H-0029  
**Related ADRs:** ADR-001 (Adapter Pattern), ADR-002 (Target Tool Prioritization)

## Rejection Summary

This ADR attempted to design a unified configuration system before implementing any adapters for the target tools 
(Copilot CLI, Crush, Claude Code). Upon review, it became clear that:

1. **Insufficient knowledge**: We don't know how each tool handles configuration
2. **Premature abstraction**: Designing abstractions before understanding concrete implementations is risky
3. **YAGNI violation**: We may not need unified configuration at all - each adapter might handle its own config

## Decision

**REJECTED** - Defer configuration system design until after implementing first adapter (Copilot CLI per ADR-002).

**Rationale**: Learn what's actually needed from real implementation experience rather than speculating. The adapter 
pattern (ADR-001) doesn't require unified configuration - each adapter can manage configuration however makes sense 
for that tool.

## Next Steps

1. Implement Copilot CLI adapter (ADR-002) without unified config system
2. Each adapter handles its own configuration as appropriate for that tool
3. If common patterns emerge across 2-3 adapters, revisit configuration abstraction
4. Don't build abstractions until they're demonstrably needed

## Original Context (For Historical Reference)

This ADR originally proposed a unified configuration system, but was rejected as premature. The content below is 
preserved for historical context only.

---

Site-nine currently uses `.opencode/` as a hardcoded directory structure and `opencode.json` as its configuration file.
To support multiple tools, we need a configuration system that:

1. Works with different tool directory structures (tool-specific directories for Copilot CLI, Crush, Claude Code, etc.)
2. Supports tool-specific configuration formats while maintaining a unified internal model
3. Enables auto-detection of which tool is active in a project
4. Maintains backward compatibility with existing `.opencode/` projects

### Current State

**Hardcoded assumptions:**
- `find_opencode_dir()` only looks for `.opencode/`
- Configuration loaded from `opencode.json`
- Paths hardcoded: `.opencode/data/project.db`, `.opencode/work/sessions/`, etc.
- No tool detection mechanism

**Configuration structure:**
```json
{
  "$schema": "https://opencode.ai/config.json",
  "skills": { "paths": [".opencode/skills"] },
  "command": {  "summon": { "template": ".opencode/commands/summon.md", ... } }
}
```

### Requirements

1. **Tool-agnostic internals**: Core site-nine code should work with any tool's structure
2. **Tool detection**: Auto-detect active tool (OpenCode, Copilot CLI, Crush, Claude Code, etc.)
3. **Path abstraction**: Site-nine manages its own data/work directories, adapts to tool-specific locations as feasible
4. **Backward compatibility**: Existing `.opencode/` projects work without changes
5. **Configuration normalization**: Different tool config formats map to unified internal model

**Note**: Full path mapping across all tools may not be feasible. We'll learn what's possible as we implement each
adapter.

## Decision

We will implement a **Unified Configuration System** with **tool detection** and **path abstraction**.

### Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│            site-nine Core Code                      │
│   Uses generic ToolConfig & PathResolver            │
└──────────────────┬──────────────────────────────────┘
                   │
                   │ requests config/paths
                   ▼
        ┌──────────────────────┐
        │   ToolRegistry        │
        │  (Auto-Detection)     │
        └──────────┬────────────┘
                   │ selects
         ┌─────────┴──────────┬──────────────┐
         │                    │              │
┌────────▼────────┐  ┌───────▼────────┐  ┌─▼──────────┐
│  OpenCodeConfig │  │  CopilotConfig │  │ClaudeConfig│
│   Loader        │  │   Loader       │  │  Loader    │
└────────┬────────┘  └───────┬────────┘  └─┬──────────┘
         │ loads              │ loads       │ loads
         ▼                    ▼             ▼
  ┌────────────┐      ┌──────────────┐   ┌────────────┐
  │ opencode.  │      │ copilot.json │   │claude.json │
  │ json       │      │              │   │            │
  └────────────┘      └──────────────┘   └────────────┘
         │                    │             │
         │ normalizes         │ normalizes  │ normalizes
         ▼                    ▼             ▼
        ┌──────────────────────┐
        │    ToolConfig         │
        │  (Unified Model)      │
        └──────────┬────────────┘
                   │
                   │ provides
                   ▼
        ┌──────────────────────┐
        │   PathResolver        │
        │ ({tool}/work/sessions)│
        └───────────────────────┘
```

### Key Components

#### 1. ToolConfig (Unified Model)

**File**: `src/site_nine/core/tool_config.py`

```python
@dataclass
class ToolConfig:
    """Unified configuration model for all tools"""

    # Tool identification
    tool_name: str  # "opencode", "copilot", "crush", "claude_code"
    tool_dir: Path  # Tool-specific directory

    # Project metadata
    project_name: str
    project_type: str = "python"

    # Directory structure
    data_dir: Path        # {tool}/data/
    docs_dir: Path        # {tool}/docs/
    work_dir: Path        # {tool}/work/
    skills_dir: Path      # {tool}/skills/
    commands_dir: Path    # {tool}/commands/

    # Skills configuration
    skills_paths: list[Path]

    # Commands configuration
    commands: dict[str, CommandConfig]

    # Features
    features: FeaturesConfig
    agent_roles: list[AgentRoleConfig]

    @classmethod
    def from_tool_config(cls, tool_name: str, config_file: Path) -> "ToolConfig":
        """Load tool-specific config and normalize to ToolConfig"""
        loader = get_config_loader(tool_name)
        return loader.load(config_file)
```

#### 2. ToolRegistry (Auto-Detection)

**File**: `src/site_nine/adapters/registry.py`

```python
class ToolRegistry:
    """Detects active tool and provides appropriate adapter"""

    TOOL_MARKERS = {
        "opencode": (".opencode", "opencode.json"),
        "copilot": (".copilot", "copilot.json"),  # Example - actual path TBD
        "crush": (".crush", "crush.json"),  # Example - actual path TBD
        "claude_code": (".claude", "claude.json"),  # Example - actual path TBD
    }

    @classmethod
    def detect_tool(cls, start_path: Path | None = None) -> str | None:
        """
        Auto-detect which tool is active in project.

        Search order:
        1. SITE_NINE_TOOL env var (explicit override)
        2. Tool-specific directories (precedence TBD based on implementation)
        3. .opencode/ directory (OpenCode - default fallback)

        Returns:
            Tool name ("opencode", "copilot", "crush", "claude_code") or None if not found
        """
        # Check environment override
        if tool := os.getenv("SITE_NINE_TOOL"):
            return tool.lower()

        # Walk up directory tree looking for tool markers
        current = (start_path or Path.cwd()).resolve()
        while True:
            # Check each tool in priority order (actual order TBD)
            for tool_name in ["copilot", "crush", "claude_code", "opencode"]:
                tool_dir, config_file = cls.TOOL_MARKERS[tool_name]
                if (current / tool_dir).exists():
                    return tool_name

            # Move up directory tree
            parent = current.parent
            if parent == current:
                return None
            current = parent

    @classmethod
    def get_tool_config(cls) -> ToolConfig:
        """Get active tool configuration"""
        tool_name = cls.detect_tool()
        if not tool_name:
            raise FileNotFoundError(
                "No site-nine tool configuration found. "
                "Run 's9 init' or configure your tool directory."
            )

        tool_dir = find_tool_dir(tool_name)
        config_file = tool_dir / get_config_filename(tool_name)

        return ToolConfig.from_tool_config(tool_name, config_file)
```

#### 3. PathResolver (Path Abstraction)

**File**: `src/site_nine/core/paths.py` (refactored)

```python
class PathResolver:
    """Resolves generic paths to tool-specific paths"""

    def __init__(self, config: ToolConfig):
        self.config = config
        self.tool_dir = config.tool_dir

    def get_data_path(self) -> Path:
        """Get data directory path"""
        return self.tool_dir / "data"

    def get_database_path(self) -> Path:
        """Get database file path"""
        return self.get_data_path() / "project.db"

    def get_sessions_path(self) -> Path:
        """Get sessions directory path"""
        return self.tool_dir / "work" / "sessions"

    def get_tasks_path(self) -> Path:
        """Get tasks directory path"""
        return self.tool_dir / "work" / "tasks"

    def resolve(self, generic_path: str) -> Path:
        """
        Resolve generic path template to tool-specific path.

        Examples:
            "{tool}/data/project.db" -> ".opencode/data/project.db"
            "{tool}/work/sessions/" -> ".copilot/work/sessions/"
        """
        return Path(generic_path.replace("{tool}", str(self.tool_dir)))
```

#### 4. Config Loaders (Tool-Specific)

**File**: `src/site_nine/adapters/config_loaders.py`

```python
class ConfigLoader(Protocol):
    """Protocol for tool-specific config loaders"""

    def load(self, config_file: Path) -> ToolConfig:
        """Load tool-specific config and normalize to ToolConfig"""
        ...

class OpenCodeConfigLoader:
    """Loads opencode.json and converts to ToolConfig"""

    def load(self, config_file: Path) -> ToolConfig:
        with open(config_file) as f:
            raw = json.load(f)

        tool_dir = config_file.parent
        return ToolConfig(
            tool_name="opencode",
            tool_dir=tool_dir,
            project_name=tool_dir.parent.name,
            data_dir=tool_dir / "data",
            docs_dir=tool_dir / "docs",
            work_dir=tool_dir / "work",
            skills_dir=tool_dir / "skills",
            commands_dir=tool_dir / "commands",
            skills_paths=[Path(p) for p in raw.get("skills", {}).get("paths", [])],
            commands={name: CommandConfig.from_dict(cmd) for name, cmd in raw.get("command", {}).items()},
            # ... normalize other fields
        )

class CopilotConfigLoader:
    """Loads copilot.json (or appropriate config format) and converts to ToolConfig"""

    def load(self, config_file: Path) -> ToolConfig:
        with open(config_file) as f:
            raw = json.load(f)  # Format TBD based on actual Copilot CLI config

        # Map Copilot CLI config format to ToolConfig
        tool_dir = config_file.parent
        return ToolConfig(
            tool_name="copilot",
            tool_dir=tool_dir,
            # ... map Copilot-specific format (TBD during implementation)
        )

# Similar loaders for Crush and Claude Code will be implemented as we learn their config formats
```

### Configuration File Strategy

#### Option A: Tool-Specific Files (CHOSEN)

**Approach**: Each tool has its own config file format.
- OpenCode: `opencode.json`
- Copilot CLI: Config format TBD (research during implementation)
- Crush: Config format TBD (research during implementation)
- Claude Code: Config format TBD (research during implementation)

**Pros**:
- ✅ Respects each tool's conventions
- ✅ Works with existing tool ecosystems
- ✅ Tool-specific features supported
- ✅ Incidentally handles multi-tool scenarios if they arise

**Cons**:
- ⚠️ Need config loaders for each tool
- ⚠️ Potential duplication if projects use multiple tools (not a priority concern)

#### Option B: Unified `.s9.json` File (REJECTED)

**Approach**: Single `.s9.json` file for all tools.

**Pros**:
- ✅ Single source of truth
- ✅ No duplication

**Cons**:
- ❌ Doesn't integrate with tool ecosystems
- ❌ Users must learn new config format
- ❌ Conflicts with tool-native configs

**Rejected because**: Introduces friction, doesn't leverage existing tool configurations.

## Alternatives Considered

### Alternative 1: Environment Variables Only

**Approach**: Use environment variables to specify tool and paths.

**Pros**:
- Simple implementation
- No config file parsing needed

**Cons**:
- User-hostile (must set env vars every time)
- No per-project configuration
- Hard to share projects

**Rejected because**: Poor user experience.

### Alternative 2: Symlinks to Unified Structure

**Approach**: Each tool creates symlinks to a shared `.s9/` structure.

**Pros**:
- Single directory structure
- No path mapping needed

**Cons**:
- Symlinks fragile (Windows issues, git issues)
- Confusing for users
- Doesn't work with tool-native configs
- Breaks tool integrations

**Rejected because**: Adds complexity without benefits.

### Alternative 3: Hard-Fork Per Tool

**Approach**: Separate site-nine forks for each tool.

**Pros**:
- No abstraction needed
- Tool-optimized

**Cons**:
- Maintenance nightmare
- Feature divergence
- No code reuse

**Rejected because**: Defeats purpose of universal tool support; violates DRY principle.

## Implementation Plan

### Phase 1: Core Abstractions (Week 1-2)

1. **Create ToolConfig model**
   - Unified configuration dataclass
   - Config loader protocol
   - OpenCodeConfigLoader (wraps existing behavior)

2. **Create ToolRegistry**
   - Tool detection logic
   - Config loading
   - Adapter selection

3. **Create PathResolver**
   - Path abstraction methods
   - Template-based path resolution

4. **Refactor core to use abstractions**
   - Replace `get_opencode_dir()` with `registry.get_tool_dir()`
   - Replace hardcoded paths with `path_resolver.get_*_path()`
   - Update all CLI commands

### Phase 2: Tool-Specific Configuration Loaders (Per Tool Implementation)

**Note**: This phase happens alongside each tool adapter implementation (see ADR-002)

1. **Create Tool-Specific ConfigLoaders**
   - Research tool's config format
   - Parse tool-specific config file
   - Map to ToolConfig

2. **Tool Directory Structure**
   - Generate tool-specific directory structure in `s9 init --tool <toolname>`
   - Create tool-specific config template

3. **Testing**
   - Test tool config loading
   - Validate path resolution for that tool

### Phase 3: Multi-Tool Support (After Multiple Adapters Complete)

1. **Tool Priority System**
   - Handle projects with multiple tool directories
   - User can override via `SITE_NINE_TOOL` env var
   - Document precedence order

2. **Config Synchronization**
   - Optional: sync configs across tools
   - Detect config drift

## Consequences

### Positive

- ✅ **Tool-agnostic core**: Core code doesn't know about specific tools
- ✅ **Auto-detection**: Users don't specify tool explicitly
- ✅ **Multi-tool ready**: Projects can use multiple tools
- ✅ **Extensible**: Easy to add new tools
- ✅ **Backward compatible**: `.opencode/` projects work unchanged

### Negative

- ⚠️ **Added abstraction layer**: More indirection in code
- ⚠️ **Config mapping complexity**: Must normalize different formats
- ⚠️ **Testing complexity**: Test each config loader independently

### Risks & Mitigation

| Risk                                        | Mitigation                                  |
|---------------------------------------------|---------------------------------------------|
| Tool detection ambiguous if multiple tool directories exist | Clear precedence order, env var override for edge cases |
| Config format changes in tools              | Version loaders, compatibility matrix       |
| Path resolution bugs                        | Comprehensive path resolution tests         |
| Performance overhead from abstraction       | Lazy loading, caching                       |

## Compliance

This decision supports:
- **ADR-001**: Enables adapter pattern with clean configuration abstraction
- **ADR-002**: Provides foundation for multi-tool support (Copilot CLI, Crush, Claude Code)
- **Project Goal**: Multi-tool support with unified internal model

## References

- ADR-001: Adapter Pattern
- ADR-002: Target Tool Prioritization
- Current implementation: `src/site_nine/core/paths.py`, `src/site_nine/core/config.py`
- OpenCode config: `.opencode/opencode.json`

## Notes

This ADR establishes the **configuration abstraction** layer. It's designed to work with ADR-001's adapter pattern -
adapters use ToolConfig to access tool-specific paths and settings in a normalized way.

**Key Principle**: Configuration system knows about different tools (detection, loading). Core business logic only sees
ToolConfig (tool-agnostic).

Next ADRs:
- ADR-004: Skills refactoring approach
- ADR-005: Backward compatibility strategy
