# ADR-012: Subagent Delegation for Session Initialization

**Status:** PROPOSED
**Date:** 2026-02-16
**Deciders:** Tucker (Director), Aruru (Architect)
**Related Tasks:** ARC-H-0131
**Related Skills:** possession-start

## Context

The `possession-start` skill currently performs all initialization steps within the main agent's context, including:

1. **Dashboard display** - Project status overview
2. **Daemon selection/creation** - Auto-selecting from suggestions or using --daemon flag
3. **Bio generation** - Researching mythology and crafting whimsical first-person narrative (if missing)
4. **Possession registration** - Creating possession record and generating codename
5. **Session renaming** - UUID generation and TUI session title update
6. **Handoff checking** - Querying and reviewing pending handoffs
7. **Review checking** - Administrator-only, checking pending reviews
8. **Dashboard filtering** - Showing role-specific task view
9. **Auto-assignment** - Claiming and starting work on tasks (if --auto-assign or --task flags used)

### The Primary Problem: Context Pollution

**The core issue is not token cost - it's context pollution.**

When possession-start completes, the main agent's context is cluttered with initialization artifacts that are irrelevant to actual work:

**Bio Generation Pollution:**
- Mythology research: "Aruru is the Mesopotamian goddess who created Enkidu..."
- Multiple drafting attempts: "Let me craft a whimsical bio..." 
- Creative iteration noise
- Database save confirmations
- **Impact:** Agent spends entire session carrying mythology facts it will never use again

**Operational Noise:**
- UUID generation debug output: `session-marker-2d78f77df6f043d2`
- Database operation confirmations: "Possession #115 created"
- File path details: `.opencode/work/possessions/2026-02-16.20:55:57...`
- Session rename logs
- **Impact:** First ~4,000 tokens of context are setup noise, not work context

**Possession File Initialization (Epic-scoped):**
- Epic query results (all task details)
- Task list formatting
- File structure decisions
- **Impact:** Agent carries epic metadata when it only needs current task

### The Core Insight

**After possession-start completes, the Director only needs the agent to:**
1. Know who they are (daemon name, role)
2. Know their possession (codename, objective)
3. See available work (dashboard results)
4. Start working (clean context)

**They DON'T need the agent to carry:**
- How the bio was generated
- Why that mythology was interesting
- What UUID was created for session renaming
- How the possession file was structured

**Subagents solve this by discarding their context after completion.**

### Context Pollution Measurements

Based on actual analysis from this session (possession #115):

**Current Session Initialization Context Pollution:**
- First-time daemon: ~3,850 tokens total
  - Bio generation noise: ~600 tokens (mythology research, creative iteration, save confirmations)
  - Operational noise: ~200 tokens (UUIDs, database confirmations, file paths)
  - Useful context: ~3,050 tokens
- Existing daemon: ~3,250 tokens total
  - Operational noise: ~200 tokens
  - Useful context: ~3,050 tokens

**With Subagent Delegation:**
- Bio generation: 600 tokens of noise (in subagent, discarded) → 150 tokens of result (useful)
- Possession file init: 800 tokens of noise (in subagent, discarded) → 50 tokens of result (useful)

**Context Cleanliness Improvement:**
- First-time daemon: ~1,200 tokens of noise removed from main context (450 tokens of research noise eliminated)
- Epic-scoped possession: ~1,800 tokens of noise removed from main context (750 tokens of operational noise eliminated)

**The value is that the agent starts work with a clean, focused context - not carrying irrelevant initialization artifacts.**

### Existing Subagent Capabilities

OpenCode already has `Task` tool for delegating work to subagents:
- `general` - General-purpose for complex multi-step tasks
- `explore` - Fast codebase exploration

Subagents:
- Run in isolated context
- Return summary results to main agent
- **Context is discarded after completion** (this is the key feature!)
- Can be invoked in parallel for independent work

## Decision

We will **selectively use subagents for initialization steps that pollute context** while keeping the core possession-start flow in the main agent.

### Core Principles

1. **Context cleanliness over token savings**: Primary goal is clean working context for actual work
2. **Selective delegation**: Only delegate steps that:
   - Generate significant context noise (research, iteration, operational details)
   - Are self-contained (don't require Director decisions)
   - Produce compact results (Director only needs summary)

2. **Keep flow in main agent**: Possession-start logic stays in main agent because:
   - Director may need to make decisions (daemon conflicts, task selection)
   - Flow control is contextual (flags, conditions, errors)
   - Most steps are already efficient (~100-200 tokens)

3. **Parallel where possible**: Independent subagent work can happen simultaneously

4. **Graceful degradation**: If subagent fails, main agent can fall back to direct execution

### Subagent Delegation Points

#### 1. Bio Generation (DELEGATE - if missing)

**Trigger:** Daemon exists but `bio IS NULL`

**Current cost:** ~600 tokens (research + craft + save)

**Subagent approach:**
```bash
# Main agent detects missing bio
Task(
  subagent_type="general",
  description="Generate daemon bio",
  prompt="""
  Generate and save a whimsical first-person bio for daemon 'aruru' (Mesopotamian, Architect role).
  
  Requirements:
  - Research: Aruru is the Mesopotamian goddess who created Enkidu from clay
  - Style: 3-5 sentences, whimsical, first-person, relevant to role
  - Save: Use the daemon_set_bio tool: daemon_set_bio({ name: "aruru", bio: "<bio-text>" })
  
  Return ONLY the bio text (not the command output).
  """
)
```

**Return to main agent:**
```
I am Aruru, the Mesopotamian mother goddess who shaped Enkidu from clay...
[rest of bio - 2-3 sentences]
```

**Context cleanliness:**
- Process noise: 600 tokens (research, iteration, database ops) - discarded in subagent
- Result in main: 150 tokens (just the bio text)
- Context pollution eliminated: ~450 tokens of mythology research and creative process

**Main agent displays:**
```
A bit about me...

[Bio text from subagent]
```

#### 2. Possession File Initial Documentation (DELEGATE - if --epic or complex scope)

**Trigger:** Possession started with --epic flag or complex multi-task objective

**Current cost:** Possession file created but empty (~200 tokens), updates would add more

**Subagent approach:**
```bash
# After possession registration, if epic-scoped
Task(
  subagent_type="general",
  description="Initialize possession file",
  prompt="""
  Initialize possession file for possession #115 (omega-nexus).
  
  Context:
  - Daemon: aruru (Architect)
  - Epic: EPC-H-0004 (Multi-Tool Adapter System)
  - Possession file: .opencode/work/possessions/2026-02-16.12:56:14.architect.aruru.omega-nexus.md
  
  Tasks:
  1. Read epic details: `s9 epic show EPC-H-0004`
  2. Read available tasks: `s9 task list --epic EPC-H-0004 --role Architect`
  3. Update possession file with:
     - Epic overview
     - Task list with status
     - Initial approach notes
  
  Return: "Possession file initialized with [N] tasks from epic EPC-H-0004"
  """
)
```

**Context cleanliness:**
- Process noise: ~800 tokens (epic queries with full task details, formatting decisions, file writes) - discarded in subagent
- Result in main: ~50 tokens (simple confirmation message)
- Context pollution eliminated: ~750 tokens of epic metadata and task lists

**Trade-off:** Only worth it for epic-scoped possessions where there's significant context to delegate, not simple task claims

#### 3. What STAYS in Main Agent

**Daemon selection** (~200 tokens):
- Director might need to make decisions (conflicts, clarifications)
- Needs to show suggestions to Director
- Already efficient

**Possession registration** (~200 tokens):
- Quick database operation
- Result needed immediately for subsequent steps
- Already efficient

**Session renaming** (~200 tokens):
- Quick operation
- Confirmation visible to Director
- Already efficient

**Handoff checking** (~150 tokens):
- May require Director interaction
- May need follow-up questions
- Already efficient

**Dashboard display** (~400-1,500 tokens):
- Director needs to see this
- Informs decisions about what to work on
- Can't be delegated

**Auto-assignment** (varies):
- Leads directly into work (stays in context)
- Can't be delegated without losing context

### Subagent Interface Contract

**Bio Generation Subagent:**
```python
Input: {
  "daemon_name": str,
  "role": str,
  "mythology": str,
  "description": str
}

Tasks:
1. Research mythology and daemon background
2. Craft 3-5 sentence first-person bio
3. Save with: daemon_set_bio tool
4. Return bio text only

Output: str  # Just the bio text
```

**Possession File Initialization Subagent:**
```python
Input: {
  "possession_id": int,
  "codename": str,
  "daemon_name": str,
  "role": str,
  "epic_id": str | None,
  "possession_file_path": str
}

Tasks:
1. Query epic details (if epic_id)
2. Query available tasks
3. Write initial possession file structure
4. Return confirmation

Output: str  # "Possession file initialized with [N] tasks"
```

### Updated Possession-Start Flow

```
Step 1: Dashboard (MAIN AGENT)
  └─> possession_dashboard

Step 2: Daemon Selection (MAIN AGENT)
  └─> daemon_suggest [Role]
  └─> Auto-select or use --daemon flag

Step 3: Check Bio (MAIN AGENT + SUBAGENT)
  ├─> daemon_show <daemon>
  ├─> IF bio IS NULL:
  │   └─> SUBAGENT: Generate and save bio (parallel with Step 4-6)
  └─> IF bio EXISTS: Display immediately

Step 4: Possession Registration (MAIN AGENT)
  └─> possession_init + possession_role_record + possession_daemon_record

Step 5: Session Rename (MAIN AGENT)
  └─> possession_rename_session

[PARALLEL: Bio subagent completes, main agent displays result]

Step 6: Possession File Init (CONDITIONAL SUBAGENT)
  ├─> IF --epic flag:
  │   └─> SUBAGENT: Initialize possession file with epic context
  └─> ELSE: Skip (simple possession)

Step 7: Handoffs (MAIN AGENT)
  └─> s9 handoff list --role [Role]

Step 8: Reviews (MAIN AGENT - Admin only)
  └─> s9 review list --status pending

Step 9: Dashboard (MAIN AGENT)
  └─> possession_dashboard

Step 10: Auto-Assign (MAIN AGENT)
  └─> IF --auto-assign or --task: Claim and start work
```

### Context Pollution Impact Analysis

**Scenario 1: First-time daemon, task-scoped possession**
- Current: 3,850 tokens (600 tokens of bio research noise)
- Proposed: 3,400 tokens (bio noise eliminated)
- Context pollution reduced: ~450 tokens of mythology research and creative iteration

**Scenario 2: Existing daemon, task-scoped possession**
- Current: 3,250 tokens
- Proposed: 3,250 tokens (no bio needed, no delegation)
- Context pollution reduced: 0 tokens (already clean)

**Scenario 3: First-time daemon, epic-scoped possession**
- Current: 4,650 tokens (600 bio noise + 800 possession file noise)
- Proposed: 2,850 tokens (both noise sources eliminated)
- Context pollution reduced: ~1,400 tokens of research, queries, and operational details

**Scenario 4: Existing daemon, epic-scoped possession**
- Current: 4,050 tokens (800 tokens of possession file noise)
- Proposed: 3,300 tokens (possession file noise eliminated)
- Context pollution reduced: ~750 tokens of epic queries and task list formatting

### When Delegation Triggers

**Bio Generation Subagent:**
- ✅ Trigger: `bio IS NULL` after daemon show
- ✅ Skip: `bio IS NOT NULL` (already exists)
- ✅ Parallel: Can run while Steps 4-5 execute
- ✅ Blocking: Main agent waits to display result before Step 7

**Possession File Subagent:**
- ✅ Trigger: `--epic` flag present
- ✅ Skip: Task-scoped or general possessions (minimal context needed)
- ✅ Parallel: Can run after Step 5
- ✅ Non-blocking: Main agent continues to Steps 7-9 while subagent works

## Alternatives Considered

### Alternative 1: Delegate Entire Possession-Start to Subagent

**Approach:** Main agent immediately delegates to subagent, receives final summary.

**Pros:**
- Maximum context cleanliness (entire initialization process in subagent context)
- Main agent gets ultra-compact result
- Clear separation of initialization vs. work

**Cons:**
- Loses Director interaction during initialization
- Can't handle --daemon conflicts or decisions
- Can't show progress (Director sees nothing until complete)
- Flags (--auto-assign, --task, --daemon) harder to handle
- Error handling more complex
- Session rename may not work (TUI session detection)

**Rejected because:** Possession-start has decision points that require Director visibility and interaction. The value is in selective delegation of noisy sub-steps, not wholesale outsourcing.

### Alternative 2: Keep Everything in Main Agent (Status Quo)

**Approach:** No subagent delegation, all work in main agent context.

**Pros:**
- Simple, no new patterns
- All context visible for debugging
- No coordination complexity

**Cons:**
- Context pollution from bio generation (~450 tokens of mythology research)
- Epic possession initialization accumulates query noise (~750 tokens)
- Main context polluted with operational details
- No parallelization opportunities
- Agent carries irrelevant artifacts into actual work

**Rejected because:** Bio generation clearly pollutes context with research that's never needed again. Epic possessions would benefit from delegating file initialization noise.

### Alternative 3: Pre-generate All Bios

**Approach:** Run batch script to generate bios for all 256 daemons upfront.

**Pros:**
- No runtime bio generation cost
- Consistent bio quality
- All daemons ready to use

**Cons:**
- Upfront context cost: 256 daemons × 600 tokens = ~153,600 tokens of wasted effort
- Quality varies (bulk generation less thoughtful)
- No agent review or iteration
- Daemons never used still cost effort
- Can't incorporate new mythologies without re-running batch

**Rejected because:** Lazy generation is more efficient overall. Most daemons won't be used. Current approach generates bios just-in-time with full context and care. This doesn't solve the pollution problem - it just front-loads it.

### Alternative 4: Cache Possession-Start Results

**Approach:** Cache entire possession-start output, replay for subsequent sessions.

**Pros:**
- Zero context cost for repeated summons
- Instant initialization
- Consistent experience

**Cons:**
- Stale data (dashboards change, tasks complete)
- No handling of new flags or contexts
- Cache invalidation complexity
- Doesn't help first-time initialization
- Director sees outdated project state

**Rejected because:** Session-start must reflect current project state. Dashboards, handoffs, and available tasks change constantly. Caching would provide stale information.

### Alternative 5: Compress Dashboards

**Approach:** Reduce dashboard verbosity, show minimal info.

**Pros:**
- Potentially cleaner context
- Faster to read
- Less scrollback

**Cons:**
- Director loses visibility into project status
- Dashboards are already reasonably concise
- Doesn't address bio generation noise
- Not where the real context pollution is
- Dashboard content is actually useful context (unlike mythology research)

**Rejected because:** Dashboard display is valuable context for Director AND for the agent's work. Dashboards help agents understand project state. **The real problem is context pollution from initialization noise, not dashboard content.**

## Consequences

### Positive

- ✅ **Clean working context**: Agent starts work without mythology research, UUID logs, or setup noise
- ✅ **Context focus**: Main agent context dedicated to actual work, not initialization artifacts
- ✅ **Reduced cognitive load**: Agent doesn't carry 600-1,400 tokens of irrelevant details into work
- ✅ **Targeted optimization**: Only noise-generating steps delegated
- ✅ **Context pollution eliminated**: Research, operational logs, and formatting noise discarded in subagents
- ✅ **Parallelization**: Bio generation can run while possession registration happens
- ✅ **Graceful degradation**: If subagent fails, main agent can fall back
- ✅ **Preserves Director interaction**: Decision points and visibility remain in main agent
- ✅ **Scalable pattern**: Can extend to other noisy skill steps in future

### Negative

- ⚠️ **Added complexity**: Possession-start skill now coordinates subagents
- ⚠️ **Debugging harder**: Bio generation process not visible in main agent context (but can add --no-subagent flag)
- ⚠️ **Latency**: Subagent invocation adds overhead (~2-3 seconds per subagent)
- ⚠️ **Error handling**: Must handle subagent failures gracefully
- ⚠️ **Conditional logic**: When to delegate vs when to execute directly
- ⚠️ **Testing**: Need to test both delegated and non-delegated paths

### Risks & Mitigation

| Risk | Mitigation |
|------|-----------|
| **Subagent fails to generate bio** | Main agent falls back to generating bio directly; Error message to Director |
| **Subagent returns malformed bio** | Validate bio length/format before saving; Regenerate if invalid |
| **Parallel execution causes race conditions** | Main agent waits for bio subagent before displaying result; Clear sequencing |
| **Possession file subagent initializes incorrectly** | Validate epic_id and task list before writing; Main agent can review and correct |
| **Increased debugging difficulty** | Add `--no-subagent` flag to possession-start for debugging; Log subagent prompts/results |
| **Context pollution returns if overused** | Only delegate genuinely noisy steps; Monitor context quality over time |
| **Complexity discourages maintenance** | Document subagent contracts clearly; Provide examples in skill |
| **Context still polluted despite delegation** | Review and refine what gets delegated; Ensure subagents return minimal results |

### Context Cleanliness Impact

**The primary value is qualitative - agents start work with focused context:**

**Before (with bio generation in main context):**
```
Main agent context after possession-start:
- Token 1-400: Dashboard display (useful - project status)
- Token 401-1000: Bio research & crafting (NOISE - mythology facts never needed again)
- Token 1001-1200: Operational logs (NOISE - UUID generation, database confirmations)
- Token 1201+: Actual work begins (agent carries 800 tokens of irrelevant context)
```

**After (with bio delegation):**
```
Main agent context after possession-start:
- Token 1-400: Dashboard display (useful - project status)
- Token 401-550: Bio result only (useful - compact daemon identity)
- Token 551+: Actual work begins (clean context, no noise)
```

**Agent starts work with 600-800 fewer tokens of irrelevant initialization artifacts.**

The agent doesn't need to "remember" how the bio was crafted or what mythology was researched - it just needs the result. Similarly for epic possession files, the agent needs the summary ("5 tasks in this epic"), not the full query results and formatting decisions.

## Implementation Plan

### Phase 1: Bio Generation Delegation

**Tasks:**
1. Update possession-start skill Step 3 to detect `bio IS NULL`
2. Implement subagent delegation for bio generation
3. Handle bio result display
4. Add fallback for subagent failure
5. Test with new daemon (e.g., bes, atum)

**Success criteria:**
- Bio generated by subagent and saved correctly
- Main agent displays result without showing research process
- Context pollution reduced by ~450 tokens for first-time daemon

### Phase 2: Possession File Delegation (Epic-Scoped)

**Tasks:**
1. Create possession file initialization subagent prompt template
2. Update possession-start Step 6 to conditionally delegate
3. Implement epic context gathering (epic details, task list)
4. Write possession file with structured initial content
5. Test with epic-scoped possession

**Success criteria:**
- Possession file created with epic overview and task list
- Main agent continues to other steps while subagent works
- Context pollution reduced by ~750 tokens for epic possessions

### Phase 3: Monitoring & Refinement

**Tasks:**
1. Add `--no-subagent` flag for debugging
2. Log subagent invocations and results
3. Monitor actual context quality vs projections
4. Gather Director feedback on experience
5. Adjust delegation thresholds if needed

**Success criteria:**
- Context cleanliness validated through monitoring
- No regressions in possession-start functionality
- Director experience improved or neutral

## References

- **Skill:** possession-start (.opencode/skills/possession-start/SKILL.md)
- **Related ADR:** ADR-006 (Entity Model Clarity - Daemons, Possessions, Agents)
- **Related ADR:** ADR-009 (Agent Coordination Patterns)
- **OpenCode Task Tool:** For subagent delegation
- **Token Budget:** 1M tokens per session (plenty of headroom for optimization experiments)

## Notes

### Design Philosophy

**Selective delegation over wholesale outsourcing:**
- Possession-start remains in main agent for Director interaction
- Only noisy, self-contained steps delegated
- Context cleanliness realized without sacrificing visibility

**Optimize for context quality, not just token count:**
- Bio generation: 600 tokens of process noise → 150 tokens of clean result (4x compression)
- Dashboard display: 1,500 tokens → stays in main (Director needs to see it, and it's useful context)
- Possession registration: 200 tokens → stays in main (already clean and efficient)

**Parallelization where safe:**
- Bio generation can happen during possession registration
- Possession file initialization can happen during handoff checking
- No shared state, no race conditions

### Future Extensions

This pattern could extend to other expensive skill steps:

**Handoff workflow initialization:**
- If 10+ pending handoffs, delegate review and summarization
- Return compact summary to main agent
- Director sees "5 high-priority handoffs, 3 medium, 2 low" not full list

**Review queue analysis (Administrator):**
- Delegate review triage to subagent
- Return prioritized list with recommendations
- Main agent shows top 3, delegates rest

**Task dependency analysis:**
- For complex epics, delegate dependency graph generation
- Subagent analyzes task relationships
- Returns recommended task order

**These are future considerations, not part of current proposal.**

### Subagent Prompt Examples

**Bio Generation:**
```
Generate and save a whimsical first-person bio for daemon 'bes' (Egyptian, Architect role).

Steps:
1. Research: Bes is the Egyptian protective craftsman deity
2. Style: 3-5 sentences, first-person, whimsical, relevant to architecture
3. Save: daemon_set_bio tool: daemon_set_bio({ name: "bes", bio: "<bio-text>" })

Return ONLY the bio text (not command output or explanations).

Example style:
"I am [Name], the [mythology] [title/role]. [Key mythology fact with humor]. 
[How this relates to technical role]. [Personality quirk or memorable detail]."
```

**Possession File Initialization:**
```
Initialize possession file for epic-scoped possession.

Context:
- Possession ID: 115
- Codename: omega-nexus
- Daemon: aruru (Architect)
- Role: Architect  
- Epic: EPC-H-0004 (Multi-Tool Adapter System)
- Possession file: .opencode/work/possessions/2026-02-16.12:56:14.architect.aruru.omega-nexus.md

Tasks:
1. Get epic details: s9 epic show EPC-H-0004 --json
2. Get tasks: s9 task list --epic EPC-H-0004 --role Architect --json
3. Write possession file with:
   - Epic title and description
   - Task list (ID, title, status)
   - Initial approach section (placeholder)
   - Work log section (empty, ready for updates)

Return: "Possession file initialized with [N] tasks from epic EPC-H-0004"
```

### Open Questions

1. **Should possession file delegation be opt-in (--init-possession-file) or automatic for --epic?**
   - Leaning toward automatic for --epic (sensible default)
   - Can add --skip-possession-file flag if Director wants minimal setup

2. **Should we show subagent work in progress to Director?**
   - Current proposal: No, just show result
   - Alternative: "Bio generation in progress..." status message
   - Leaning toward silent delegation (cleaner UX)

3. **What's the failure UX?**
   - Current proposal: Fall back to main agent execution
   - Alternative: Skip step, warn Director
   - Leaning toward fallback (robustness over context pollution)

4. **Should context cleanliness improvements be logged/reported?**
   - Could add to possession end summary: "Context optimization: eliminated ~450 tokens of initialization noise"
   - Useful for monitoring, but may be noise
   - Leaning toward silent optimization (Director doesn't care about internals)

---

**Status:** PROPOSED
**Next Step:** Discuss with Director, gather feedback, proceed to implementation or revision
