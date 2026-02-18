# Commit Guidelines

Commit message format and conventions.


## Format

```
type(scope): brief description [Agent: Role - Name]

Optional longer description explaining why (not just what).

- Key changes listed
- Files affected
```


## Types

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `test:` Tests
- `refactor:` Code refactoring
- `chore:` Maintenance, dependencies
- `perf:` Performance improvements
- `style:` Code style/formatting
- `ci:` CI/CD changes


## Scopes (site-nine specific)

`cli`, `core`, `tasks`, `agents`, `templates`, `database`, `config`, `docs`

## Examples

**Good:**
```bash
feat(cli): add task dependency command [Agent: Engineer - Azazel]
fix(database): handle missing daemon names [Agent: Engineer - Lucifer]
docs(readme): update quickstart guide [Agent: Documentarian - Thoth]
```

**Bad:**
```bash
Updated stuff
Fix
wip
```

## Workflow

1. Make changes
2. Run quality checks: `make qa` (format, lint, test)
3. Stage changes: `git add <files>`
4. Commit with proper format
5. Push when ready

Always run `make qa` before committing to prevent CI failures.

## Related

- [testing.md](./testing.md) - Testing patterns
- [README.md](./README.md) - Development guide overview
