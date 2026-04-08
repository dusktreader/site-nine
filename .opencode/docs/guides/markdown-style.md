# Markdown Style Guide

Markdown formatting standards for site-nine. **All agents must follow these conventions.**

Applies to: documentation (`docs/source/`), ADRs, possession files, task files, and all markdown files.


## Heading Styles

### Format

ATX-style with hash marks (`#`). No Setext-style underlines.

```markdown
# Heading 1
## Heading 2
### Heading 3
```


### Capitalization

- **H1 (titles)**: Title Case
- **H2+ (sections)**: Sentence case


### Spacing

**Before headings:** 2 blank lines (unless stacked with no content between).

**After headings:** 1 blank line before content.


## Line Wrapping

Wrap at **120 characters** for prose. Code blocks, tables, URLs, and commands are exempt.


## Code Blocks

Fenced code blocks with triple backticks and language identifier.

```markdown
```bash
s9 task create "Fix bug"
```
```

**Common languages:** `bash`, `python`, `yaml`, `markdown`, `text`, `json`

**Don't use** indented code blocks (4-space style).


## Lists

**Use lists for:** Distinct items, sequential steps, related examples, key points needing visual separation.

**Don't use for:** Prose content, narrative explanations, single items, excessive nesting (>2 levels).

**Golden rule:** Use lists when enumeration adds clarity.


### Unordered Lists

Hyphens (`-`) with 2-space nesting.

```markdown
- First item
- Second item
  - Nested item
- Third item
```

Blank line before and after lists when separating from other blocks.


### Ordered Lists

Sequential numbering (`1.`, `2.`, `3.`) or auto-numbering (all `1.`). Be consistent within document.


## Tables

### Alignment

**ALWAYS align columns vertically.** Tables must be readable in source and browser.

**Good:**

```markdown
| Column One | Column Two | Column Three |
|------------|------------|--------------|
| Short      | Medium     | Long content |
| Data       | More data  | Even more    |
```


### Syntax

- Leading and trailing pipes on every row
- Simple hyphens in separator row (use alignment syntax `:---:` / `---:` only when needed)
- Left-align by default


## Emphasis

**Bold:** `**double asterisks**`

**Italic:** `_single underscores_`

**Bold in lists:** Use for key terms: `- **Term** - Description`


## Admonitions

Callout boxes for critical information. Use sparingly.

**Use for:** Critical warnings, prerequisites, security concerns, common pitfalls, key concepts.

**Don't use for:** General info, every paragraph, styling regular content.

**Golden rule:** If everything is important, nothing is important.


### MkDocs (`docs/source/`)

```markdown
!!! note
    This is a note.

!!! warning
    Potential issues.

!!! danger
    Critical warning.
```

**Types:** `note`, `abstract`, `info`, `tip`, `success`, `question`, `warning`, `failure`, `danger`, `bug`, `example`,
`quote`

**Collapsible:** Use `???` for collapsed, `???+` for expanded by default.


### Other Markdown Files

GitHub-style with blockquote syntax:

```markdown
> [!NOTE]
> This is a note.

> [!WARNING]
> Potential issues.

> [!IMPORTANT]
> Critical information.
```

**Types:** `NOTE`, `TIP`, `IMPORTANT`, `WARNING`, `CAUTION`


## Links, Rules, Emoji

**Links:** Inline reference style: `[Link text](path/to/file.md)`

**Horizontal rules:** 8 hyphens: `--------`

**Emoji:** Use sparingly for section markers, status indicators, warnings. Avoid in technical docs, ADRs, API refs.


## Front Matter

YAML front matter at file beginning (no blank lines before).

```markdown
---
id: DOC-M-0001
daemon: marbas
role: Documentarian
---

# Possession Title
```


## Checklist

- [ ] ATX headings (`#`) - Title Case H1, Sentence case H2+
- [ ] 2 blank lines before headings (except stacked)
- [ ] 1 blank line after headings
- [ ] 120-char line wrap (prose only)
- [ ] Fenced code blocks with language IDs
- [ ] Hyphen bullets (`-`) with 2-space indent
- [ ] Aligned table columns
- [ ] Minimal emoji
- [ ] Inline links `[text](path)`
