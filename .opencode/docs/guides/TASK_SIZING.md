# Task Sizing Guide for AI Agents

## Overview

When estimating work effort, **use t-shirt sizes instead of time estimates**. Time estimates (hours, days, weeks) are calibrated for human developers and don't apply to AI agents with different working patterns.

## T-Shirt Sizes

Use these standardized sizes for all task and effort estimates:

### XS (Extra Small)
- **Scope:** Trivial changes, single-line fixes, typo corrections
- **Examples:**
  - Fix a typo in documentation
  - Update a version number
  - Add a single log statement
  - Change a variable name

### S (Small)
- **Scope:** Simple, isolated changes with minimal testing
- **Examples:**
  - Add a single CLI flag to existing command
  - Update docstring for a function
  - Add a simple validation check
  - Create a basic template file

### M (Medium)
- **Scope:** Moderate changes requiring some design and testing
- **Examples:**
  - Implement a new CLI command
  - Add a database migration
  - Refactor a single module
  - Write comprehensive tests for a feature

### L (Large)
- **Scope:** Significant features requiring design, implementation, testing
- **Examples:**
  - Implement a new adapter (OpenCodeAdapter, CursorAdapter)
  - Design and implement a new subsystem
  - Major refactoring across multiple files
  - Complete PoC implementation

### XL (Extra Large)
- **Scope:** Major features or multi-phase work
- **Examples:**
  - Implement entire Phase 1 (Adapter Foundation)
  - Complete skills system refactoring
  - End-to-end integration of new tool support
  - Major architecture changes

### XXL (Double Extra Large)
- **Scope:** Epic-level work spanning multiple phases
- **Examples:**
  - Complete multi-tool architecture implementation (all 5 phases)
  - Full system redesign
  - Migration to new framework

## When to Use Each Size

### In Task Descriptions

**✅ Correct:**
```markdown
## Task: Implement ToolAdapter Protocol

**Size:** L
**Scope:** Create complete protocol with 30+ methods, type hints, docstrings
```

**❌ Incorrect:**
```markdown
## Task: Implement ToolAdapter Protocol

**Estimated:** 8 hours
**Scope:** Create complete protocol
```

### In Handoff Documents

**✅ Correct:**
```markdown
**Task 1.1:** Create ToolAdapter Protocol (Size: L)
**Task 1.2:** Implement OpenCodeAdapter (Size: XL)
**Task 1.3:** Create ToolRegistry (Size: L)
```

**❌ Incorrect:**
```markdown
**Task 1.1:** Create ToolAdapter Protocol (8 hours)
**Task 1.2:** Implement OpenCodeAdapter (16 hours)
**Task 1.3:** Create ToolRegistry (12 hours)
```

### In Summaries

**✅ Correct:**
```markdown
**Phase 1 Effort:** XL (7 large/medium tasks)
**Next Task:** M (medium complexity, well-defined)
```

**❌ Incorrect:**
```markdown
**Phase 1 Effort:** 80 hours over 2 weeks
**Next Task:** 4-6 hours
```

## Sizing Guidelines

### Breaking Down Large Tasks

If a task is XL or XXL, consider breaking it into smaller tasks:

**Instead of:**
```markdown
Task: Implement complete multi-tool support (XXL)
```

**Do this:**
```markdown
Phase 1: Adapter Foundation (XL)
  - Task 1.1: ToolAdapter Protocol (L)
  - Task 1.2: OpenCodeAdapter (XL)
  - Task 1.3: ToolRegistry (L)
  - Task 1.4: PathResolver (M)
  - Task 1.5: Unit Tests (L)
```

### Combining Small Tasks

If you have many XS/S tasks, consider grouping them:

**Instead of:**
```markdown
- Fix typo in README (XS)
- Fix typo in AGENTS.md (XS)
- Fix typo in architecture.md (XS)
```

**Do this:**
```markdown
- Fix documentation typos across 3 files (S)
```

## Communicating Scope

Instead of saying "this will take X hours," describe the scope:

**✅ Good Communication:**
```markdown
This is a **Large (L)** task involving:
- Creating 30+ protocol methods with full type hints
- Writing comprehensive docstrings
- Designing error handling patterns
- Documenting extension points

The complexity comes from ensuring the protocol covers all tool operations while remaining extensible.
```

**❌ Poor Communication:**
```markdown
This will take 8 hours because you need to write 30+ methods with documentation.
```

## Context for Humans

When humans need to plan work, they can use these rough guidelines to translate sizes:

| Size | Rough Human Estimate | Note |
|------|---------------------|------|
| XS | < 30 min | Trivial |
| S | 1-2 hours | Simple |
| M | Half day | Moderate |
| L | 1-2 days | Complex |
| XL | 3-5 days | Major feature |
| XXL | 1-2 weeks | Epic |

**However:** These are ONLY for human planning. AI agents should NOT use time estimates in their communication or task descriptions.

## Examples from site-nine

### Phase 1 Tasks (Sized)

```markdown
## Phase 1: Adapter Foundation (XL)

### Task Breakdown

**Task 1.1: Create ToolAdapter Protocol (L)**
- Define Protocol class with 30+ abstract methods
- Full type hints and docstrings
- Error handling specifications

**Task 1.2: Implement OpenCodeAdapter (XL)**
- Wrap existing functionality (thin wrapper)
- Delegate to existing code in core, agents, tasks
- Maintain 100% backward compatibility
- Comprehensive testing

**Task 1.3: Create ToolRegistry (L)**
- Auto-detection via directory markers
- Adapter initialization and caching
- Error handling for missing tools

**Task 1.4: Implement PathResolver (M)**
- Path mapping between tool conventions
- Tool-specific directory structure handling
- Backward compatible with existing resolution

**Task 1.5: Write Unit Tests (L)**
- 90%+ coverage for new components
- Test all adapter operations
- Backward compatibility validation

**Task 1.6: Integration Testing (M)**
- End-to-end tests with OpenCodeAdapter
- Performance benchmarks
- Existing project validation

**Task 1.7: Update Documentation (M)**
- Docstrings for all classes/methods
- Architecture README updates
- Code comments and examples
```

### Handoff Example (Sized)

```markdown
## Summary

**Task:** Phase 1: Adapter Foundation  
**Size:** XL (7 tasks: 3 Large, 3 Medium, 1 Extra Large)  
**Priority:** HIGH

### Phase 1 Tasks

**Week 1:**
- Task 1.1: Create ToolAdapter Protocol (L)
- Task 1.2: Implement OpenCodeAdapter (XL)

**Week 2:**
- Task 1.3: Create ToolRegistry (L)
- Task 1.4: Implement PathResolver (M)
- Task 1.5: Write Unit Tests (L)
- Task 1.6: Integration Testing (M)
- Task 1.7: Update Documentation (M)
```

## Migration from Time Estimates

When updating existing documents:

1. **Find time estimates:** Search for patterns like "8 hours", "2 weeks", "4-6 hours"
2. **Assess scope:** Understand what the task actually involves
3. **Map to t-shirt size:** Use the guidelines above
4. **Describe complexity:** Explain WHY it's that size, not HOW LONG it takes

**Example Migration:**

**Before:**
```markdown
**Estimated:** 16 hours
This task requires implementing the adapter with full backward compatibility.
```

**After:**
```markdown
**Size:** XL
This is an extra-large task due to:
- Wrapping extensive existing functionality
- Maintaining 100% backward compatibility
- Comprehensive testing requirements
- Multiple integration points with core systems
```

## Summary

- ✅ **Use t-shirt sizes** (XS, S, M, L, XL, XXL)
- ✅ **Describe scope and complexity**
- ✅ **Break down large tasks into smaller ones**
- ❌ **Don't use time estimates** (hours, days, weeks)
- ❌ **Don't assume human work patterns**

**Remember:** T-shirt sizing focuses on scope and complexity, not duration. This better reflects the variability in how different AI agents approach problems.
