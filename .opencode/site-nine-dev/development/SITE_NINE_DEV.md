# site-nine Development Guide

This guide contains development instructions specific to working on the **site-nine** project itself. These instructions are NOT included when bootstrapping new site-nine projects.

---

## Reporting Broken Commands

**IMPORTANT:** If you encounter any broken `s9` commands during development, you MUST create an Operator task to fix them.

### What Constitutes a "Broken Command"

A command is considered broken if:
- It crashes with an error or exception
- It shows incorrect help text or usage information
- Required options are missing or incorrectly defined
- The command doesn't perform its documented function
- Error messages are unclear or misleading
- The command has a bug that prevents normal operation

### How to Report Broken Commands

When you encounter a broken `s9` command:

1. **Create an Operator task immediately:**
   ```bash
   s9 task create --role Operator --priority HIGH \
     --title "Fix broken s9 command: [command-name]" \
     --description "Command: s9 [command-name] [subcommand]
   
   Issue: [Describe what's broken]
   
   Expected behavior: [What should happen]
   
   Actual behavior: [What actually happens]
   
   Error output: [Paste any error messages]
   
   Steps to reproduce:
   1. [Step 1]
   2. [Step 2]
   3. [etc.]"
   ```

2. **Use the workaround (if available):**
   - If there's a known workaround, document it in the task
   - Continue your work using the workaround
   - The Operator will fix the underlying issue

3. **Document the issue:**
   - Add a note to your session file about the broken command
   - Include the task ID you created
   - Mention any workarounds you used

### Example: Creating a Task for a Broken Command

```bash
s9 task create --role Operator --priority HIGH \
  --title "Fix s9 mission start --session-file parameter" \
  --description "Command: s9 mission start [name] --role [Role] --session-file [path]

Issue: The --session-file parameter doesn't exist but is documented in the session-start skill.

Expected behavior: Should accept --session-file to link agent session to a specific session file.

Actual behavior: Shows error 'No such option: --session-file'

Error output:
╭─ Error ──────────────────────────────────────────────────────────────────────╮
│ No such option: --session-file                                               │
╰──────────────────────────────────────────────────────────────────────────────╯

Steps to reproduce:
1. Run: s9 mission start myagent --role Engineer --session-file '.opencode/work/sessions/test.md'
2. Observe the error

Workaround: Use --task parameter instead, which exists and works."
```

---

## Why This Matters

site-nine is a project management tool that uses its own commands. When those commands break:
- It disrupts development workflow
- It creates confusion for agents and developers
- It reduces confidence in the tool
- It blocks progress on other tasks

By immediately creating Operator tasks when you find broken commands, you:
- Document the issue for future reference
- Ensure the problem gets fixed
- Help improve the overall quality of site-nine
- Make life easier for the next agent or developer

---

## Additional Development Notes

### Testing Your Changes

When working on site-nine, always test your changes:
- Run relevant unit tests: `uv run pytest tests/`
- Test CLI commands manually: `uv run s9 [command]`
- Verify database changes with SQLite: `sqlite3 .opencode/data/project.db`

### Building site-nine

To rebuild and test the package locally:
```bash
# Install in development mode
uv pip install -e .

# Run tests
uv run pytest

# Test CLI
uv run s9 --help
```

### Project Structure

- `src/site_nine/` - Main Python package
- `src/site_nine/cli/` - CLI command implementations
- `src/site_nine/templates/` - Templates for new projects (these GET COPIED)
- `.opencode/` - site-nine's own project management (NOT copied)
- `tests/` - Test suite

---

## Remember

**This file is for developing site-nine itself, not for projects created with site-nine.**

When you bootstrap a new project with `s9 init`, this file will NOT be copied. Only the template files in `src/site_nine/templates/base/` get copied to new projects.
