# ADR-002: Cursor MCP as First Multi-Tool Target

**Status:** Proposed  
**Date:** 2026-02-03  
**Deciders:** Ptah (Architect)  
**Related Tasks:** ARC-H-0030, ADM-H-0029  
**Related ADRs:** ADR-001 (Adapter Pattern)

## Context

After deciding to use the Adapter Pattern (ADR-001) for multi-tool support, we must choose which tool to target first for our proof-of-concept adapter. The main candidates are:

1. **Cursor** (with MCP - Model Context Protocol)
2. **Aider** (CLI-based coding assistant)
3. **GitHub Copilot CLI**
4. **Claude Code** (Anthropic's coding tool)

The first target will:
- Validate the adapter pattern design
- Establish patterns for future adapters
- Demonstrate feasibility of multi-tool support
- Provide a working example for community contributors

### Tool Comparison

| Criterion | Cursor MCP | Aider | GitHub Copilot CLI | Claude Code |
|-----------|------------|-------|-------------------|-------------|
| **Market Adoption** | High (VSCode fork, popular) | Medium (CLI power users) | High (GitHub ecosystem) | Low (new, invite-only) |
| **Extensibility API** | ✅ MCP (Model Context Protocol) | ⚠️ Limited plugin system | ❌ Closed ecosystem | ❓ Unknown (beta) |
| **Session Management** | ✅ Built-in with API | ⚠️ File-based only | ❌ Not exposed | ❓ Unknown |
| **Skill System** | ✅ MCP servers (standardized) | ❌ No equivalent | ❌ No equivalent | ❓ Unknown |
| **Documentation** | ✅ Excellent MCP docs | ✅ Good CLI docs | ⚠️ Limited | ❌ Beta/NDA |
| **Open Standard** | ✅ MCP is open protocol | ⚠️ Aider-specific | ❌ Proprietary | ❓ Unknown |
| **Similarity to OpenCode** | ✅ Closest (IDE integration) | ⚠️ Different paradigm | ⚠️ Different paradigm | ❓ Unknown |
| **Configuration** | ✅ JSON config files | ✅ YAML config | ⚠️ Limited config | ❓ Unknown |

## Decision

We will implement **Cursor MCP adapter** as our first multi-tool target.

### Rationale

**Primary Reasons:**

1. **MCP is an Open Standard**
   - Model Context Protocol is Anthropic's open specification
   - Other tools (including future ones) may adopt MCP
   - Building for MCP means we can support multiple MCP-compatible tools
   - Future-proof investment

2. **Strong API & Extensibility**
   - MCP defines clear server protocol for skills/tools
   - Session management API available
   - Configuration system well-documented
   - Closest API match to OpenCode's feature set

3. **Market Validation**
   - Cursor has significant market adoption
   - Active community and development
   - VSCode-based (familiar to many developers)
   - Proven production tool, not experimental

4. **Technical Feasibility**
   - MCP servers can directly map to site-nine skills
   - Configuration format similar to OpenCode
   - Directory structure mappable (`.cursor/` ↔ `.opencode/`)
   - API surface area well-defined

**Secondary Reasons:**

5. **Adapter Pattern Validation**
   - Cursor is different enough from OpenCode to stress-test our abstraction
   - MCP protocol forces clean interface design
   - Will expose any adapter API gaps early

6. **Community Benefit**
   - Many developers use Cursor
   - MCP adapter example helps community build other adapters
   - Demonstrates site-nine's tool-agnostic vision

## Alternatives Considered

### Alternative 1: Aider First

**Pros**:
- Simpler architecture (CLI-only, no IDE integration)
- Excellent documentation
- Clear scope (less surface area than Cursor)
- Good for validating basic adapter pattern

**Cons**:
- **No skill system equivalent** - hard to map site-nine skills
- **Different paradigm** (CLI vs IDE) - less similar to OpenCode
- **Smaller market** - fewer users to benefit
- **Not extensible** - no plugin API means limited site-nine integration
- **Doesn't validate full adapter** - too simple, won't expose edge cases

**Rejected because**: Aider is too different from OpenCode (CLI vs IDE) and lacks extensibility APIs that would validate our adapter design. It's a weaker proof-of-concept.

### Alternative 2: GitHub Copilot CLI First

**Pros**:
- Massive user base
- GitHub integration
- Microsoft backing

**Cons**:
- **Closed ecosystem** - no public extensibility API
- **No skill system** - can't integrate site-nine workflows
- **Limited configuration** - hard to customize
- **No session management API** - can't track agent sessions
- **Proprietary** - dependent on Microsoft's roadmap

**Rejected because**: GitHub Copilot CLI doesn't expose enough APIs to integrate site-nine functionality. We'd be severely limited in what we could adapt.

### Alternative 3: Claude Code First

**Pros**:
- Built by Anthropic (MCP creators)
- May have native MCP support
- Cutting-edge features

**Cons**:
- **Beta/invite-only** - not publicly available
- **Unknown API surface** - can't design against it yet
- **Immature** - too early in lifecycle
- **Risky** - may change significantly before public release

**Rejected because**: Can't design for a tool that's not publicly available. Better to start with proven tools and add Claude Code later when it's released.

### Alternative 4: Multiple Tools Simultaneously

**Pros**:
- Validates adapter pattern across multiple tools at once
- Faster path to multi-tool support
- Reveals abstraction issues earlier

**Cons**:
- **Resource-intensive** - requires parallel development
- **Complexity** - hard to iterate on adapter API while building multiple adapters
- **Higher risk** - if adapter pattern is wrong, affects all implementations
- **Slower learning** - can't apply lessons from first adapter to second

**Rejected because**: Adapter pattern is new. Need to validate with one implementation, learn lessons, refine API, then scale to others. Sequential is safer than parallel.

## Implementation Plan

### Phase 1: Cursor Adapter Foundation (Week 3)

1. **MCP Protocol Integration**
   - Implement MCP client in site-nine
   - Connect to Cursor MCP servers
   - Test basic server communication

2. **CursorAdapter Implementation**
   - Implement ToolAdapter protocol for Cursor
   - Map `.opencode/` paths to `.cursor/` equivalents
   - Handle Cursor-specific configuration

3. **Skill Mapping**
   - Map site-nine skills to MCP server format
   - Implement skill invocation via MCP protocol
   - Test skill execution in Cursor

### Phase 2: Cursor Integration Testing (Week 4)

1. **Session Management**
   - Integrate Cursor session API
   - Test agent session tracking
   - Validate session file format

2. **Configuration System**
   - Support `cursor.json` config format
   - Implement path resolution for `.cursor/` directory
   - Test multi-project scenarios

3. **User Testing**
   - Recruit Cursor users for beta testing
   - Gather feedback on integration
   - Iterate on adapter implementation

### Success Criteria

- ✅ Cursor users can run `s9 init` and get `.cursor/` directory structure
- ✅ Site-nine skills work in Cursor via MCP
- ✅ Agent sessions tracked across Cursor sessions
- ✅ Task management works identically in Cursor vs OpenCode
- ✅ Zero OpenCode regressions
- ✅ Adapter pattern validated for extensibility

## Consequences

### Positive

- ✅ **MCP investment pays dividends** - future MCP-compatible tools get free support
- ✅ **Strong proof-of-concept** - validates adapter pattern with real-world complexity
- ✅ **Large user base** - many Cursor users can benefit immediately
- ✅ **Open protocol** - not locked into proprietary APIs
- ✅ **Community examples** - MCP adapter becomes template for others

### Negative

- ⚠️ **MCP learning curve** - team must learn MCP protocol
- ⚠️ **Cursor-specific quirks** - may discover Cursor MCP implementation issues
- ⚠️ **API stability risk** - Cursor MCP implementation may evolve
- ⚠️ **Complexity** - MCP is more complex than simpler tools like Aider

### Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Cursor MCP API changes breaking adapter | High | Medium | Version adapter, maintain compatibility matrix |
| MCP protocol too complex for site-nine needs | High | Low | Start minimal, implement only needed MCP features |
| Cursor user adoption low | Medium | Low | Strong documentation, example projects, support |
| Adapter pattern inadequate for MCP | High | Low | Phase 1 is validation phase, can iterate on API |

### Future Opportunities

After Cursor MCP adapter:
- **Aider Adapter** (Week 7-8): Simpler CLI-based adapter
- **Other MCP Tools**: Any future MCP-compatible tools get automatic support
- **Custom MCP Servers**: Community can build site-nine MCP servers
- **MCP Ecosystem**: Site-nine becomes part of growing MCP ecosystem

## Compliance

This decision supports:
- **ADR-001**: Uses adapter pattern as designed
- **Project Goal**: Multi-tool support starting with high-impact target
- **User Benefit**: Large Cursor user base gains site-nine workflows
- **Technical Excellence**: Validates abstraction with real-world complexity

## References

- ADR-001: Adapter Pattern for Tool Abstraction
- MCP Documentation: https://modelcontextprotocol.io/
- Cursor Documentation: https://docs.cursor.com/
- Task ARC-H-0030: This architecture design task
- Task ADM-H-0029: Research findings

## Notes

This ADR establishes Cursor MCP as **first target**, not **only target**. The adapter pattern (ADR-001) is designed to support multiple tools. After validating the pattern with Cursor, we'll implement Aider adapter (simpler CLI case) and then others based on community demand.

**Key Insight**: Choosing Cursor MCP isn't just about Cursor - it's about betting on MCP as an open protocol that will enable wider ecosystem adoption.

Next ADRs:
- ADR-003: Configuration system design
- ADR-004: Skills refactoring approach
- ADR-005: Backward compatibility strategy
