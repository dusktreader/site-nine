# Task Sizing Guide for AI Agents

## Overview

**Use t-shirt sizes instead of time estimates.** Time estimates don't apply to AI agents with different working
patterns.


## T-Shirt Sizes

**XS:** Trivial changes, single-line fixes, typos.

**S:** Simple isolated changes with minimal testing.

**M:** Moderate changes requiring design and testing.

**L:** Significant features requiring design, implementation, testing.

**XL:** Major features or multi-phase work.

**XXL:** Epic-level work spanning multiple phases.


## Usage Examples

**Task descriptions:**
```markdown
## Task: Implement ToolAdapter Protocol

**Size:** L
**Scope:** Create protocol with 30+ methods, type hints, docstrings
```

**Handoffs:**
```markdown
**Task 1.1:** Create ToolAdapter Protocol (Size: L)
**Task 1.2:** Implement OpenCodeAdapter (Size: XL)
```


## Guidelines

**Break down large tasks:**

Instead of `Implement multi-tool support (XXL)`, use:
```markdown
Phase 1: Adapter Foundation (XL)
  - Task 1.1: ToolAdapter Protocol (L)
  - Task 1.2: OpenCodeAdapter (XL)
  - Task 1.3: ToolRegistry (L)
```

**Combine small tasks:**

Instead of multiple XS tasks, group: `Fix documentation typos across 3 files (S)`


## Communicate Scope

**✅ Good:**
```markdown
**Large (L)** task involving 30+ protocol methods with full type hints, comprehensive docstrings, error handling
patterns, and extension points. Complexity comes from ensuring protocol covers all tool operations while remaining
extensible.
```

**❌ Poor:**
```markdown
This will take 8 hours because you need to write 30+ methods with documentation.
```


## Summary

- ✅ Use t-shirt sizes (XS, S, M, L, XL, XXL)
- ✅ Describe scope and complexity
- ✅ Break down large tasks
- ❌ Don't use time estimates (hours, days, weeks)
- ❌ Don't assume human work patterns

T-shirt sizing focuses on scope and complexity, not duration.
