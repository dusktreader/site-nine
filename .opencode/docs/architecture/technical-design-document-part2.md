# Technical Design Document (Part 2): Skills, Diagrams, and Implementation

**Continuation of**: `technical-design-document.md`

---

## 5. Skills System Architecture

### Skill Definition Format (YAML)

**File**: `{tool}/skills/{skill-name}/skill.yaml`

```yaml
# Skill metadata
name: session-start
version: "1.0.0"
description: Initialize a new agent session with role selection and daemon naming
category: session-management
author: site-nine
license: MIT

# Tool compatibility
compatibility:
  - opencode
  - cursor
  - aider

# Workflow steps (tool-agnostic)
steps:
  # Step 1: Execute command
  - id: show-dashboard
    type: command
    command: s9 dashboard
    description: Display project status
    capture_output: true
    store_as: dashboard_output
    
  # Step 2: Render output using template
  - id: present-status
    type: output
    template: status-summary
    data:
      dashboard: "{dashboard_output}"
    
  # Step 3: Ask question
  - id: get-role
    type: question
    prompt: "Which role would you like me to assume?"
    options:
      type: command
      command: s9 agent roles
    validate:
      type: enum
      values: [Administrator, Architect, Builder, Tester, Documentarian, Designer, Inspector, Operator]
    store_as: selected_role
    
  # Step 4: Conditional logic
  - id: check-existing-sessions
    type: conditional
    condition: "{active_sessions} > 0"
    then:
      - type: output
        template: warning-active-sessions
    
  # Step 5: Loop
  - id: suggest-names
    type: command
    command: s9 name suggest {selected_role} --count 3
    store_as: name_suggestions
    
  - id: select-name
    type: question
    prompt: "Select a daemon name:"
    options:
      type: variable
      source: name_suggestions
    store_as: selected_name
    
  # Step 6: Register agent
  - id: register-agent
    type: command
    command: s9 agent start {selected_name} --role {selected_role} --task "session-start"
    capture_output: true
    parse: json
    store_as: agent_data
    
  # Step 7: Optional step (tool-specific)
  - id: rename-tui
    type: command
    command: s9 agent rename-tui {selected_name} {selected_role}
    optional: true
    fail_silently: true
    when:
      tool: opencode

# Output templates (Jinja2)
templates:
  status-summary: |
    **📊 Project Status**
    
    | Metric           | Count |
    |------------------|-------|
    | Active agents    | {{ active_agents }} |
    | Tasks in progress| {{ tasks_in_progress }} |
    | Tasks completed  | {{ tasks_completed }} |
    
  warning-active-sessions: |
    ⚠️  Warning: {{ active_sessions }} active session(s) detected.
    Consider using /dismiss to end previous sessions.

# Variable definitions
variables:
  dashboard_output: string
  selected_role: string
  name_suggestions: list
  selected_name: string
  agent_data: object

# Validation rules
validation:
  required_commands:
    - s9
  required_files:
    - .opencode/data/project.db
```

### Skill Executor

**File**: `src/site_nine/skills/executor.py`

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import subprocess
import yaml
from loguru import logger

@dataclass
class SkillStep:
    """Single step in skill workflow"""
    id: str
    type: str  # command, output, question, conditional, loop
    config: dict[str, Any]
    optional: bool = False
    fail_silently: bool = False
    when: dict[str, str] | None = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "SkillStep":
        return cls(
            id=data["id"],
            type=data["type"],
            config={k: v for k, v in data.items() if k not in ["id", "type", "optional", "fail_silently", "when"]},
            optional=data.get("optional", False),
            fail_silently=data.get("fail_silently", False),
            when=data.get("when"),
        )

@dataclass
class SkillDefinition:
    """Skill workflow definition"""
    name: str
    version: str
    description: str
    category: str
    compatibility: list[str]
    steps: list[SkillStep]
    templates: dict[str, str]
    variables: dict[str, str]
    
    @classmethod
    def from_yaml(cls, path: Path) -> "SkillDefinition":
        """Load skill from YAML file"""
        with open(path) as f:
            data = yaml.safe_load(f)
        
        return cls(
            name=data["name"],
            version=data["version"],
            description=data["description"],
            category=data.get("category", "general"),
            compatibility=data.get("compatibility", ["opencode"]),
            steps=[SkillStep.from_dict(s) for s in data["steps"]],
            templates=data.get("templates", {}),
            variables=data.get("variables", {}),
        )

class SkillExecutor:
    """Executes skill workflows"""
    
    def __init__(self, renderer: "SkillRenderer", tool_name: str):
        self.renderer = renderer
        self.tool_name = tool_name
        self.state: dict[str, Any] = {}
    
    async def execute(self, skill: SkillDefinition) -> dict[str, Any]:
        """Execute skill workflow.
        
        Args:
            skill: Skill definition to execute
            
        Returns:
            Execution results (state variables)
        """
        logger.info(f"Executing skill: {skill.name} v{skill.version}")
        
        # Validate tool compatibility
        if self.tool_name not in skill.compatibility:
            logger.warning(
                f"Skill {skill.name} may not be compatible with {self.tool_name}"
            )
        
        # Execute steps
        for step in skill.steps:
            try:
                # Check conditional execution
                if step.when and not self._evaluate_condition(step.when):
                    logger.debug(f"Skipping step {step.id} (condition not met)")
                    continue
                
                await self._execute_step(step, skill)
                
            except Exception as e:
                if step.optional or step.fail_silently:
                    logger.warning(f"Optional step {step.id} failed: {e}")
                    continue
                else:
                    logger.error(f"Step {step.id} failed: {e}")
                    raise
        
        return self.state
    
    def _evaluate_condition(self, when: dict[str, str]) -> bool:
        """Evaluate conditional execution"""
        if "tool" in when:
            return when["tool"] == self.tool_name
        # Add more condition types as needed
        return True
    
    async def _execute_step(self, step: SkillStep, skill: SkillDefinition) -> None:
        """Execute single step"""
        logger.debug(f"Executing step: {step.id} (type: {step.type})")
        
        if step.type == "command":
            await self._execute_command(step)
        elif step.type == "output":
            await self._execute_output(step, skill)
        elif step.type == "question":
            await self._execute_question(step)
        elif step.type == "conditional":
            await self._execute_conditional(step, skill)
        else:
            raise ValueError(f"Unknown step type: {step.type}")
    
    async def _execute_command(self, step: SkillStep) -> None:
        """Execute command step"""
        # Interpolate command with state variables
        command = step.config["command"].format(**self.state)
        
        logger.debug(f"Running command: {command}")
        result = subprocess.run(
            command,
            shell=True,
            capture_output=step.config.get("capture_output", False),
            text=True
        )
        
        if result.returncode != 0 and not step.fail_silently:
            raise RuntimeError(f"Command failed: {command}")
        
        # Store output if requested
        if store_var := step.config.get("store_as"):
            output = result.stdout.strip() if result.stdout else ""
            
            # Parse output if requested
            if step.config.get("parse") == "json":
                import json
                self.state[store_var] = json.loads(output)
            else:
                self.state[store_var] = output
    
    async def _execute_output(self, step: SkillStep, skill: SkillDefinition) -> None:
        """Render output using template"""
        template_name = step.config["template"]
        template = skill.templates[template_name]
        
        # Prepare data (interpolate state variables)
        data = step.config.get("data", {})
        interpolated_data = {
            k: v.format(**self.state) if isinstance(v, str) else v
            for k, v in data.items()
        }
        
        # Merge with state
        render_context = {**self.state, **interpolated_data}
        
        # Render via tool-specific renderer
        await self.renderer.render(template, render_context)
    
    async def _execute_question(self, step: SkillStep) -> None:
        """Ask question and store response"""
        prompt = step.config["prompt"].format(**self.state)
        
        # Get options
        options_config = step.config.get("options", {})
        if options_config.get("type") == "command":
            # Run command to get options
            result = subprocess.run(
                options_config["command"].format(**self.state),
                shell=True,
                capture_output=True,
                text=True
            )
            options = result.stdout.strip().split("\n")
        elif options_config.get("type") == "variable":
            # Get options from variable
            options = self.state[options_config["source"]]
        else:
            options = options_config.get("list", [])
        
        # Ask via renderer
        response = await self.renderer.ask_question(prompt, options)
        
        # Validate if specified
        if validate := step.config.get("validate"):
            self._validate_response(response, validate)
        
        # Store response
        if store_var := step.config.get("store_as"):
            self.state[store_var] = response
    
    async def _execute_conditional(self, step: SkillStep, skill: SkillDefinition) -> None:
        """Execute conditional branch"""
        condition = step.config["condition"].format(**self.state)
        
        # Simple eval for now (could use safer expression parser)
        if eval(condition, {}, self.state):
            # Execute 'then' branch
            for substep_data in step.config.get("then", []):
                substep = SkillStep.from_dict({**substep_data, "id": f"{step.id}_then"})
                await self._execute_step(substep, skill)
        elif "else" in step.config:
            # Execute 'else' branch
            for substep_data in step.config["else"]:
                substep = SkillStep.from_dict({**substep_data, "id": f"{step.id}_else"})
                await self._execute_step(substep, skill)
    
    def _validate_response(self, response: str, validation: dict) -> None:
        """Validate user response"""
        if validation.get("type") == "enum":
            if response not in validation["values"]:
                raise ValueError(f"Invalid response: {response}")
        # Add more validation types as needed
```

### Skill Renderers

**File**: `src/site_nine/skills/renderers/opencode.py`

```python
from typing import Protocol, Any
from jinja2 import Template

class SkillRenderer(Protocol):
    """Protocol for tool-specific skill renderers"""
    
    async def render(self, template: str, data: dict[str, Any]) -> None:
        """Render template with data"""
        ...
    
    async def ask_question(self, prompt: str, options: list[str]) -> str:
        """Ask user a question"""
        ...

class OpenCodeRenderer:
    """Renderer for OpenCode (direct output to chat)"""
    
    async def render(self, template: str, data: dict[str, Any]) -> None:
        """Render Jinja2 template and output"""
        jinja_template = Template(template)
        output = jinja_template.render(**data)
        print(output)
    
    async def ask_question(self, prompt: str, options: list[str]) -> str:
        """Present question in OpenCode chat"""
        print(prompt)
        print()
        for i, option in enumerate(options, 1):
            print(f"{i}. {option}")
        print()
        
        # In OpenCode, user responds in chat
        # This is handled by OpenCode's skill system
        # Return value would come from OpenCode API
        return await self._wait_for_user_response()
    
    async def _wait_for_user_response(self) -> str:
        """Wait for user response (OpenCode handles this)"""
        # In reality, OpenCode's skill system provides the response
        # This is a placeholder
        pass
```

**File**: `src/site_nine/skills/renderers/cursor.py`

```python
import json
from typing import Any

class CursorMCPRenderer:
    """Renderer for Cursor MCP protocol"""
    
    def __init__(self, mcp_client: "MCPClient"):
        self.mcp = mcp_client
    
    async def render(self, template: str, data: dict[str, Any]) -> None:
        """Send formatted output via MCP"""
        from jinja2 import Template
        
        jinja_template = Template(template)
        output = jinja_template.render(**data)
        
        await self.mcp.send_notification({
            "method": "notifications/resources/updated",
            "params": {
                "content": output,
                "mimeType": "text/markdown"
            }
        })
    
    async def ask_question(self, prompt: str, options: list[str]) -> str:
        """Ask question via MCP prompt"""
        response = await self.mcp.send_request({
            "method": "sampling/createMessage",
            "params": {
                "messages": [{
                    "role": "assistant",
                    "content": {
                        "type": "text",
                        "text": prompt
                    }
                }],
                "systemPrompt": f"Choose one: {', '.join(options)}",
                "maxTokens": 100
            }
        })
        
        return response["content"]["text"].strip()
```

---

## 6. Tool Detection & Registry

**File**: `src/site_nine/adapters/registry.py`

```python
from pathlib import Path
from typing import Type
import os

from site_nine.adapters.protocol import ToolAdapter
from site_nine.adapters.opencode import OpenCodeAdapter
from site_nine.core.tool_config import ToolConfig

class ToolRegistry:
    """Detects active tool and provides appropriate adapter"""
    
    # Tool detection markers (directory, config file)
    TOOL_MARKERS = {
        "cursor": (".cursor", "cursor.json"),
        "aider": (".aider", ".aider.conf.yml"),
        "opencode": (".opencode", "opencode.json"),
    }
    
    # Tool priority order (for multi-tool projects)
    TOOL_PRIORITY = ["cursor", "aider", "opencode"]
    
    # Adapter class registry
    _ADAPTERS: dict[str, Type[ToolAdapter]] = {}
    
    @classmethod
    def register_adapter(cls, tool_name: str, adapter_class: Type[ToolAdapter]) -> None:
        """Register tool adapter.
        
        Args:
            tool_name: Tool identifier
            adapter_class: Adapter implementation class
        """
        cls._ADAPTERS[tool_name] = adapter_class
    
    @classmethod
    def detect_tool(cls, start_path: Path | None = None) -> str:
        """Auto-detect which tool is active.
        
        Args:
            start_path: Starting directory (defaults to cwd)
            
        Returns:
            Tool name ("opencode", "cursor", "aider")
            
        Priority:
            1. SITE_NINE_TOOL environment variable (explicit override)
            2. Tool directories in priority order (cursor > aider > opencode)
            3. Default to "opencode" if nothing found
        """
        # Check environment override
        if tool := os.getenv("SITE_NINE_TOOL"):
            return tool.lower()
        
        # Walk up directory tree
        current = (start_path or Path.cwd()).resolve()
        
        while True:
            # Check each tool in priority order
            for tool_name in cls.TOOL_PRIORITY:
                tool_dir, _ = cls.TOOL_MARKERS[tool_name]
                if (current / tool_dir).exists():
                    return tool_name
            
            # Move up directory tree
            parent = current.parent
            if parent == current:
                # Reached root - default to opencode
                return "opencode"
            current = parent
    
    @classmethod
    def find_tool_dir(cls, tool_name: str, start_path: Path | None = None) -> Path | None:
        """Find tool directory by walking up from start_path.
        
        Args:
            tool_name: Tool to find ("opencode", "cursor", etc.)
            start_path: Starting directory
            
        Returns:
            Path to tool directory or None if not found
        """
        if tool_name not in cls.TOOL_MARKERS:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        tool_dir_name, _ = cls.TOOL_MARKERS[tool_name]
        current = (start_path or Path.cwd()).resolve()
        
        while True:
            tool_dir = current / tool_dir_name
            if tool_dir.exists() and tool_dir.is_dir():
                return tool_dir
            
            parent = current.parent
            if parent == current:
                return None
            current = parent
    
    @classmethod
    def get_adapter(cls, tool_name: str | None = None) -> ToolAdapter:
        """Get adapter for tool.
        
        Args:
            tool_name: Tool name (auto-detected if None)
            
        Returns:
            Tool adapter instance
            
        Raises:
            FileNotFoundError: If tool directory not found
        """
        # Auto-detect if not specified
        if not tool_name:
            tool_name = cls.detect_tool()
        
        # Find tool directory
        tool_dir = cls.find_tool_dir(tool_name)
        if not tool_dir:
            raise FileNotFoundError(
                f"No {tool_name} directory found. "
                f"Run 's9 init' or 's9 init --tool {tool_name}' to initialize."
            )
        
        # Get adapter class
        if tool_name not in cls._ADAPTERS:
            raise ValueError(f"No adapter registered for tool: {tool_name}")
        
        adapter_class = cls._ADAPTERS[tool_name]
        
        # Instantiate adapter
        return adapter_class(tool_dir)
    
    @classmethod
    def get_config(cls, tool_name: str | None = None) -> ToolConfig:
        """Get tool configuration.
        
        Args:
            tool_name: Tool name (auto-detected if None)
            
        Returns:
            Unified ToolConfig
        """
        adapter = cls.get_adapter(tool_name)
        return adapter.load_config()

# Register built-in adapters
ToolRegistry.register_adapter("opencode", OpenCodeAdapter)

# Cursor and Aider adapters registered when implemented
# ToolRegistry.register_adapter("cursor", CursorAdapter)
# ToolRegistry.register_adapter("aider", AiderAdapter)
```

---

## 7. Data Flow Diagrams

### Skill Execution Flow

```
User invokes skill
      │
      ▼
┌─────────────────┐
│  Tool Interface │ (OpenCode: skill(), Cursor: MCP, Aider: /cmd)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ToolAdapter    │ .load_skill(name)
└────────┬────────┘
         │
         ├─ Try skill.yaml (new format)
         └─ Fall back to SKILL.md (legacy)
         │
         ▼
┌─────────────────┐
│ SkillDefinition │ (parsed workflow)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ SkillExecutor   │ .execute(skill)
└────────┬────────┘
         │
         │ For each step:
         ├─ command  → Run subprocess, capture output
         ├─ output   → Render via SkillRenderer
         ├─ question → Ask via SkillRenderer
         └─ conditional → Evaluate and branch
         │
         ▼
┌─────────────────┐
│ SkillRenderer   │ (tool-specific)
└────────┬────────┘
         │
         ├─ OpenCode: print() to chat
         ├─ Cursor: MCP protocol
         └─ Aider: CLI output
         │
         ▼
    User sees output
```

### Configuration Loading Flow

```
Application starts
      │
      ▼
┌──────────────────┐
│  ToolRegistry    │ .detect_tool()
└────────┬─────────┘
         │
         ├─ Check SITE_NINE_TOOL env var
         ├─ Walk up directory tree
         └─ Find .cursor/ or .aider/ or .opencode/
         │
         ▼
    Tool detected (e.g., "cursor")
         │
         ▼
┌──────────────────┐
│  ToolRegistry    │ .get_adapter("cursor")
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  CursorAdapter   │ (instantiated)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  CursorAdapter   │ .load_config()
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│CursorConfigLoader│ .load(cursor.json)
└────────┬─────────┘
         │
         ├─ Parse cursor.json (MCP format)
         └─ Normalize to ToolConfig
         │
         ▼
┌──────────────────┐
│   ToolConfig     │ (unified model)
└────────┬─────────┘
         │
         ▼
Application uses ToolConfig
(tool-agnostic paths, commands, skills)
```

---

## 8. Sequence Diagrams

### Task Management with Adapter

```
User         CLI         TaskManager    ToolRegistry    Adapter      Database
 │           │               │              │             │             │
 ├─ s9 task list ────────────►│             │             │             │
 │           │               ├─ get_adapter()────────────►│             │
 │           │               │              ├─ detect_tool()            │
 │           │               │              │  (finds .opencode/)       │
 │           │               │              └────────────►│             │
 │           │               │              │  OpenCodeAdapter          │
 │           │               │◄─────────────┼─────────────┘             │
 │           │               │              │             │             │
 │           │               ├─ get_database_path() ──────►│             │
 │           │               │◄─────────────┼─────────────┘             │
 │           │               │  .opencode/data/project.db  │             │
 │           │               │              │             │             │
 │           │               ├─ SELECT * FROM tasks ──────────────────►│
 │           │               │◄────────────────────────────────────────┤
 │           │               │  [task rows]                             │
 │           │               │              │             │             │
 │           │◄──────────────┤              │             │             │
 │◄──────────┤  display table               │             │             │
```

---

## 9. Error Handling

### Error Hierarchy

```python
class SiteNineError(Exception):
    """Base exception for site-nine"""
    pass

class ToolError(SiteNineError):
    """Tool-related errors"""
    pass

class ToolNotFoundError(ToolError):
    """Tool directory not found"""
    pass

class ToolNotSupportedError(ToolError):
    """Tool not supported"""
    pass

class ConfigError(SiteNineError):
    """Configuration errors"""
    pass

class ConfigNotFoundError(ConfigError):
    """Config file not found"""
    pass

class ConfigInvalidError(ConfigError):
    """Config file invalid"""
    pass

class SkillError(SiteNineError):
    """Skill execution errors"""
    pass

class SkillNotFoundError(SkillError):
    """Skill not found"""
    pass

class SkillExecutionError(SkillError):
    """Skill execution failed"""
    pass
```

### Error Handling Strategy

1. **Graceful Degradation**: Optional features fail silently
2. **Clear Messages**: User-friendly error messages with next steps
3. **Logging**: Detailed logs for debugging
4. **Rollback**: Failed operations don't leave partial state

---

## 10. Testing Strategy

### Test Pyramid

```
           ┌────────────┐
           │  E2E Tests │  (5%)
           │  Full CLI  │
           └────────────┘
         ┌────────────────┐
         │Integration Tests│ (25%)
         │ Adapter + Core  │
         └────────────────┘
     ┌──────────────────────┐
     │     Unit Tests        │ (70%)
     │ Adapters, Executors   │
     └──────────────────────┘
```

### Test Coverage Requirements

- **Unit Tests**: 90%+ coverage
- **Integration Tests**: All adapter operations
- **E2E Tests**: Common workflows (task management, session start)
- **Backward Compat Tests**: All v1.x.x workflows

### Key Test Scenarios

1. **Adapter Tests**
   - OpenCodeAdapter loads config correctly
   - OpenCodeAdapter finds all paths
   - CursorAdapter maps MCP config to ToolConfig
   
2. **Skill Execution Tests**
   - Legacy SKILL.md conversion
   - New skill.yaml execution
   - Tool-specific rendering
   
3. **Backward Compatibility Tests**
   - Existing .opencode/ project works unchanged
   - All CLI commands produce same output
   - Skills execute identically

---

**End of Technical Design Document Part 2**
