# Markdown Style Guide

This document establishes markdown formatting standards for the site-nine project. **All agents must follow these conventions** when creating or editing markdown files.

This applies to:
- Documentation in `docs/source/` (human-facing documentation)
- ADRs in `.opencode/docs/adrs/`
- Mission files in `.opencode/work/missions/`
- Task files in `.opencode/work/tasks/`
- All other markdown files in the repository

Following these conventions ensures consistency across all documentation.


## Heading styles

### Format

Use ATX-style headings with hash marks (`#`). Do not use Setext-style underlines.

```markdown
# Heading 1
## Heading 2
### Heading 3
```

### Capitalization

- **H1 (document titles)**: Title Case
- **H2 and below (sections)**: Sentence case

**Examples:**

```markdown
# Markdown Style Guide

## Heading styles

### Format conventions
```

### Spacing

Place **2 blank lines** before a heading UNLESS the parent heading has no content or paragraphs.

**Correct:**

```markdown
## Section one

This section has content, so the next heading needs 2 blank lines.


## Section two

More content here.
```

**Correct:**

```markdown
## Section one
### Subsection

No blank lines needed between stacked headings.
```

**Incorrect:**

```markdown
## Section one


### Subsection
```


## Line wrapping

Wrap lines at **120 characters** for prose content. Code blocks and tables are exempt from this rule.

**When to wrap:**
- Paragraph text in documentation
- List items with long descriptions
- Notes and descriptions in task files

**When not to wrap:**
- Code blocks
- Table content
- URLs
- Command examples


## Code blocks

Use fenced code blocks with triple backticks. Always specify a language identifier for syntax highlighting.

```markdown
```bash
s9 task create "Fix bug in parser"
```
```

**Common language identifiers:**
- `bash` - Shell commands
- `python` - Python code
- `yaml` - YAML configuration
- `markdown` - Markdown examples
- `text` - Plain text output
- `json` - JSON data

**Do not use** indented code blocks (4-space indent style).


## Lists

### Unordered lists

Use hyphens (`-`) as bullets. Use 2-space indentation for nested items.

```markdown
- First item
- Second item
  - Nested item
  - Another nested item
- Third item
```

Place a blank line before and after lists when separating from other block elements (paragraphs, headings, code blocks).

**User-facing documentation:** Avoid overusing bullet lists. Use prose paragraphs when appropriate to improve
readability and flow. Reserve lists for cases where enumeration adds clarity.

### Ordered lists

Use sequential numbering (`1.`, `2.`, `3.`).

```markdown
1. First step
2. Second step
3. Third step
```

You may use auto-numbering (all items as `1.`) if preferred, but be consistent within a document.


## Tables

### Alignment

**ALWAYS align table columns vertically in the source markdown.** Tables must be readable in both the editor and the browser. Properly aligned tables make code review, manual editing, and understanding content structure much easier.

**Good:**

```markdown
| Column One | Column Two | Column Three |
|------------|------------|--------------|
| Short      | Medium     | Long content |
| Data       | More data  | Even more    |
```

**Unacceptable:**

```markdown
| Column One | Column Two | Column Three |
|---|---|---|
| Short | Medium | Long content |
| Data | More data | Even more |
```

**Why this matters:** Unaligned tables are difficult to read and edit in source files. Since markdown is read both as source and rendered output, source readability is just as important as rendered appearance.

### Syntax

- Use leading and trailing pipes on every row
- Use simple hyphens in separator row (no alignment syntax like `:---:` or `---:` unless alignment is needed)
- Left-align content by default


## Emphasis

### Bold

Use double asterisks for bold text.

```markdown
**bold text**
```

### Italic

Use single asterisks for italic text.

```markdown
*italic text*
```

### Bold in lists

Use bold for emphasis on key terms in list items.

```markdown
- **Project name** - The name of your project
- **Project type** - Select from python, typescript, go, rust, or other
```


## Links

Use inline reference style for links.

```markdown
[Link text](path/to/file.md)
[External link](https://example.com)
```


## Horizontal rules

Use three hyphens for horizontal rules.

```markdown
---
```


## Emoji usage

Use emojis sparingly and purposefully. Appropriate uses include:

- Section markers in guides (e.g., `### 📚 Essential Reading`)
- Status indicators in task files
- Warning/info callouts (e.g., `### ⚠️ Critical Requirements`)

Avoid emoji in:
- Technical documentation
- ADRs
- API references
- Code comments


## Front matter

Mission files and certain documentation may use YAML front matter. Place it at the very beginning of the file with no
blank lines before it.

```markdown
---
id: MISSION-001
persona: haya-ji
role: Documentarian
status: active
---

# Mission Title
```


## Summary checklist

When creating or editing markdown files, ensure:

- [ ] ATX-style headings (`#`) with proper capitalization (Title Case for H1, Sentence case for H2+)
- [ ] 2 blank lines before headings (except when stacked with no content between)
- [ ] Lines wrapped at 120 characters (prose only)
- [ ] Fenced code blocks with language identifiers
- [ ] Hyphen bullets (`-`) with 2-space indentation
- [ ] Tables aligned vertically in source
- [ ] Minimal and purposeful emoji usage
- [ ] Links use inline reference style `[text](path)`
