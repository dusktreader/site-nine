# Code Review Guide

Guidelines and checklist for code reviews.

> **Note:** General best practices until s9-native review framework is implemented.

**Use for:** Reviewing other agents' code, self-review before committing, quality assurance.


## Pre-Review Checklist

- [ ] All tests pass
- [ ] Code formatted and linted
- [ ] Commits follow guidelines
- [ ] Changes clearly described


## Review Checklist

### Code Quality

- [ ] Follows existing patterns
- [ ] Type hints on functions
- [ ] Docstrings on public APIs
- [ ] No commented-out code or debug statements
- [ ] Appropriate error handling
- [ ] No hardcoded values
- [ ] Clear, descriptive names


### Testing

- [ ] All tests pass
- [ ] New features have tests
- [ ] Edge cases covered
- [ ] Tests clear and focused


### Documentation

- [ ] User docs updated if needed
- [ ] Docstrings added/updated
- [ ] Complex logic commented


### Security

- [ ] No credentials in code
- [ ] Input validation present
- [ ] Parameterized SQL queries
- [ ] Path traversal prevention
- [ ] Secrets in environment variables


### Git

- [ ] Conventional commit format
- [ ] Clear commit messages
- [ ] Logical commit organization


## Feedback Guidelines

### Critical Issues (must fix)

Security vulnerabilities, breaking changes, logic errors, test failures.


### Suggestions (nice to have)

Code clarity, performance optimizations, additional tests.


### Effective Feedback

✅ Be specific - Point to exact lines and issues  
✅ Be clear - Explain what's wrong and why  
✅ Be actionable - Suggest concrete improvements  
✅ Distinguish severity - Critical vs nice-to-have

❌ Don't be vague - "This looks wrong" isn't helpful  
❌ Don't rewrite code in comments - Point to the issue instead


## Related Documentation

- **[testing.md](./testing.md)** - Testing patterns and best practices
- **[commit-guidelines.md](./commit-guidelines.md)** - Commit message format
