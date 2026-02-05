# Commit Guidelines

Guidelines for writing clear, consistent commit messages in site-nine.

## Format

```
type(scope): brief description [Agent: Role - Name]

Optional longer description explaining why (not just what).

- Key changes listed
- Files affected
```

## Types

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `test:` - Tests
- `refactor:` - Code refactoring
- `chore:` - Maintenance, dependencies
- `perf:` - Performance improvements
- `style:` - Code style/formatting
- `ci:` - CI/CD changes

## Scopes (site-nine specific)

- `cli` - CLI commands
- `core` - Core business logic
- `tasks` - Task management
- `agents` - Agent sessions
- `templates` - Template rendering
- `database` - Database operations
- `config` - Configuration
- `docs` - Documentation

## Examples

**Good commits:**
```bash
feat(cli): add task dependency command [Agent: Engineer - Azazel]
fix(database): handle missing daemon names [Agent: Engineer - Lucifer]
docs(readme): update quickstart guide [Agent: Documentarian - Thoth]
test(cli): add agent session tests [Agent: Engineer - Azazel]
refactor(core): simplify template rendering [Agent: Engineer - Mephistopheles]
```

**Bad commits:**
```bash
Updated stuff
Fix
wip
changes
```

## Workflow

1. Make changes
2. Run quality checks: `make qa`
3. Stage changes: `git add <files>`
4. Commit with proper format
5. Push when ready

## Related

- **Development Procedures:** `.opencode/docs/procedures/README.md` - Command references for common tasks
- **Agent Guide:** `.opencode/docs/guides/AGENTS.md` - Agent workflows and responsibilities
