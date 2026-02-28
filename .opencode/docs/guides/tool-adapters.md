# Tool Adapters Guide

Guide to the tool adapter system that enables site-nine to work with multiple AI coding tools.


## Overview

**Status:** Proposed (not yet implemented)

The tool adapter system will enable site-nine to work with multiple AI coding tools (OpenCode, Cursor, Aider, etc.) 
through a unified interface. Instead of being tightly coupled to OpenCode, site-nine will use adapters to abstract 
tool-specific functionality.


## What are adapters?

Adapters are implementations of a common interface that translate between site-nine's tool-agnostic core and specific 
AI coding tool APIs. They follow the **Adapter Pattern** from software design patterns.

**Analogy:** Like power adapters for international travel - they let your device work with different outlets while 
the device stays the same.


### Why adapters exist

Site-nine was originally built for OpenCode. To support other tools without duplicating code or creating 
tool-specific forks, we use adapters to:

- **Abstract tool differences** - Core code doesn't know about specific tools
- **Enable easy extension** - New tools added by implementing adapter interface
- **Preserve compatibility** - OpenCode users see no breaking changes
- **Maintain single codebase** - One site-nine works with all tools


## How adapters work

### Architecture overview

```
┌──────────────────────────────────────────────────────┐
│                  site-nine Core                      │
│  (CLI, Tasks, Database, Agents)                      │
└──────────────────┬───────────────────────────────────┘
                   │
                   │ uses ToolAdapter interface
                   ▼
        ┌──────────────────────┐
        │   ToolAdapter API    │  ◄── Protocol (Interface)
        └──────────────────────┘
                   △
                   │ implements
         ┌─────────┴──────────┬─────────────┐
         │                    │             │
┌────────▼────────┐  ┌───────▼────────┐  ┌▼──────────┐
│ OpenCodeAdapter │  │ CursorAdapter  │  │ AiderAdapter│
│                 │  │   (Planned)    │  │  (Planned)  │
└─────────────────┘  └────────────────┘  └──────────────┘
```


### ToolAdapter protocol

All adapters implement the `ToolAdapter` protocol, which defines standard methods for:

**Configuration:**
- Get tool name and version
- Load tool configuration files
- Provide unified configuration model

**Path resolution:**
- Get tool directory (.opencode/, .cursor/, .aider/)
- Get subdirectories (data, docs, work, skills, commands)
- Get database path

**Skills and commands:**
- Load skill definitions
- List available skills
- Get skill renderer for tool's output format
- Load command definitions

**Session management (optional):**
- Check if tool supports session API
- Rename sessions (if supported)
- List active sessions (if supported)

**Project initialization:**
- Create tool-specific directory structure
- Generate configuration files
- Set up templates

**See:** `.opencode/docs/guides/architecture.md` for complete protocol specification


### Tool detection

The `ToolRegistry` auto-detects which tool is active using this cascade:

1. **Environment variable** - Check `S9_TOOL` override (e.g., `S9_TOOL=cursor`)
2. **Directory markers** - Look for `.opencode/`, `.cursor/`, `.aider/` directories
3. **Config files** - Check for tool-specific config files
4. **Default fallback** - Use OpenCodeAdapter for backward compatibility

**Example detection logic:**

```python
def detect_tool() -> ToolAdapter:
    # Check environment override
    if tool_env := os.getenv("S9_TOOL"):
        return load_adapter(tool_env)
    
    # Check for tool directories
    if (Path.cwd() / ".opencode").exists():
        return OpenCodeAdapter()
    elif (Path.cwd() / ".cursor").exists():
        return CursorAdapter()
    elif (Path.cwd() / ".aider").exists():
        return AiderAdapter()
    
    # Default to OpenCode
    return OpenCodeAdapter()
```


## Using the adapter system

**Note:** This section describes planned behavior. Implementation not yet complete.


### For users

**Normal usage - automatic detection:**

Most users won't need to think about adapters. Site-nine auto-detects your tool:

```bash
# Works automatically if you have .opencode/ directory
s9 task list

# Works automatically if you have .cursor/ directory
s9 task list

# Works automatically if you have .aider/ directory
s9 task list
```


**Explicit tool selection:**

Override detection with environment variable:

```bash
# Force OpenCode adapter
S9_TOOL=opencode s9 task list

# Force Cursor adapter
S9_TOOL=cursor s9 task list

# Force Aider adapter
S9_TOOL=aider s9 task list
```


**Project initialization:**

Initialize project for specific tool:

```bash
# Initialize for OpenCode
s9 init --tool opencode

# Initialize for Cursor
s9 init --tool cursor

# Initialize for Aider
s9 init --tool aider
```


### For developers

**Using adapters in code:**

```python
from site_nine.adapters.registry import get_adapter

# Get adapter for current project
adapter = get_adapter()

# Access tool-agnostic configuration
config = adapter.config
print(f"Tool: {adapter.tool_name}")
print(f"Database: {adapter.get_database_path()}")

# Load skills
skill = adapter.load_skill("session-start")

# Get paths
data_dir = adapter.get_data_dir()
skills_dir = adapter.get_skills_dir()
```


**Implementing a new adapter:**

1. Create adapter class in `src/site_nine/adapters/<tool_name>.py`
2. Implement `ToolAdapter` protocol methods
3. Register in `ToolRegistry`
4. Test with tool's API
5. Document tool-specific setup

**Example adapter skeleton:**

```python
from pathlib import Path
from site_nine.adapters.protocol import ToolAdapter
from site_nine.core.tool_config import ToolConfig

class MyToolAdapter:
    """Adapter for MyTool integration"""
    
    def __init__(self, tool_dir: Path | None = None):
        self._tool_dir = tool_dir or self._detect_tool_dir()
        self._config: ToolConfig | None = None
    
    @property
    def tool_name(self) -> str:
        return "mytool"
    
    @property
    def tool_version(self) -> str:
        return "1.0.0"
    
    def get_tool_dir(self) -> Path:
        return self._tool_dir
    
    def load_config(self) -> ToolConfig:
        # Load mytool.json and convert to ToolConfig
        config_path = self._tool_dir / "mytool.json"
        # ... parse and return ToolConfig
    
    # Implement remaining protocol methods...
```


## Adapter capabilities

Different tools have different capabilities. Adapters expose capabilities via `get_capabilities()`:


### OpenCodeAdapter capabilities

- `session-api` - Supports programmatic session management (TUI API)
- `tui-integration` - Has terminal UI integration
- `skills-markdown` - Skills defined in markdown format
- `commands-markdown` - Commands defined in markdown templates


### CursorAdapter capabilities (planned)

- `mcp-server` - Model Context Protocol server integration
- `skills-typescript` - Skills as TypeScript MCP tools
- `file-watching` - Real-time file change detection


### AiderAdapter capabilities (planned)

- `cli-only` - No GUI/TUI, command-line only
- `git-integration` - Deep git commit automation
- `ai-chat` - Direct AI chat interface


### Checking capabilities

```python
adapter = get_adapter()

if "session-api" in adapter.get_capabilities():
    adapter.rename_session(session_id, new_title)
else:
    print("Tool doesn't support session API")
```


## Configuration mapping

Each tool has its own configuration format. Adapters map tool configs to unified `ToolConfig` model:


### OpenCode → ToolConfig

**Source:** `.opencode/opencode.json`

```json
{
  "project": {
    "name": "site-nine",
    "type": "python"
  },
  "skills": {
    "paths": [".opencode/skills"]
  },
  "command": {
    "summon": {
      "template": ".opencode/commands/summon.md"
    }
  }
}
```

**Mapped to ToolConfig:**

```python
ToolConfig(
    tool_name="opencode",
    tool_dir=Path(".opencode"),
    project_name="site-nine",
    project_type="python",
    skills_dir=Path(".opencode/skills"),
    commands_dir=Path(".opencode/commands"),
    data_dir=Path(".opencode/data"),
    # ...
)
```


### Cursor → ToolConfig (planned)

**Source:** `.cursor/cursor.json` (MCP format)

```json
{
  "mcpServers": {
    "site-nine": {
      "command": "uv",
      "args": ["run", "site-nine-mcp"]
    }
  }
}
```

**Mapped to ToolConfig:**

```python
ToolConfig(
    tool_name="cursor",
    tool_dir=Path(".cursor"),
    project_name="site-nine",
    skills_dir=Path(".cursor/mcp/servers"),
    # ...
)
```


## Environment variable overrides

**Planned feature** (not yet implemented):

Override auto-detection with environment variables:


### S9_TOOL

Force specific tool adapter:

```bash
export S9_TOOL=cursor
s9 task list  # Uses CursorAdapter regardless of directory markers
```


### S9_TOOL_DIR

Override tool directory location:

```bash
export S9_TOOL_DIR=/custom/path/.opencode
s9 task list  # Uses specified directory instead of searching
```


### S9_CONFIG

Override config file location:

```bash
export S9_CONFIG=/custom/opencode.json
s9 init  # Uses specified config
```


## Tool-specific features

Some tools have unique features not in the common protocol. Use `execute_tool_specific()` for these:


### OpenCode-specific: TUI operations

```python
adapter = get_adapter()

if adapter.tool_name == "opencode":
    result = adapter.execute_tool_specific(
        "tui-integration",
        operation="list-sessions"
    )
```


### Cursor-specific: MCP server commands (planned)

```python
adapter = get_adapter()

if adapter.tool_name == "cursor":
    result = adapter.execute_tool_specific(
        "mcp-command",
        server="site-nine",
        command="task.list"
    )
```


## Testing adapters

**Challenge:** Cannot run integration tests (can't run coding agent from within another agent).

**Solution:** Manual testing protocol with comprehensive smoke test checklist:


### Adapter smoke tests

For each new adapter:

1. **Detection** - Verify adapter auto-detected in project
2. **Configuration** - Verify config loads and maps correctly
3. **Paths** - Verify all directory paths resolve correctly
4. **Database** - Verify database operations work (create task, list tasks)
5. **Skills** - Verify skills load and execute
6. **Commands** - Verify commands load
7. **Sessions** (if supported) - Verify session operations
8. **Initialization** - Verify `s9 init` creates correct structure


### Testing with different tools

Real-world validation with each tool before release:

**OpenCode:**
1. Run `s9 init --tool opencode` in test project
2. Verify `.opencode/` structure created
3. Run `s9 task create "Test task"`
4. Run `s9 task list` and verify display
5. Test skills via OpenCode TUI

**Cursor (when implemented):**
1. Run `s9 init --tool cursor` in test project
2. Verify `.cursor/` structure created
3. Test MCP server integration
4. Verify task management via Cursor UI

**Aider (when implemented):**
1. Run `s9 init --tool aider` in test project
2. Verify `.aider/` structure created
3. Test CLI-only workflow
4. Verify git integration features


## Migration guide

**For OpenCode users:** No action required. The OpenCodeAdapter wraps existing functionality with zero breaking 
changes.

**For new tool users:** Initialize your project with the specific tool:

```bash
# For Cursor users
cd my-project
s9 init --tool cursor

# For Aider users
cd my-project
s9 init --tool aider
```


## Troubleshooting

### Wrong tool detected

**Problem:** Site-nine using wrong adapter

**Solution:** Override with environment variable:

```bash
S9_TOOL=opencode s9 task list
```


### Tool directory not found

**Problem:** `ToolAdapter` can't find tool directory

**Solution 1:** Ensure you're in project root (parent of `.opencode/`, `.cursor/`, etc.)

**Solution 2:** Set explicit path:

```bash
export S9_TOOL_DIR=/path/to/.opencode
```


### Adapter not found

**Problem:** `Unknown tool: mytool`

**Solution:** Check tool name spelling and ensure adapter is registered in `ToolRegistry`


### Configuration load error

**Problem:** `ValueError: Invalid config format`

**Solution:** Validate tool config file format:

```bash
# For OpenCode
python -m json.tool .opencode/opencode.json

# For Cursor
python -m json.tool .cursor/cursor.json
```


### Session API not supported

**Problem:** `Tool doesn't support session API`

**Solution:** This is expected for CLI-only tools (e.g., Aider). Some features like session renaming won't work.


## Implementation status

**Current state (as of 2026-02-03):**

- ✅ **Design complete** - ADR-001 and Technical Design Document
- ✅ **Documentation complete** - This guide and architecture.md
- ⏳ **Implementation pending** - Adapter code not yet written
- ⏳ **Testing pending** - Smoke tests not yet run

**Next steps:**

1. Implement ToolAdapter protocol (`src/site_nine/adapters/protocol.py`)
2. Implement OpenCodeAdapter (`src/site_nine/adapters/opencode.py`)
3. Implement ToolRegistry (`src/site_nine/adapters/registry.py`)
4. Update core code to use adapters
5. Implement CursorAdapter
6. Implement AiderAdapter
7. Run smoke tests for each adapter


## References

### Documentation

- **Architecture Guide** - `.opencode/docs/guides/architecture.md`
- **ADR-001** - Adapter Pattern for Tool Abstraction
- **Technical Design Document** - Complete adapter specification

### Code (planned locations)

- `src/site_nine/adapters/protocol.py` - ToolAdapter protocol
- `src/site_nine/adapters/registry.py` - ToolRegistry auto-detection
- `src/site_nine/adapters/opencode.py` - OpenCodeAdapter implementation
- `src/site_nine/adapters/cursor.py` - CursorAdapter implementation
- `src/site_nine/adapters/aider.py` - AiderAdapter implementation
- `src/site_nine/core/tool_config.py` - Unified ToolConfig model

### Related tasks

- **OPR-H-0065** - Implement ToolAdapter protocol
- **OPR-H-0066** - Implement OpenCodeAdapter
- **OPR-H-0067** - Implement ToolRegistry
- **OPR-H-0068** - Update core code to use adapters
