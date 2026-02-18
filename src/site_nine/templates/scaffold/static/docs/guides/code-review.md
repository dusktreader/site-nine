# Code Review Guide

Guidelines and checklist for code reviews in s9-powered projects.

> **Note:** This guide provides general code review best practices in lieu of an s9-native review framework. It may be
> replaced in the future with a workflow that integrates with s9 tasks and missions.

**Use this guide for:**
- Reviewing code written by other agents
- Self-reviewing your own code before committing
- Ensuring code quality standards are met


## Pre-Review Checklist

Before requesting a review or committing code:

- [ ] All tests pass
- [ ] Code is formatted and linted
- [ ] Commits follow commit guidelines
- [ ] Changes are clearly described


## Review Checklist


### Code Quality

- [ ] Follows existing code patterns
- [ ] Has type hints on functions (if applicable)
- [ ] Has docstrings on public APIs
- [ ] No commented-out code
- [ ] No debug statements
- [ ] Error handling is appropriate
- [ ] No hardcoded values
- [ ] Names are clear and descriptive


### Testing

- [ ] All tests pass
- [ ] New features have tests
- [ ] Edge cases covered
- [ ] Tests are clear and focused


### Documentation

- [ ] User docs updated if needed
- [ ] Docstrings added/updated
- [ ] Code comments for complex logic


### Security

- [ ] No credentials in code
- [ ] Input validation present
- [ ] SQL injection prevention (parameterized queries)
- [ ] Path traversal prevention
- [ ] Secrets in environment variables


### Git

- [ ] Commits follow conventional format
- [ ] Commit messages are clear
- [ ] Logical commit organization


## Review Process

1. **Understand context** - Read the task/issue description
2. **High-level review** - Does the approach make sense?
3. **Detailed review** - Check against checklist above
4. **Test the code** - Actually run it
5. **Provide feedback** - Be specific and constructive
6. **Follow up** - Verify issues are resolved


## Feedback Guidelines


### Critical Issues (must fix)

- Security vulnerabilities
- Breaking changes
- Logic errors
- Test failures


### Suggestions (nice to have)

- Code clarity improvements
- Performance optimizations
- Additional test cases


## Providing Effective Feedback

When reviewing code (or self-reviewing):

✅ Be specific - Point to exact lines and issues  
✅ Be clear - Explain what's wrong and why  
✅ Be actionable - Suggest concrete improvements  
✅ Distinguish severity - Critical vs nice-to-have

❌ Don't be vague - "This looks wrong" isn't helpful  
❌ Don't rewrite code in comments - Point to the issue instead


## Related Documentation

- **[testing.md](./testing.md)** - Testing patterns and best practices
- **[commit-guidelines.md](./commit-guidelines.md)** - Commit message format
