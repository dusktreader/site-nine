# ADR-002: Target Tool Prioritization

**Status:** Proposed  
**Date:** 2026-02-03  
**Deciders:** Al-Lat (Administrator)  
**Related Tasks:** ARC-H-0030, ADM-H-0029  
**Related ADRs:** ADR-001 (Adapter Pattern)

## Context

After deciding to use the Adapter Pattern (ADR-001) for multi-tool support, we must prioritize which tools to target 
for our adapter implementations. The candidate tools are:

1. **GitHub Copilot CLI** - GitHub's command-line coding assistant
2. **Crush** - Emerging AI coding tool
3. **Claude Code** - Anthropic's coding tool (pending enterprise approval)

The prioritization will:
- Validate the adapter pattern design
- Establish patterns for future adapters
- Demonstrate feasibility of multi-tool support
- Provide working examples for community contributors

### Tool Comparison

| Criterion                  | GitHub Copilot CLI                    | Crush                           | Claude Code                      |
|----------------------------|---------------------------------------|---------------------------------|----------------------------------|
| **Availability**           | ✅ Publicly available now             | ✅ Available now                | ⚠️ Pending enterprise approval   |
| **Market Adoption**        | ✅ High (GitHub ecosystem)            | ⚠️ Growing/emerging             | ✅ Very High (Anthropic)         |
| **Documentation**          | ✅ GitHub documentation available     | ⚠️ Limited docs                 | ✅ Anthropic documentation available |
| **Extensibility API**      | ⚠️ Limited/closed ecosystem           | ❓ Unknown                      | ❓ Unknown                       |
| **Configuration**          | ⚠️ Limited config options             | ❓ Unknown                      | ❓ Unknown                       |
| **Testing Feasibility**    | ✅ Can test immediately               | ✅ Can test immediately         | ❌ No access yet                 |
| **Risk Level**             | ✅ Low (stable, established)          | ⚠️ Medium (emerging tool)       | ⚠️ High (unreleased, may change) |

## Decision

We will implement adapters in the following priority order:

1. **GitHub Copilot CLI** (First Target)
2. **Crush** (Second Target)
3. **Claude Code** (Third Target - when available)

**Important**: This prioritization is pragmatic, not dogmatic. **If Claude Code becomes available before we begin the 
Crush adapter, we will implement Claude Code second instead of Crush.** The current order is based on availability; 
access changes the priority.

### Rationale

**Priority 1: GitHub Copilot CLI**

1. **Immediate Availability**
   - Tool is publicly available and stable
   - Can begin implementation and testing immediately
   - No access barriers or approval delays

2. **Market Validation**
   - Large existing user base in GitHub ecosystem
   - Proven production tool, not experimental
   - Strong GitHub integration and backing

3. **Risk Mitigation**
   - Well-documented tool with established APIs
   - Lower risk of breaking changes
   - Provides stable foundation for adapter pattern validation

4. **Adapter Pattern Validation**
   - Real-world complexity without experimental tool risk
   - Establishes baseline patterns for future adapters
   - Tests adapter abstraction with production tool

**Priority 2: Crush**

1. **Availability**
   - Currently accessible for testing and development
   - Can validate adapter pattern with second tool
   - No approval gates blocking progress

2. **Validation of Adapter Flexibility**
   - Different tool paradigm from Copilot CLI
   - Tests adapter pattern's flexibility across diverse tools
   - Reveals any abstraction gaps not caught by first adapter
   - **Proving ground, not a commitment** - if Crush adapter proves too difficult or costly to implement, we may 
     abandon it; the value is in testing the pattern, not necessarily shipping Crush support

3. **Emerging Tool Support**
   - Early support for emerging tools demonstrates site-nine's versatility
   - Community value in supporting newer tools
   - Lower user base means lower risk if implementation issues arise or we abandon the adapter

**Priority 3: Claude Code**

1. **Access Constraints**
   - Currently unavailable (pending enterprise approval)
   - Cannot design or test against it yet
   - Risk of significant changes before public release

2. **Learning from Prior Adapters**
   - By the time access is granted, we'll have two working adapters
   - Can apply lessons learned from Copilot CLI and Crush
   - More mature adapter pattern to build against

3. **Strategic Value**
   - Anthropic tool may have strong integration potential
   - Enterprise approval suggests future organizational support
   - Worth waiting for rather than building blind

## Implementation Plan

### Phase 1: Copilot CLI Adapter (First Implementation)

1. **CopilotAdapter Implementation**
   - Implement ToolAdapter protocol for Copilot CLI
   - Research Copilot CLI's directory structure and config
   - Map site-nine concepts to Copilot CLI equivalents

2. **Configuration System**
   - Support Copilot CLI config format
   - Implement path resolution for Copilot CLI directories
   - Test multi-project scenarios

3. **Testing & Validation**
   - Manual testing protocol (no integration tests possible)
   - Smoke test checklist for core functionality
   - Real-world validation with Copilot CLI
   - Document limitations and workarounds

4. **Success Criteria**
   - ✅ Copilot CLI users can run `s9 init`
   - ✅ Task management works in Copilot CLI context
   - ✅ Agent sessions tracked properly
   - ✅ Zero OpenCode regressions
   - ✅ Adapter pattern validated for basic functionality

### Phase 2: Crush Adapter (Second Implementation)

1. **CrushAdapter Implementation**
   - Apply lessons learned from Copilot CLI adapter
   - Implement ToolAdapter protocol for Crush
   - Research Crush's architecture and integration points

2. **Pattern Refinement**
   - Identify common patterns between first two adapters
   - Refactor shared code into base classes if needed
   - Update ToolAdapter protocol if gaps discovered

3. **Testing & Documentation**
   - Apply testing protocol from Copilot CLI
   - Document Crush-specific setup and configuration
   - Create comparison guide (Copilot CLI vs Crush differences)

4. **Success Criteria**
   - ✅ Both Copilot CLI and Crush adapters work
   - ✅ Common patterns identified and documented
   - ✅ Adapter pattern proven flexible across tools
   - ✅ Community contribution guide updated with lessons

### Phase 3: Claude Code Adapter (When Available)

1. **Access & Research**
   - Wait for enterprise approval and access
   - Research Claude Code architecture and APIs
   - Evaluate any unique integration opportunities

2. **ClaudeCodeAdapter Implementation**
   - Apply mature adapter pattern from prior implementations
   - Leverage any Anthropic-specific features
   - Implement with confidence from prior experience

3. **Success Criteria**
   - ✅ All three adapters working
   - ✅ Adapter pattern fully validated
   - ✅ Multi-tool support demonstrated
   - ✅ Community has three adapter examples

## Alternatives Considered

### Alternative 1: Wait for Claude Code First

**Pros**:
- Anthropic tool may have best integration potential
- Potential for official Anthropic support

**Cons**:
- **Blocks all progress** - can't start until access granted
- **Unknown timeline** - enterprise approval could take months
- **Risk of vaporware** - tool may change significantly or be cancelled
- **Missed opportunities** - can't validate adapter pattern or help current users

**Rejected because**: Cannot block entire multi-tool effort on unavailable tool with unknown timeline.

### Alternative 2: Build All Three Simultaneously

**Pros**:
- Faster to multi-tool support
- Validates adapter pattern across all tools at once
- Reveals abstraction issues earlier

**Cons**:
- **Resource-intensive** - requires parallel development effort
- **Cannot test Claude Code** - don't have access yet
- **Higher risk** - if adapter pattern wrong, affects all three implementations
- **Slower learning** - can't apply lessons from first adapter to others

**Rejected because**: Sequential implementation allows learning and iteration, which is **essential** for building 
robust adapters. Each adapter implementation will teach us critical lessons about the pattern, tool integration 
challenges, and edge cases. Attempting parallel implementation would mean making the same mistakes three times instead 
of learning from each one. Also, Claude Code access blocks simultaneous approach.

### Alternative 3: Crush First, Then Copilot CLI

**Pros**:
- Support emerging tool first
- Different from Copilot CLI (more diversity)

**Cons**:
- **Higher risk starting point** - emerging tool may have stability issues
- **Less documentation** - harder to debug issues
- **Smaller user base** - fewer users benefit from first adapter
- **Riskier validation** - if issues arise, unclear if problem is our adapter or the tool

**Rejected because**: Copilot CLI's stability and documentation make it safer for validating adapter pattern. Once 
pattern is proven with Copilot CLI, Crush implementation will be lower risk.

## Consequences

### Positive

- ✅ **Clear roadmap** - team knows implementation order and can plan accordingly
- ✅ **Progressive validation** - each adapter validates and refines the pattern
- ✅ **Risk management** - start with stable tool, progress to experimental
- ✅ **Sequential learning is essential** - lessons from each adapter directly improve the next; this is not optional, 
  it's the core strategy for building robust adapters
- ✅ **User value delivered early** - Copilot CLI users benefit first (large user base)
- ✅ **No blockers** - work can start immediately on available tools

### Negative

- ⚠️ **Delayed Claude Code support** - users wanting Claude Code must wait
- ⚠️ **Sequential timeline** - slower than parallel implementation
- ⚠️ **Potential rework** - Claude Code may reveal adapter pattern gaps requiring changes to prior adapters

### Risks & Mitigation

| Risk                                                     | Impact | Probability | Mitigation                                                                         |
|----------------------------------------------------------|--------|-------------|------------------------------------------------------------------------------------|
| Copilot CLI adapter reveals fundamental pattern flaws    | High   | Low         | Copilot CLI is similar enough to OpenCode; pattern designed with multi-tool in mind |
| Crush adapter proves too difficult to implement          | Low    | Medium      | Crush is a proving ground, not a commitment; may abandon if adapter proves infeasible; already have Copilot CLI working |
| Crush adapter implementation stalls due to lack of docs  | Medium | Medium      | Community research, trial-and-error, document findings as we go; abandon if cost exceeds value |
| Claude Code never gets approved/released                 | Medium | Medium      | Roadmap already includes two working adapters; Claude Code is bonus, not requirement |
| Adapter pattern changes break completed adapters         | Medium | Low         | Comprehensive manual testing protocol per adapter; version adapters independently   |

### Future Opportunities

After all three adapters:
- **Additional tools** - pattern for adding more tools to the codebase established
- **Tool comparison guides** - first-hand experience enables honest tool comparisons
- **Adapter maturity** - proven patterns for building robust tool adapters

**Note**: All adapters are first-class citizens of the site-nine codebase. Community-contributed adapters or adapter 
marketplaces are not part of this roadmap.

## Compliance

This decision supports:
- **ADR-001**: Uses adapter pattern as designed with sequential validation strategy
- **Project Goal**: Multi-tool support with pragmatic prioritization
- **Risk Management**: Start stable, progress to experimental
- **User Benefit**: Deliver value to large user base first, expand from there

## References

- ADR-001: Adapter Pattern for Tool Abstraction
- Task ARC-H-0030: Architecture design task
- Task ADM-H-0029: Research findings on tool-agnostic architecture
- GitHub Copilot CLI Documentation: https://docs.github.com/en/copilot/github-copilot-in-the-cli

## Notes

This ADR establishes **priority order**, not **scope limitation**. All three tools are targets; this defines the 
sequence. The adapter pattern (ADR-001) is designed to support multiple tools - this ADR simply establishes the 
implementation order based on availability, risk, and learning opportunities.

**Key Insight**: Sequential implementation allows each adapter to inform and improve the next, reducing risk while 
maximizing learning. Starting with Copilot CLI (stable, documented) provides solid foundation for the second adapter 
(Crush or Claude Code, depending on access) and third adapter.

Next ADRs:
- ADR-003: Configuration system design
- ADR-004: Skills refactoring approach
- ADR-005: Backward compatibility strategy
