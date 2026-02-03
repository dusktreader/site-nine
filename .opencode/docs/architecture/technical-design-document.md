# Technical Design Document: Multi-Tool Adapter Architecture

**Version:** 1.0  
**Date:** 2026-02-03  
**Author:** Ptah (Architect)  
**Status:** Proposed  
**Related Task:** ARC-H-0030

---

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Adapter Pattern Specification](#adapter-pattern-specification)
4. [Configuration System](#configuration-system)
5. [Skills System Architecture](#skills-system-architecture)
6. [Path Resolution](#path-resolution)
7. [Tool Detection & Registry](#tool-detection--registry)
8. [Data Flow Diagrams](#data-flow-diagrams)
9. [Sequence Diagrams](#sequence-diagrams)
10. [API Specifications](#api-specifications)
11. [Error Handling](#error-handling)
12. [Testing Strategy](#testing-strategy)

---

## 1. Overview

### Purpose

This document provides detailed technical specifications for refactoring site-nine from an OpenCode-specific system to a tool-agnostic framework that supports multiple AI coding tools (OpenCode, Cursor MCP, Aider, etc.).

### Goals

- **Tool Abstraction**: Core site-nine functionality works with any supported tool
- **Zero Regression**: Existing OpenCode users experience no breaking changes
- **Extensibility**: New tools can be added via adapters without core changes
- **Clean Architecture**: Clear separation of concerns between layers

### Design Principles

1. **Dependency Inversion**: Core depends on abstractions, not concrete tools
2. **Open/Closed**: Open for extension (new tools), closed for modification (core logic)
3. **Single Responsibility**: Each component has one reason to change
4. **Interface Segregation**: Adapters implement only what they need
5. **Backward Compatibility**: OpenCode behavior preserved exactly

---

## 2. System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Layer                                │
│  s9 init, s9 task, s9 agent, s9 dashboard, s9 name, etc.       │
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
│  │                  │  │   (MCP)          │  │  (Future)     │ │
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

### Layer Responsibilities

#### CLI Layer
- Parse command-line arguments
- Validate input
- Delegate to application layer
- Format output for terminal

#### Application Layer
- Business logic (task management, agent sessions, etc.)
- **Tool-agnostic**: No knowledge of specific tools
- Uses abstractions (ToolAdapter, ToolConfig)
- Manages core data (database, files)

#### Abstraction Layer
- Defines protocols/interfaces for tools
- Provides unified models (ToolConfig)
- Path resolution across tools
- Skill rendering abstraction

#### Tool Adapter Layer
- Implements protocols for specific tools
- Handles tool-specific APIs
- Manages tool-specific configurations
- Maps tool formats to unified models

---

## 3. Adapter Pattern Specification

### ToolAdapter Protocol

**File**: `src/site_nine/adapters/protocol.py`

```python
from typing import Protocol, runtime_checkable
from pathlib import Path

@runtime_checkable
class ToolAdapter(Protocol):
    """Protocol defining interface for all tool adapters.
    
    All adapters must implement these methods to integrate with site-nine.
    This protocol follows the Dependency Inversion Principle - core code
    depends on this abstraction, not concrete implementations.
    """
    
    # ============================================================
    # Configuration & Metadata
    # ============================================================
    
    @property
    def tool_name(self) -> str:
        """Return tool identifier (opencode, cursor, aider)"""
        ...
    
    @property
    def tool_version(self) -> str:
        """Return tool version string"""
        ...
    
    @property
    def config(self) -> "ToolConfig":
        """Return unified configuration model"""
        ...
    
    # ============================================================
    # Path Resolution
    # ============================================================
    
    def get_tool_dir(self) -> Path:
        """Get tool base directory (.opencode/, .cursor/, etc.)"""
        ...
    
    def get_data_dir(self) -> Path:
        """Get data directory (database, caches)"""
        ...
    
    def get_docs_dir(self) -> Path:
        """Get documentation directory"""
        ...
    
    def get_work_dir(self) -> Path:
        """Get work directory (sessions, tasks, planning)"""
        ...
    
    def get_skills_dir(self) -> Path:
        """Get skills directory"""
        ...
    
    def get_commands_dir(self) -> Path:
        """Get commands directory"""
        ...
    
    def get_sessions_dir(self) -> Path:
        """Get sessions directory"""
        ...
    
    def get_tasks_dir(self) -> Path:
        """Get tasks directory"""
        ...
    
    def get_database_path(self) -> Path:
        """Get database file path"""
        ...
    
    # ============================================================
    # Configuration Loading
    # ============================================================
    
    def load_config(self) -> "ToolConfig":
        """Load and parse tool configuration file.
        
        Returns:
            ToolConfig: Unified configuration model
            
        Raises:
            FileNotFoundError: If config file not found
            ValueError: If config invalid
        """
        ...
    
    def get_config_path(self) -> Path:
        """Get path to tool's config file (opencode.json, cursor.json, etc.)"""
        ...
    
    # ============================================================
    # Skills System
    # ============================================================
    
    def load_skill(self, name: str) -> "SkillDefinition":
        """Load skill definition by name.
        
        Args:
            name: Skill name (e.g., "session-start")
            
        Returns:
            SkillDefinition: Parsed skill workflow
            
        Raises:
            FileNotFoundError: If skill not found
        """
        ...
    
    def list_skills(self) -> list[str]:
        """List all available skill names"""
        ...
    
    def get_skill_renderer(self) -> "SkillRenderer":
        """Get tool-specific skill renderer.
        
        Returns:
            SkillRenderer: Renderer for this tool's output format
        """
        ...
    
    # ============================================================
    # Commands System
    # ============================================================
    
    def load_command(self, name: str) -> "CommandDefinition":
        """Load command definition by name.
        
        Args:
            name: Command name (e.g., "summon", "dismiss")
            
        Returns:
            CommandDefinition: Parsed command definition
        """
        ...
    
    def list_commands(self) -> list[str]:
        """List all available command names"""
        ...
    
    # ============================================================
    # Session Management (Optional)
    # ============================================================
    
    def supports_session_api(self) -> bool:
        """Check if tool supports programmatic session management.
        
        Returns:
            True if tool has session API (e.g., OpenCode TUI),
            False otherwise (e.g., Aider CLI-only)
        """
        ...
    
    def rename_session(self, session_id: str, new_title: str) -> bool:
        """Rename tool session (if supported).
        
        Args:
            session_id: Tool-specific session identifier
            new_title: New session title
            
        Returns:
            True if renamed successfully, False if not supported
        """
        ...
    
    def list_tool_sessions(self) -> list[dict]:
        """List active tool sessions (if supported).
        
        Returns:
            List of session metadata dicts, empty if not supported
        """
        ...
    
    # ============================================================
    # Initialization
    # ============================================================
    
    def initialize_project(self, project_dir: Path, config: "ProjectConfig") -> None:
        """Initialize new project with tool-specific structure.
        
        Creates directory structure, config files, templates, etc.
        
        Args:
            project_dir: Project root directory
            config: Project configuration (name, type, features)
        """
        ...
    
    # ============================================================
    # Tool-Specific Features (Optional)
    # ============================================================
    
    def get_capabilities(self) -> set[str]:
        """Return set of tool-specific capabilities.
        
        Examples: {"session-api", "mcp-server", "file-watching"}
        """
        ...
    
    def execute_tool_specific(self, feature: str, **kwargs) -> any:
        """Execute tool-specific feature not in protocol.
        
        Escape hatch for tool-unique functionality.
        
        Args:
            feature: Feature identifier
            **kwargs: Feature-specific arguments
            
        Returns:
            Feature-specific return value
            
        Raises:
            NotImplementedError: If feature not supported
        """
        ...
```

### OpenCodeAdapter Implementation

**File**: `src/site_nine/adapters/opencode.py`

```python
from pathlib import Path
from site_nine.adapters.protocol import ToolAdapter
from site_nine.core.tool_config import ToolConfig
from site_nine.core.paths import find_opencode_dir
import json

class OpenCodeAdapter:
    """Adapter for OpenCode - wraps existing implementation.
    
    This adapter preserves exact OpenCode behavior for backward compatibility.
    It delegates to existing code rather than reimplementing.
    """
    
    def __init__(self, tool_dir: Path | None = None):
        """Initialize OpenCode adapter.
        
        Args:
            tool_dir: .opencode directory path (auto-detected if None)
        """
        self._tool_dir = tool_dir or find_opencode_dir()
        if not self._tool_dir:
            raise FileNotFoundError(".opencode directory not found")
        
        self._config: ToolConfig | None = None
    
    # ============================================================
    # Configuration & Metadata
    # ============================================================
    
    @property
    def tool_name(self) -> str:
        return "opencode"
    
    @property
    def tool_version(self) -> str:
        # Read from package or config
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
        return self._tool_dir / "skills"
    
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
        """Load opencode.json and convert to ToolConfig"""
        config_path = self.get_config_path()
        
        with open(config_path) as f:
            raw = json.load(f)
        
        from site_nine.core.tool_config import (
            ToolConfig, CommandConfig, FeaturesConfig, AgentRoleConfig
        )
        
        return ToolConfig(
            tool_name="opencode",
            tool_dir=self._tool_dir,
            project_name=self._tool_dir.parent.name,
            project_type="python",  # from config or detect
            data_dir=self.get_data_dir(),
            docs_dir=self.get_docs_dir(),
            work_dir=self.get_work_dir(),
            skills_dir=self.get_skills_dir(),
            commands_dir=self.get_commands_dir(),
            skills_paths=[Path(p) for p in raw.get("skills", {}).get("paths", [])],
            commands={
                name: CommandConfig.from_dict(cmd) 
                for name, cmd in raw.get("command", {}).items()
            },
            features=FeaturesConfig(),  # defaults or from config
            agent_roles=[],  # load if needed
        )
    
    def get_config_path(self) -> Path:
        return self._tool_dir / "opencode.json"
    
    # ============================================================
    # Skills System
    # ============================================================
    
    def load_skill(self, name: str) -> "SkillDefinition":
        """Load skill - supports both old and new formats"""
        from site_nine.skills.definition import SkillDefinition
        from site_nine.skills.legacy import convert_legacy_skill
        
        skill_dir = self.get_skills_dir() / name
        
        # Try new format first
        yaml_path = skill_dir / "skill.yaml"
        if yaml_path.exists():
            return SkillDefinition.from_yaml(yaml_path)
        
        # Fall back to legacy SKILL.md format
        md_path = skill_dir / "SKILL.md"
        if md_path.exists():
            return convert_legacy_skill(md_path)
        
        raise FileNotFoundError(f"Skill '{name}' not found in {skill_dir}")
    
    def list_skills(self) -> list[str]:
        """List available skills"""
        skills_dir = self.get_skills_dir()
        if not skills_dir.exists():
            return []
        
        return [
            d.name for d in skills_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]
    
    def get_skill_renderer(self) -> "SkillRenderer":
        """Get OpenCode skill renderer"""
        from site_nine.skills.renderers.opencode import OpenCodeRenderer
        return OpenCodeRenderer()
    
    # ============================================================
    # Commands System
    # ============================================================
    
    def load_command(self, name: str) -> "CommandDefinition":
        """Load command definition"""
        from site_nine.commands.definition import CommandDefinition
        
        commands_dir = self.get_commands_dir()
        command_file = commands_dir / f"{name}.md"
        
        if not command_file.exists():
            raise FileNotFoundError(f"Command '{name}' not found")
        
        return CommandDefinition.from_file(command_file)
    
    def list_commands(self) -> list[str]:
        """List available commands"""
        commands_dir = self.get_commands_dir()
        if not commands_dir.exists():
            return []
        
        return [
            f.stem for f in commands_dir.glob("*.md")
            if not f.name.startswith(".")
        ]
    
    # ============================================================
    # Session Management
    # ============================================================
    
    def supports_session_api(self) -> bool:
        """OpenCode supports session API"""
        return True
    
    def rename_session(self, session_id: str, new_title: str) -> bool:
        """Rename OpenCode TUI session"""
        from site_nine.cli.agent import _update_session_title
        try:
            _update_session_title(session_id, new_title)
            return True
        except Exception:
            return False
    
    def list_tool_sessions(self) -> list[dict]:
        """List OpenCode sessions"""
        from site_nine.cli.agent import _list_opencode_sessions
        return _list_opencode_sessions()
    
    # ============================================================
    # Initialization
    # ============================================================
    
    def initialize_project(self, project_dir: Path, config: "ProjectConfig") -> None:
        """Initialize .opencode/ structure"""
        from site_nine.cli.init import render_all_templates
        from site_nine.core.templates import TemplateRenderer
        
        opencode_dir = project_dir / ".opencode"
        opencode_dir.mkdir(exist_ok=True)
        
        renderer = TemplateRenderer()
        context = config.to_template_context()
        render_all_templates(renderer, opencode_dir, context)
    
    # ============================================================
    # Tool-Specific Features
    # ============================================================
    
    def get_capabilities(self) -> set[str]:
        """OpenCode capabilities"""
        return {
            "session-api",
            "tui-integration",
            "skills-markdown",
            "commands-markdown",
        }
    
    def execute_tool_specific(self, feature: str, **kwargs):
        """Execute OpenCode-specific features"""
        if feature == "tui-integration":
            # OpenCode-specific TUI operations
            pass
        else:
            raise NotImplementedError(f"Feature '{feature}' not supported")
```

---

## 4. Configuration System

### ToolConfig (Unified Model)

**File**: `src/site_nine/core/tool_config.py`

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

@dataclass
class CommandConfig:
    """Configuration for a single command"""
    name: str
    template: Path
    description: str
    
    @classmethod
    def from_dict(cls, data: dict) -> "CommandConfig":
        return cls(
            name=data.get("name", ""),
            template=Path(data["template"]),
            description=data.get("description", ""),
        )

@dataclass
class FeaturesConfig:
    """Feature flags"""
    pm_system: bool = True
    session_tracking: bool = True
    commit_guidelines: bool = True
    daemon_naming: bool = True

@dataclass
class AgentRoleConfig:
    """Agent role configuration"""
    name: str
    enabled: bool = True
    description: str | None = None

@dataclass
class ToolConfig:
    """Unified configuration model for all tools.
    
    This model abstracts over tool-specific config formats,
    providing a common interface for site-nine core.
    """
    
    # Tool identification
    tool_name: str              # "opencode", "cursor", "aider"
    tool_dir: Path              # .opencode/, .cursor/, .aider/
    
    # Project metadata
    project_name: str
    project_type: str = "python"
    project_description: str = ""
    
    # Directory structure (absolute paths)
    data_dir: Path
    docs_dir: Path
    work_dir: Path
    skills_dir: Path
    commands_dir: Path
    
    # Skills configuration
    skills_paths: list[Path] = field(default_factory=list)
    
    # Commands configuration
    commands: dict[str, CommandConfig] = field(default_factory=dict)
    
    # Features & roles
    features: FeaturesConfig = field(default_factory=FeaturesConfig)
    agent_roles: list[AgentRoleConfig] = field(default_factory=list)
    
    # Custom variables
    custom_vars: dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_tool_config(cls, tool_name: str, config_path: Path) -> "ToolConfig":
        """Load tool-specific config and normalize to ToolConfig.
        
        Args:
            tool_name: Tool identifier ("opencode", "cursor", etc.)
            config_path: Path to tool's config file
            
        Returns:
            Normalized ToolConfig
        """
        from site_nine.adapters.config_loaders import get_config_loader
        
        loader = get_config_loader(tool_name)
        return loader.load(config_path)
    
    def get_database_path(self) -> Path:
        """Get database path"""
        return self.data_dir / "project.db"
    
    def get_sessions_path(self) -> Path:
        """Get sessions directory"""
        return self.work_dir / "sessions"
    
    def get_tasks_path(self) -> Path:
        """Get tasks directory"""
        return self.work_dir / "tasks"
    
    def to_template_context(self) -> dict[str, Any]:
        """Convert to Jinja2 template context"""
        from datetime import datetime
        
        return {
            "tool_name": self.tool_name,
            "project_name": self.project_name,
            "project_name_hyphen": self.project_name.lower().replace("_", "-"),
            "project_name_underscore": self.project_name.lower().replace("-", "_"),
            "project_type": self.project_type,
            "project_description": self.project_description,
            "has_pm_system": self.features.pm_system,
            "has_session_tracking": self.features.session_tracking,
            "has_commit_guidelines": self.features.commit_guidelines,
            "agent_roles": [
                {"name": role.name, "enabled": role.enabled}
                for role in self.agent_roles
            ],
            "custom": self.custom_vars,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "generated_at": datetime.now().isoformat(),
        }
```

### Config Loaders

**File**: `src/site_nine/adapters/config_loaders.py`

```python
from pathlib import Path
from typing import Protocol
import json
import yaml

from site_nine.core.tool_config import ToolConfig, CommandConfig, FeaturesConfig

class ConfigLoader(Protocol):
    """Protocol for tool-specific config loaders"""
    
    def load(self, config_path: Path) -> ToolConfig:
        """Load tool-specific config and normalize to ToolConfig"""
        ...

class OpenCodeConfigLoader:
    """Load opencode.json"""
    
    def load(self, config_path: Path) -> ToolConfig:
        with open(config_path) as f:
            raw = json.load(f)
        
        tool_dir = config_path.parent
        
        return ToolConfig(
            tool_name="opencode",
            tool_dir=tool_dir,
            project_name=tool_dir.parent.name,
            project_type=raw.get("project", {}).get("type", "python"),
            project_description=raw.get("project", {}).get("description", ""),
            data_dir=tool_dir / "data",
            docs_dir=tool_dir / "docs",
            work_dir=tool_dir / "work",
            skills_dir=tool_dir / "skills",
            commands_dir=tool_dir / "commands",
            skills_paths=[
                Path(p) for p in raw.get("skills", {}).get("paths", [])
            ],
            commands={
                name: CommandConfig.from_dict({**cmd, "name": name})
                for name, cmd in raw.get("command", {}).items()
            },
            features=FeaturesConfig(
                **raw.get("features", {})
            ),
        )

class CursorConfigLoader:
    """Load cursor.json (MCP format)"""
    
    def load(self, config_path: Path) -> ToolConfig:
        with open(config_path) as f:
            raw = json.load(f)
        
        tool_dir = config_path.parent
        
        # Map Cursor MCP config to ToolConfig
        return ToolConfig(
            tool_name="cursor",
            tool_dir=tool_dir,
            project_name=raw.get("name", tool_dir.parent.name),
            project_type=raw.get("type", "python"),
            data_dir=tool_dir / "data",
            docs_dir=tool_dir / "docs",
            work_dir=tool_dir / "work",
            skills_dir=tool_dir / "mcp" / "servers",  # MCP servers location
            commands_dir=tool_dir / "commands",
            skills_paths=[
                Path(p) for p in raw.get("mcpServers", {}).keys()
            ],
            # Map MCP commands to site-nine commands
            commands={},  # Populate from MCP config
        )

class AiderConfigLoader:
    """Load .aider.conf.yml"""
    
    def load(self, config_path: Path) -> ToolConfig:
        with open(config_path) as f:
            raw = yaml.safe_load(f)
        
        tool_dir = config_path.parent
        
        return ToolConfig(
            tool_name="aider",
            tool_dir=tool_dir,
            project_name=raw.get("project_name", tool_dir.parent.name),
            project_type=raw.get("project_type", "python"),
            data_dir=tool_dir / "data",
            docs_dir=tool_dir / "docs",
            work_dir=tool_dir / "work",
            skills_dir=tool_dir / "skills",
            commands_dir=tool_dir / "commands",
            # Map Aider config...
        )

def get_config_loader(tool_name: str) -> ConfigLoader:
    """Get config loader for tool"""
    loaders = {
        "opencode": OpenCodeConfigLoader(),
        "cursor": CursorConfigLoader(),
        "aider": AiderConfigLoader(),
    }
    
    if tool_name not in loaders:
        raise ValueError(f"Unknown tool: {tool_name}")
    
    return loaders[tool_name]
```

---

**[This document continues with sections 5-12. Due to length, I'll create this as a separate file. Should I continue with the full document or would you like me to proceed to the other deliverables?]**
