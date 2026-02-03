# ADR-003: Unified Configuration System Design

**Status:** Proposed  
**Date:** 2026-02-03  
**Deciders:** Ptah (Architect)  
**Related Tasks:** ARC-H-0030, ADM-H-0029  
**Related ADRs:** ADR-001 (Adapter Pattern), ADR-002 (Cursor MCP Target)

## Context

Site-nine currently uses `.opencode/` as a hardcoded directory structure and `opencode.json` as its configuration file. To support multiple tools, we need a configuration system that:

1. Works with different tool directory structures (`.opencode/`, `.cursor/`, `.aider/`, etc.)
2. Supports tool-specific configuration formats while maintaining a unified internal model
3. Enables auto-detection of which tool is active in a project
4. Allows projects to use multiple tools simultaneously (multi-tool projects)
5. Maintains backward compatibility with existing `.opencode/` projects

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
2. **Tool detection**: Auto-detect active tool (OpenCode, Cursor, Aider, etc.)
3. **Path mapping**: Map generic paths to tool-specific paths (e.g., `{tool}/work/sessions/`)
4. **Multi-tool support**: Projects can have `.opencode/` AND `.cursor/` simultaneously
5. **Backward compatibility**: Existing `.opencode/` projects work without changes
6. **Configuration normalization**: Different tool config formats map to unified internal model

## Decision

We will implement a **Unified Configuration System** with **tool detection** and **path abstraction**.

### Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│            site-nine Core Code                       │
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
         ┌─────────┴──────────┐
         │                    │
┌────────▼────────┐  ┌───────▼────────┐
│  OpenCodeConfig │  │  CursorConfig  │
│   Loader        │  │   Loader       │
└────────┬────────┘  └───────┬────────┘
         │ loads              │ loads
         ▼                    ▼
  ┌────────────┐      ┌──────────────┐
  │ opencode.  │      │ cursor.json  │
  │ json       │      │              │
  └────────────┘      └──────────────┘
         │                    │
         │ normalizes         │ normalizes
         ▼                    ▼
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
    tool_name: str  # "opencode", "cursor", "aider"
    tool_dir: Path  # .opencode/, .cursor/, .aider/
    
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
        "cursor": (".cursor", "cursor.json"),
        "aider": (".aider", ".aider.conf.yml"),
    }
    
    @classmethod
    def detect_tool(cls, start_path: Path | None = None) -> str | None:
        """
        Auto-detect which tool is active in project.
        
        Search order:
        1. SITE_NINE_TOOL env var (explicit override)
        2. .cursor/ directory (Cursor MCP)
        3. .aider/ directory (Aider)
        4. .opencode/ directory (OpenCode - default)
        
        Returns:
            Tool name ("opencode", "cursor", "aider") or None if not found
        """
        # Check environment override
        if tool := os.getenv("SITE_NINE_TOOL"):
            return tool.lower()
        
        # Walk up directory tree looking for tool markers
        current = (start_path or Path.cwd()).resolve()
        while True:
            # Check each tool in priority order
            for tool_name in ["cursor", "aider", "opencode"]:
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
            "{tool}/work/sessions/" -> ".cursor/work/sessions/"
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

class CursorConfigLoader:
    """Loads cursor.json and converts to ToolConfig"""
    
    def load(self, config_file: Path) -> ToolConfig:
        with open(config_file) as f:
            raw = json.load(f)
        
        # Map Cursor MCP config format to ToolConfig
        tool_dir = config_file.parent
        return ToolConfig(
            tool_name="cursor",
            tool_dir=tool_dir,
            # ... map Cursor-specific format
        )
```

### Configuration File Strategy

#### Option A: Tool-Specific Files (CHOSEN)

**Approach**: Each tool has its own config file format.
- OpenCode: `opencode.json`
- Cursor: `cursor.json`
- Aider: `.aider.conf.yml`

**Pros**:
- ✅ Respects each tool's conventions
- ✅ Works with existing tool ecosystems
- ✅ No conflicts in multi-tool projects
- ✅ Tool-specific features supported

**Cons**:
- ⚠️ Need config loaders for each tool
- ⚠️ Duplication in multi-tool projects

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
- Doesn't support multi-tool projects

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

**Rejected because**: Defeats purpose of multi-tool support.

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

### Phase 2: Cursor Configuration (Week 3)

1. **Create CursorConfigLoader**
   - Parse `cursor.json`
   - Map to ToolConfig

2. **Cursor Directory Structure**
   - Generate `.cursor/` structure in `s9 init --tool cursor`
   - Create `cursor.json` template

3. **Testing**
   - Test Cursor config loading
   - Validate path resolution

### Phase 3: Multi-Tool Support (Week 5)

1. **Tool Priority System**
   - Handle projects with both `.opencode/` and `.cursor/`
   - User can override via `SITE_NINE_TOOL` env var

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

| Risk | Mitigation |
|------|------------|
| Tool detection ambiguous in multi-tool projects | Clear precedence order, env var override |
| Config format changes in tools | Version loaders, compatibility matrix |
| Path resolution bugs | Comprehensive path resolution tests |
| Performance overhead from abstraction | Lazy loading, caching |

## Compliance

This decision supports:
- **ADR-001**: Enables adapter pattern with clean configuration abstraction
- **ADR-002**: Provides foundation for Cursor MCP support
- **Project Goal**: Multi-tool support with unified internal model

## References

- ADR-001: Adapter Pattern
- ADR-002: Cursor MCP First Target
- Current implementation: `src/site_nine/core/paths.py`, `src/site_nine/core/config.py`
- OpenCode config: `.opencode/opencode.json`

## Notes

This ADR establishes the **configuration abstraction** layer. It's designed to work with ADR-001's adapter pattern - adapters use ToolConfig to access tool-specific paths and settings in a normalized way.

**Key Principle**: Configuration system knows about different tools (detection, loading). Core business logic only sees ToolConfig (tool-agnostic).

Next ADRs:
- ADR-004: Skills refactoring approach
- ADR-005: Backward compatibility strategy
