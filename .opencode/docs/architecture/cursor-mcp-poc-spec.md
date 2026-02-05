# Cursor MCP Adapter: Proof of Concept Specification

**Version:** 1.0  
**Date:** 2026-02-03  
**Author:** Ptah (Architect)  
**Related ADR:** ADR-002 (Cursor MCP First Target)  
**Related Task:** ARC-H-0030

---

## 1. Overview

### Purpose

This document specifies the Proof of Concept (PoC) implementation for the Cursor MCP adapter. The PoC validates:
1. Adapter pattern works for a real non-OpenCode tool
2. MCP protocol integration is feasible
3. Site-nine skills can be exposed as MCP servers
4. Configuration system handles Cursor's format

### Success Criteria

- ✅ Cursor users can run `s9 init --tool cursor` to create `.cursor/` structure
- ✅ Site-nine skills work in Cursor via MCP
- ✅ Basic task management works (create, list, claim tasks)
- ✅ Agent sessions tracked across Cursor usage
- ✅ Zero OpenCode regressions
- ✅ PoC demonstrates extensibility for future tools

### Scope

**In Scope:**
- CursorAdapter implementation (ToolAdapter protocol)
- CursorConfigLoader (cursor.json → ToolConfig)
- MCP client integration (connect to Cursor's MCP host)
- One MCP server (session-start skill)
- Basic cursor.json template generation

**Out of Scope:**
- Full skill library migration to MCP
- Cursor-specific UI customizations
- Performance optimizations
- Production-ready error handling
- MCP server discovery/registration automation

---

## 2. Cursor MCP Architecture

### MCP Protocol Basics

Model Context Protocol (MCP) is Anthropic's specification for AI tool integration. It defines:
- **MCP Servers**: Expose tools/resources to AI systems
- **MCP Clients**: Connect to servers and invoke tools
- **Transport**: JSON-RPC 2.0 over stdio or HTTP

**Site-nine's Role:**
- **MCP Client**: Connect to Cursor's MCP host
- **MCP Server**: Expose site-nine skills as MCP tools

### Integration Model

```
┌────────────────────────────────────────────────────┐
│                  Cursor IDE                         │
│  ┌──────────────────────────────────────────┐     │
│  │          Cursor MCP Host                  │     │
│  │  (coordinates MCP servers)               │     │
│  └───────┬──────────────────────────┬───────┘     │
│          │                          │              │
└──────────┼──────────────────────────┼──────────────┘
           │                          │
           │ MCP Protocol             │ MCP Protocol
           │ (JSON-RPC)               │ (JSON-RPC)
           ▼                          ▼
  ┌────────────────┐        ┌────────────────────┐
  │  s9 MCP Server │        │ Other MCP Servers  │
  │  (skills)      │        │ (filesystem, etc.)│
  └────────┬───────┘        └────────────────────┘
           │
           │ invokes
           ▼
  ┌────────────────┐
  │ site-nine Core │
  │ (CLI, Tasks,   │
  │  Agents, etc.) │
  └────────────────┘
```

---

## 3. CursorAdapter Implementation

### File: `src/site_nine/adapters/cursor.py`

```python
from pathlib import Path
from site_nine.adapters.protocol import ToolAdapter
from site_nine.core.tool_config import ToolConfig
import json

class CursorAdapter:
    """Adapter for Cursor MCP integration"""
    
    def __init__(self, tool_dir: Path):
        """Initialize Cursor adapter.
        
        Args:
            tool_dir: .cursor directory path
        """
        self._tool_dir = tool_dir
        self._config: ToolConfig | None = None
        self._mcp_client: "MCPClient | None" = None
    
    # ============================================================
    # Configuration & Metadata
    # ============================================================
    
    @property
    def tool_name(self) -> str:
        return "cursor"
    
    @property
    def tool_version(self) -> str:
        return "1.0.0"
    
    @property
    def config(self) -> ToolConfig:
        if not self._config:
            self._config = self.load_config()
        return self._config
    
    # ============================================================
    # Path Resolution
    # ============================================================
    
    def get_tool_dir(self) -> Path:
        return self._tool_dir
    
    def get_data_dir(self) -> Path:
        return self._tool_dir / "data"
    
    def get_docs_dir(self) -> Path:
        return self._tool_dir / "docs"
    
    def get_work_dir(self) -> Path:
        return self._tool_dir / "work"
    
    def get_skills_dir(self) -> Path:
        # In Cursor, skills are MCP servers
        return self._tool_dir / "mcp" / "servers"
    
    def get_commands_dir(self) -> Path:
        return self._tool_dir / "commands"
    
    def get_sessions_dir(self) -> Path:
        return self._tool_dir / "work" / "sessions"
    
    def get_tasks_dir(self) -> Path:
        return self._tool_dir / "work" / "tasks"
    
    def get_database_path(self) -> Path:
        return self._tool_dir / "data" / "project.db"
    
    # ============================================================
    # Configuration Loading
    # ============================================================
    
    def load_config(self) -> ToolConfig:
        """Load cursor.json and convert to ToolConfig"""
        from site_nine.adapters.config_loaders import CursorConfigLoader
        
        config_path = self.get_config_path()
        loader = CursorConfigLoader()
        return loader.load(config_path)
    
    def get_config_path(self) -> Path:
        return self._tool_dir / "cursor.json"
    
    # ============================================================
    # Skills System (MCP Integration)
    # ============================================================
    
    def load_skill(self, name: str) -> "SkillDefinition":
        """Load skill from MCP server definition"""
        from site_nine.skills.definition import SkillDefinition
        
        # Check for skill.yaml (new format)
        skill_dir = self.get_skills_dir() / name
        yaml_path = skill_dir / "skill.yaml"
        
        if yaml_path.exists():
            return SkillDefinition.from_yaml(yaml_path)
        
        # Check for MCP server definition
        mcp_path = skill_dir / "server.json"
        if mcp_path.exists():
            return self._convert_mcp_to_skill(mcp_path)
        
        raise FileNotFoundError(f"Skill '{name}' not found")
    
    def _convert_mcp_to_skill(self, mcp_path: Path) -> "SkillDefinition":
        """Convert MCP server definition to SkillDefinition"""
        # Parse MCP server.json
        with open(mcp_path) as f:
            mcp_def = json.load(f)
        
        # Map MCP tools to skill steps
        # (implementation details omitted for brevity)
        ...
    
    def list_skills(self) -> list[str]:
        """List available skills (MCP servers)"""
        skills_dir = self.get_skills_dir()
        if not skills_dir.exists():
            return []
        
        return [
            d.name for d in skills_dir.iterdir()
            if d.is_dir() and (d / "skill.yaml").exists() or (d / "server.json").exists()
        ]
    
    def get_skill_renderer(self) -> "SkillRenderer":
        """Get Cursor MCP skill renderer"""
        from site_nine.skills.renderers.cursor import CursorMCPRenderer
        
        # Get or create MCP client
        if not self._mcp_client:
            self._mcp_client = self._connect_mcp()
        
        return CursorMCPRenderer(self._mcp_client)
    
    def _connect_mcp(self) -> "MCPClient":
        """Connect to Cursor's MCP host"""
        from site_nine.mcp.client import MCPClient
        
        # Cursor MCP host connection details
        # (would be configured in cursor.json)
        return MCPClient(
            transport="stdio",  # or "http"
            # connection params...
        )
    
    # ============================================================
    # Commands System
    # ============================================================
    
    def load_command(self, name: str) -> "CommandDefinition":
        """Load command definition"""
        # Similar to OpenCode, but may use MCP format
        from site_nine.commands.definition import CommandDefinition
        
        commands_dir = self.get_commands_dir()
        command_file = commands_dir / f"{name}.md"
        
        if command_file.exists():
            return CommandDefinition.from_file(command_file)
        
        raise FileNotFoundError(f"Command '{name}' not found")
    
    def list_commands(self) -> list[str]:
        """List available commands"""
        commands_dir = self.get_commands_dir()
        if not commands_dir.exists():
            return []
        
        return [
            f.stem for f in commands_dir.glob("*.md")
        ]
    
    # ============================================================
    # Session Management
    # ============================================================
    
    def supports_session_api(self) -> bool:
        """Cursor may or may not have session API"""
        # Check if Cursor exposes session API
        # For PoC, return False (Cursor sessions not accessible)
        return False
    
    def rename_session(self, session_id: str, new_title: str) -> bool:
        """Not supported in Cursor PoC"""
        return False
    
    def list_tool_sessions(self) -> list[dict]:
        """Not supported in Cursor PoC"""
        return []
    
    # ============================================================
    # Initialization
    # ============================================================
    
    def initialize_project(self, project_dir: Path, config: "ProjectConfig") -> None:
        """Initialize .cursor/ structure"""
        from site_nine.cli.init import render_cursor_templates
        
        cursor_dir = project_dir / ".cursor"
        cursor_dir.mkdir(exist_ok=True)
        
        # Create directory structure
        (cursor_dir / "data").mkdir(exist_ok=True)
        (cursor_dir / "docs").mkdir(exist_ok=True)
        (cursor_dir / "work" / "sessions").mkdir(parents=True, exist_ok=True)
        (cursor_dir / "work" / "tasks").mkdir(parents=True, exist_ok=True)
        (cursor_dir / "mcp" / "servers").mkdir(parents=True, exist_ok=True)
        (cursor_dir / "commands").mkdir(exist_ok=True)
        
        # Render templates
        render_cursor_templates(cursor_dir, config)
    
    # ============================================================
    # Tool-Specific Features
    # ============================================================
    
    def get_capabilities(self) -> set[str]:
        """Cursor capabilities"""
        return {
            "mcp-server",
            "mcp-client",
            "skills-yaml",
        }
    
    def execute_tool_specific(self, feature: str, **kwargs):
        """Execute Cursor-specific features"""
        if feature == "mcp-server":
            # Start MCP server for site-nine skills
            return self._start_mcp_server()
        else:
            raise NotImplementedError(f"Feature '{feature}' not supported")
    
    def _start_mcp_server(self) -> "MCPServer":
        """Start MCP server exposing site-nine skills"""
        from site_nine.mcp.server import SiteNineMCPServer
        
        return SiteNineMCPServer(self)
```

---

## 4. MCP Server Implementation

### File: `src/site_nine/mcp/server.py`

```python
from pathlib import Path
import json
import sys

from site_nine.adapters.cursor import CursorAdapter
from site_nine.skills.executor import SkillExecutor

class SiteNineMCPServer:
    """MCP server exposing site-nine skills as MCP tools"""
    
    def __init__(self, adapter: CursorAdapter):
        self.adapter = adapter
        self.executor = SkillExecutor(
            renderer=adapter.get_skill_renderer(),
            tool_name="cursor"
        )
    
    def start(self):
        """Start MCP server on stdio"""
        # MCP uses JSON-RPC 2.0 over stdio
        # Read requests from stdin, write responses to stdout
        
        for line in sys.stdin:
            try:
                request = json.loads(line)
                response = self.handle_request(request)
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                }
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()
    
    def handle_request(self, request: dict) -> dict:
        """Handle MCP JSON-RPC request"""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        if method == "initialize":
            return self.handle_initialize(request_id)
        elif method == "tools/list":
            return self.handle_list_tools(request_id)
        elif method == "tools/call":
            return self.handle_call_tool(request_id, params)
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    
    def handle_initialize(self, request_id) -> dict:
        """Handle MCP initialize request"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "site-nine",
                    "version": "2.0.0"
                }
            }
        }
    
    def handle_list_tools(self, request_id) -> dict:
        """List available tools (site-nine skills)"""
        skills = self.adapter.list_skills()
        
        tools = []
        for skill_name in skills:
            try:
                skill = self.adapter.load_skill(skill_name)
                tools.append({
                    "name": f"s9-{skill_name}",
                    "description": skill.description,
                    "inputSchema": {
                        "type": "object",
                        "properties": {},  # Extract from skill definition
                        "required": []
                    }
                })
            except Exception:
                # Skip skills that can't be loaded
                continue
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": tools
            }
        }
    
    async def handle_call_tool(self, request_id, params: dict) -> dict:
        """Execute skill tool"""
        tool_name = params.get("name")
        
        # Strip s9- prefix
        if tool_name.startswith("s9-"):
            skill_name = tool_name[3:]
        else:
            skill_name = tool_name
        
        try:
            # Load and execute skill
            skill = self.adapter.load_skill(skill_name)
            result = await self.executor.execute(skill)
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32000,
                    "message": f"Tool execution failed: {str(e)}"
                }
            }
```

---

## 5. cursor.json Template

**File**: `src/site_nine/templates/cursor/cursor.json.jinja`

```json
{
  "name": "{{ project_name }}",
  "version": "1.0.0",
  "description": "{{ project_description }}",
  
  "mcpServers": {
    "site-nine": {
      "command": "uv",
      "args": ["run", "s9", "mcp", "server"],
      "env": {
        "SITE_NINE_TOOL": "cursor"
      }
    }
  },
  
  "rules": [
    "Site-nine project management system is active",
    "Use s9- prefixed tools for task management and agent sessions",
    "Available tools: s9-session-start, s9-task-list, s9-task-claim, etc."
  ]
}
```

---

## 6. PoC Validation Tests

### Test Cases

**Test 1: Initialization**
```bash
$ cd test-project/
$ s9 init --tool cursor
# Should create .cursor/ directory with cursor.json
```

**Test 2: Skill Loading**
```python
def test_cursor_adapter_loads_skill():
    adapter = CursorAdapter(Path(".cursor"))
    skill = adapter.load_skill("session-start")
    assert skill.name == "session-start"
    assert "cursor" in skill.compatibility
```

**Test 3: MCP Server**
```bash
$ uv run s9 mcp server
# Should start MCP server on stdio
# Send initialize request, verify response
```

**Test 4: Task Management**
```bash
$ uv run s9 task list
# Should work identically to OpenCode
```

**Test 5: Zero OpenCode Regression**
```bash
$ cd opencode-project/
$ uv run s9 dashboard
# Should detect .opencode/ and work unchanged
```

---

## 7. Demo Scenario

### Setup

1. Install site-nine v2.0.0
2. Create new project: `mkdir cursor-demo && cd cursor-demo`
3. Initialize for Cursor: `s9 init --tool cursor`
4. Configure Cursor to use site-nine MCP server (via cursor.json)

### Demo Walkthrough

**Step 1: Open project in Cursor**
```
Cursor detects cursor.json
Starts site-nine MCP server
Tools appear in Cursor's tool palette
```

**Step 2: User invokes s9-session-start**
```
User: "Start a new agent session"
Cursor: [Invokes s9-session-start MCP tool]
Site-nine: Runs session-start skill
Output: Role selection, daemon name, etc.
```

**Step 3: User creates task**
```
User: "Create a task for implementing auth"
Cursor: [Invokes s9-task-create]
Site-nine: Creates task in database
Output: "Created task ENG-H-0042"
```

**Step 4: User lists tasks**
```
User: "Show my tasks"
Cursor: [Invokes s9-task-list]
Site-nine: Queries database, returns task table
Output: Formatted task list
```

---

## 8. Implementation Checklist

**Phase 1: Foundation (Week 1)**
- [ ] Create `src/site_nine/adapters/cursor.py`
- [ ] Implement CursorAdapter (ToolAdapter protocol)
- [ ] Create `CursorConfigLoader`
- [ ] Add cursor.json template
- [ ] Register CursorAdapter in ToolRegistry
- [ ] Unit tests for CursorAdapter

**Phase 2: MCP Integration (Week 2)**
- [ ] Create `src/site_nine/mcp/server.py`
- [ ] Implement MCP JSON-RPC server
- [ ] Handle initialize, tools/list, tools/call
- [ ] Add `s9 mcp server` CLI command
- [ ] Integration tests for MCP server

**Phase 3: Skills Migration (Week 3)**
- [ ] Convert session-start to skill.yaml
- [ ] Test skill execution via MCP
- [ ] Create CursorMCPRenderer
- [ ] Test skill rendering in Cursor

**Phase 4: Testing & Documentation (Week 4)**
- [ ] End-to-end tests in Cursor
- [ ] Regression tests (OpenCode unchanged)
- [ ] Write Cursor setup guide
- [ ] Demo video/screenshots

---

## 9. Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| MCP protocol implementation issues | High | Follow MCP spec closely, test against reference servers |
| Cursor MCP API changes | Medium | Version adapter, track Cursor updates |
| Skills don't map cleanly to MCP tools | High | Design skill.yaml with MCP in mind, escape hatch for complex skills |
| Performance issues with MCP overhead | Low | Benchmark, optimize if needed |

---

## 10. Success Metrics

- ✅ CursorAdapter implements all required ToolAdapter methods
- ✅ At least one skill (session-start) works via MCP
- ✅ Task management commands work identically
- ✅ Zero OpenCode test failures
- ✅ Demo successfully completed
- ✅ Documentation published

---

**End of Cursor MCP PoC Specification**
