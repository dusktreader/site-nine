# ADR-004: Skills System Refactoring for Tool-Agnostic Execution

**Status:** Proposed  
**Date:** 2026-02-03  
**Deciders:** Ptah (Architect)  
**Related Tasks:** ARC-H-0030, ADM-H-0029  
**Related ADRs:** ADR-001 (Adapter Pattern), ADR-002 (Cursor MCP), ADR-003 (Configuration System)

## Context

Site-nine's skills system is currently tightly coupled to OpenCode's skill invocation mechanism. Skills are invoked via `skill(name="session-start")` which only works in OpenCode. To support multiple tools, we need to refactor the skills system to separate:

1. **Skill logic** (what steps to perform) - tool-agnostic
2. **Skill presentation** (how to format/display) - tool-specific
3. **Skill invocation** (how skills are triggered) - tool-specific

### Current State

**Skills structure**:
```
.opencode/skills/
├── session-start/
│   └── SKILL.md          # Contains both logic AND OpenCode-specific formatting
├── session-end/
│   └── SKILL.md
├── handoff-workflow/
│   └── SKILL.md
├── task-management/
│   └── SKILL.md
└── tasks-report/
    └── SKILL.md
```

**Current skill format** (`.opencode/skills/session-start/SKILL.md`):
- YAML frontmatter with metadata
- Markdown content with instructions
- Bash commands (tool-agnostic)
- OpenCode-specific formatting (table layouts, UI elements)
- Mixed workflow logic and presentation

**Invocation**: `skill(name="session-start")` (OpenCode only)

**Problems**:
1. **Tool coupling**: Skills contain OpenCode-specific formatting and instructions
2. **No reusability**: Can't use skills in Cursor, Aider, or other tools
3. **Mixed concerns**: Workflow logic mixed with UI presentation
4. **Hard to test**: Can't test workflow logic separately from presentation
5. **Duplication risk**: Supporting multiple tools means duplicating skill logic

### Requirements

1. **Tool-agnostic core**: Workflow logic works in any tool
2. **Tool-specific rendering**: Each tool can customize presentation
3. **Backward compatibility**: Existing OpenCode skills must work unchanged
4. **Extensibility**: Easy to add new skills without tool-specific code
5. **Testability**: Workflow logic testable independently of presentation
6. **MCP compatibility**: Skills should map cleanly to Cursor MCP servers

## Decision

We will refactor skills using a **three-layer architecture**: Skill Definition → Skill Executor → Skill Renderer.

### Architecture Overview

```
┌────────────────────────────────────────────────────┐
│              Skill Definition (YAML)                │
│  {tool}/skills/session-start/skill.yaml            │
│  - name, description, metadata                      │
│  - steps: list of actions (tool-agnostic)          │
│  - data: expected inputs/outputs                    │
└──────────────────┬─────────────────────────────────┘
                   │ loaded by
                   ▼
        ┌──────────────────────┐
        │   Skill Executor      │  ◄── Core skill engine (tool-agnostic)
        │  - Parses skill def   │
        │  - Executes steps     │
        │  - Manages state      │
        └──────────┬────────────┘
                   │ delegates rendering to
         ┌─────────┴──────────┐
         │                    │
┌────────▼────────┐  ┌───────▼────────┐
│ OpenCodeRenderer│  │ CursorRenderer │
│ - Formats for   │  │ - Formats for  │
│   OpenCode UI   │  │   Cursor MCP   │
│ - Tables, MD    │  │ - MCP protocol │
└─────────────────┘  └────────────────┘
```

### Layer 1: Skill Definition (YAML)

**Tool-agnostic workflow specification**

**File**: `{tool}/skills/session-start/skill.yaml`

```yaml
name: session-start
version: "1.0"
description: Initialize a new agent session with role selection and daemon naming
category: session-management
compatibility:
  - opencode
  - cursor
  - aider

# Workflow steps (tool-agnostic)
steps:
  - id: show-dashboard
    type: command
    command: s9 dashboard
    description: Display project status and available tasks
    
  - id: present-status-summary
    type: output
    template: status-summary
    data:
      source: dashboard-output
    
  - id: get-role-selection
    type: question
    prompt: "Which role would you like me to assume?"
    options:
      type: command
      command: s9 agent roles
    validate: role-exists
    
  - id: suggest-daemon-name
    type: command
    command: s9 name suggest {role} --count 3
    description: Get unused daemon name suggestions
    
  - id: confirm-name
    type: question
    prompt: "Would you like to use {suggested_name}, or choose a different one?"
    
  - id: create-session-file
    type: command
    command: date +"%Y-%m-%d.%H:%M:%S"
    store: timestamp
    
  - id: register-agent
    type: command
    command: s9 agent start {name} --role {role} --task "session-start"
    store: agent_id
    
  - id: share-mythology
    type: output
    template: mythology-background
    data:
      name: "{name}"
      mythology: "{mythology}"
      
  - id: rename-tui-session
    type: command
    command: s9 agent rename-tui {name} {role}
    optional: true  # Only works in tools with TUI API
    
  - id: check-handoffs
    type: command
    command: ls {tool}/work/sessions/handoffs/*{role}.pending.md
    optional: true
    
  - id: show-role-dashboard
    type: command
    command: s9 dashboard --role {role}

# Output templates (tool-specific rendering)
templates:
  status-summary: |
    **📊 Project Status**
    
    | Metric           | Count |
    |------------------|-------|
    | Active agents    | {active_agents} |
    | Tasks in progress| {tasks_in_progress} |
    | Tasks completed  | {tasks_completed} |
    
  mythology-background: |
    📖 **A bit about me...**
    
    {mythology_text}
```

### Layer 2: Skill Executor (Core Engine)

**Tool-agnostic execution engine**

**File**: `src/site_nine/skills/executor.py`

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass
class SkillStep:
    """A single step in a skill workflow"""
    id: str
    type: str  # command, output, question, conditional
    config: dict[str, Any]
    optional: bool = False

@dataclass
class SkillDefinition:
    """Skill workflow definition"""
    name: str
    version: str
    description: str
    steps: list[SkillStep]
    templates: dict[str, str]
    
    @classmethod
    def from_yaml(cls, path: Path) -> "SkillDefinition":
        """Load skill definition from YAML"""
        with open(path) as f:
            data = yaml.safe_load(f)
        
        return cls(
            name=data["name"],
            version=data["version"],
            description=data["description"],
            steps=[SkillStep.from_dict(s) for s in data["steps"]],
            templates=data.get("templates", {}),
        )

class SkillExecutor:
    """Executes skill workflows in tool-agnostic manner"""
    
    def __init__(self, renderer: "SkillRenderer"):
        self.renderer = renderer
        self.state: dict[str, Any] = {}
    
    async def execute(self, skill_def: SkillDefinition) -> None:
        """Execute skill workflow"""
        for step in skill_def.steps:
            try:
                await self._execute_step(step, skill_def)
            except Exception as e:
                if not step.optional:
                    raise
                # Optional step failed, continue
    
    async def _execute_step(self, step: SkillStep, skill_def: SkillDefinition) -> None:
        """Execute a single workflow step"""
        if step.type == "command":
            await self._execute_command(step)
        elif step.type == "output":
            await self._execute_output(step, skill_def)
        elif step.type == "question":
            await self._execute_question(step)
        # ... other step types
    
    async def _execute_command(self, step: SkillStep) -> None:
        """Execute a command step"""
        command = step.config["command"].format(**self.state)
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if store_var := step.config.get("store"):
            self.state[store_var] = result.stdout.strip()
    
    async def _execute_output(self, step: SkillStep, skill_def: SkillDefinition) -> None:
        """Render output using tool-specific renderer"""
        template_name = step.config["template"]
        template = skill_def.templates[template_name]
        
        # Let renderer format for specific tool
        await self.renderer.render(template, self.state)
```

### Layer 3: Skill Renderer (Tool-Specific Presentation)

**Tool-specific output formatting**

**File**: `src/site_nine/adapters/opencode_renderer.py`

```python
class SkillRenderer(Protocol):
    """Protocol for tool-specific skill renderers"""
    
    async def render(self, template: str, data: dict[str, Any]) -> None:
        """Render template with data for specific tool"""
        ...
    
    async def ask_question(self, prompt: str, options: list[str]) -> str:
        """Present question to user in tool-specific way"""
        ...

class OpenCodeRenderer:
    """Renders skills for OpenCode (direct output)"""
    
    async def render(self, template: str, data: dict[str, Any]) -> None:
        """Render as markdown for OpenCode"""
        output = template.format(**data)
        print(output)  # Direct output to OpenCode
    
    async def ask_question(self, prompt: str, options: list[str]) -> str:
        """OpenCode-style question (waits for user response)"""
        print(prompt)
        for i, option in enumerate(options):
            print(f"{i+1}. {option}")
        # Wait for user input in chat
        return await get_user_response()

class CursorMCPRenderer:
    """Renders skills for Cursor MCP protocol"""
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp = mcp_client
    
    async def render(self, template: str, data: dict[str, Any]) -> None:
        """Send formatted output via MCP protocol"""
        output = template.format(**data)
        await self.mcp.send_message({
            "type": "skill-output",
            "content": output,
            "format": "markdown"
        })
    
    async def ask_question(self, prompt: str, options: list[str]) -> str:
        """Cursor-style question via MCP prompt"""
        response = await self.mcp.prompt({
            "type": "select",
            "message": prompt,
            "choices": options
        })
        return response.selected
```

### Skill Invocation (Tool-Specific)

**How skills are triggered varies by tool:**

**OpenCode**:
```python
# User types: skill(name="session-start")
# OpenCode calls: skill_tool.invoke("session-start")
```

**Cursor MCP**:
```python
# Exposed as MCP server tool
mcp_server.register_tool("s9-session-start", session_start_skill)
# User invokes via Cursor's MCP interface
```

**Aider**:
```python
# Aider slash command
# User types: /s9-session-start
# Aider calls: s9_command("session-start")
```

## Alternatives Considered

### Alternative 1: Keep Skills as Markdown, Add Tool-Specific Versions

**Approach**: Create separate skill files for each tool (e.g., `SKILL.opencode.md`, `SKILL.cursor.md`).

**Pros**:
- Simple to understand
- Easy to customize per tool
- No execution engine needed

**Cons**:
- **Massive duplication**: Workflow logic repeated in each file
- **Maintenance nightmare**: Updates need N file changes
- **Inconsistency risk**: Files drift apart over time
- **Not extensible**: Adding new tool means copying all skills

**Rejected because**: Violates DRY, unmaintainable at scale.

### Alternative 2: Embed Tool Logic in Skills

**Approach**: Add conditional logic in skills: `{% if tool == "opencode" %} ... {% endif %}`

**Pros**:
- Single skill file
- Template-based

**Cons**:
- **Skills become complex**: Logic littered with conditionals
- **Hard to read**: Nested conditionals confuse workflow
- **Limited flexibility**: Templates can't handle complex tool differences
- **Poor testability**: Can't test tool-specific branches easily

**Rejected because**: Skills become unreadable, hard to maintain.

### Alternative 3: Python-Based Skills (No YAML)

**Approach**: Write skills as Python classes with methods for each step.

**Pros**:
- Type safety
- IDE support
- Unit testable

**Cons**:
- **Less accessible**: Requires Python knowledge to create skills
- **Not user-editable**: Can't edit skills without code changes
- **Deployment complexity**: Skills need to be installed as code
- **Community barrier**: Higher bar for community skill contributions

**Rejected because**: Makes skills less accessible to non-developers.

### Alternative 4: Keep Current System, No Refactoring

**Approach**: Accept tool-specific skills, require tools to implement OpenCode-compatible skill format.

**Pros**:
- No refactoring needed
- Proven system

**Cons**:
- **Defeats multi-tool goal**: Other tools won't adopt OpenCode format
- **Not extensible**: Hard for tools with different paradigms
- **MCP incompatibility**: Doesn't map to MCP server model
- **Limits adoption**: Tools must bend to site-nine's format

**Rejected because**: Doesn't achieve goal of tool-agnostic system.

## Implementation Plan

### Phase 1: Skill Executor Core (Week 5)

1. **Create skill definition format**
   - Design YAML schema for skill definitions
   - Implement SkillDefinition dataclass
   - YAML parser and validator

2. **Implement SkillExecutor**
   - Core execution engine
   - Step types: command, output, question
   - State management

3. **Create SkillRenderer protocol**
   - Define renderer interface
   - Implement OpenCodeRenderer (wraps existing behavior)

### Phase 2: Refactor Existing Skills (Week 6)

1. **Convert skills to new format**
   - session-start → skill.yaml + templates
   - session-end → skill.yaml + templates
   - handoff-workflow → skill.yaml + templates
   - task-management → skill.yaml + templates
   - tasks-report → skill.yaml + templates

2. **Backward compatibility layer**
   - Support loading old SKILL.md format
   - Auto-convert to new format internally
   - Deprecation warning for old format

3. **Testing**
   - Test each converted skill
   - Validate output matches original
   - Test edge cases

### Phase 3: Cursor MCP Integration (Week 7)

1. **Implement CursorMCPRenderer**
   - MCP protocol integration
   - Format skills for MCP

2. **Create MCP Server**
   - Expose site-nine skills as MCP tools
   - Map skill invocations to MCP calls

3. **Testing**
   - Test skills in Cursor
   - Validate MCP protocol compliance

## Consequences

### Positive

- ✅ **Tool-agnostic**: Skills work in any tool
- ✅ **Maintainable**: Single source of truth for workflow logic
- ✅ **Extensible**: New tools add renderer, not duplicate skills
- ✅ **Testable**: Workflow logic unit testable
- ✅ **Community-friendly**: YAML easier than tool-specific formats
- ✅ **MCP-ready**: Clean mapping to MCP server model

### Negative

- ⚠️ **Migration required**: Existing skills need conversion
- ⚠️ **Added complexity**: Three-layer architecture vs simple markdown
- ⚠️ **YAML learning curve**: Users must learn YAML skill format

### Risks & Mitigation

| Risk | Mitigation |
|------|------------|
| YAML format too rigid for complex skills | Allow escape hatch to Python for advanced skills |
| Performance overhead from execution engine | Benchmark, optimize hot paths, async execution |
| Breaking existing skills | Backward compatibility layer, gradual deprecation |
| Renderer API insufficient for tool differences | Start minimal, extend based on real tool needs |

## Compliance

This decision supports:
- **ADR-001**: Skills use adapter pattern via renderers
- **ADR-002**: Enables Cursor MCP skill integration
- **ADR-003**: Uses ToolConfig for path resolution in skills
- **Project Goal**: Tool-agnostic skills for universal workflow system

## References

- ADR-001: Adapter Pattern
- ADR-002: Cursor MCP First Target
- ADR-003: Unified Configuration System
- Current skills: `.opencode/skills/*/SKILL.md`
- MCP specification: https://modelcontextprotocol.io/

## Notes

This ADR establishes the **skills refactoring strategy**. The three-layer architecture (Definition → Executor → Renderer) separates concerns cleanly:
- **Definitions**: What to do (tool-agnostic)
- **Executor**: How to execute (tool-agnostic)
- **Renderers**: How to present (tool-specific)

**Key Principle**: Workflow logic is tool-agnostic. Only presentation varies by tool.

**Migration Path**: Phase 1 builds infrastructure with backward compatibility. Phase 2 converts skills gradually. Phase 3 adds new tool support.

Next ADR:
- ADR-005: Backward compatibility strategy (comprehensive)
