# Code Review Guide

Guidelines and checklist for reviewing code in site-nine.

## Philosophy

- **Inspector role** - Primary code reviewer, but all agents can review
- **Constructive feedback** - Suggest improvements, don't just criticize
- **Security focus** - Pay special attention to security implications
- **Pattern consistency** - Ensure code follows established patterns
- **Readability matters** - Code is read more than written

## Pre-Review Checklist

Before requesting a review, the author should verify:

✅ All tests pass locally (`make qa`)  
✅ Code is formatted (`make qa/format`)  
✅ No linting errors (`make qa/lint`)  
✅ Commits follow conventional format  
✅ PR/branch description is clear

## Code Review Checklist

Use this checklist when reviewing code before submitting PR or merging:

### Code Quality

- [ ] **Follows existing code patterns** - Consistent with codebase style
- [ ] **Has type hints on all functions** - All parameters and returns typed
- [ ] **Has docstrings on public APIs** - Clear documentation for public functions/classes
- [ ] **No commented-out code** - Remove dead code, don't comment it out
- [ ] **No debug print statements** - Use proper logging instead
- [ ] **Error handling is appropriate** - Exceptions are caught and handled properly
- [ ] **No hardcoded values** - Use constants or configuration
- [ ] **Function/variable names are clear** - Names explain purpose

### Testing

- [ ] **All tests pass** - `make qa/test` succeeds
- [ ] **New features have tests** - Every new feature has corresponding tests
- [ ] **Edge cases covered** - Tests include boundary conditions and error cases
- [ ] **Test coverage >85%** - Coverage doesn't drop below threshold
- [ ] **Tests are clear and focused** - Each test has a single purpose
- [ ] **No flaky tests** - Tests are deterministic and repeatable

### Documentation

- [ ] **User docs updated** - If user-facing, documentation is updated
- [ ] **Docstrings added/updated** - Public APIs are documented
- [ ] **CHANGELOG entry** - Significant changes have changelog entry (if applicable)
- [ ] **README updated** - Setup/usage docs updated if needed
- [ ] **Code comments for complex logic** - Non-obvious code is explained
- [ ] **Examples provided** - Complex features have usage examples

### Git

- [ ] **Commits follow Conventional Commits** - Format: `type(scope): description`
- [ ] **Persona attribution in commits** - Format: `[Agent: Role - Name]`
- [ ] **Commit messages are clear** - Explain why, not just what
- [ ] **No merge commits** - Rebase preferred over merge
- [ ] **Logical commit organization** - Related changes grouped together
- [ ] **No WIP or "fix" commits** - Clean commit history

### Security

- [ ] **No credentials in code** - No API keys, passwords, tokens
- [ ] **Input validation** - User input is validated and sanitized
- [ ] **SQL injection prevention** - Parameterized queries used
- [ ] **Path traversal prevention** - File paths are validated
- [ ] **Secrets in environment** - Sensitive config uses environment variables
- [ ] **Dependencies are trusted** - New dependencies are vetted

### Performance

- [ ] **No obvious performance issues** - No N+1 queries, unnecessary loops
- [ ] **Database queries are efficient** - Indexes used appropriately
- [ ] **Large operations are batched** - Batch processing for bulk operations
- [ ] **Caching used appropriately** - Expensive operations are cached when possible

### Architecture

- [ ] **Separation of concerns** - Business logic separate from presentation
- [ ] **Dependencies are clear** - Module dependencies are explicit
- [ ] **No circular dependencies** - Import cycles are avoided
- [ ] **Appropriate abstraction level** - Not over-engineered or under-engineered

## Review Process

### 1. Understand Context

Before diving into code:
- Read the PR/task description
- Understand the problem being solved
- Review any linked issues or design docs
- Check related code/files

### 2. Start with High-Level Review

Look at the big picture first:
- Does the approach make sense?
- Is the scope appropriate?
- Are there architectural concerns?
- Does it fit the project's design philosophy?

### 3. Detailed Code Review

Go through line by line:
- Check against the checklist above
- Look for bugs and logic errors
- Verify error handling
- Check for security issues
- Assess code clarity

### 4. Test the Code

Actually run it:
```bash
# Pull the branch
git checkout feature-branch

# Run tests
make qa/test

# Try the feature manually (if applicable)
uv run s9 <command>

# Check for unexpected behavior
```

### 5. Provide Feedback

Structure your feedback:

**Critical issues** (must fix):
- Security vulnerabilities
- Breaking changes
- Logic errors
- Test failures

**Suggestions** (nice to have):
- Code clarity improvements
- Performance optimizations
- Additional test cases
- Documentation enhancements

**Positive feedback** (acknowledge good work):
- Clever solutions
- Good test coverage
- Clear documentation
- Well-structured code

### 6. Follow Up

After feedback is addressed:
- Review the changes
- Verify issues are resolved
- Approve when ready
- Thank the author

## Common Review Issues

### Code Smells

Watch for these common issues:

**Long functions** - Functions >50 lines often need refactoring:
```python
# Bad - 100+ line function
def process_user_data(user):
    # ... lots of code ...

# Good - Split into smaller functions
def process_user_data(user):
    validated = validate_user(user)
    enriched = enrich_user_data(validated)
    return save_user(enriched)
```

**Deep nesting** - Nested if/for statements >3 levels:
```python
# Bad - Deep nesting
if user:
    if user.active:
        if user.role == "admin":
            if has_permission:
                # do something

# Good - Early returns
if not user:
    return
if not user.active:
    return
if user.role != "admin":
    return
if not has_permission:
    return
# do something
```

**Magic numbers** - Unexplained constants:
```python
# Bad
if len(items) > 100:
    process_batch(items[:100])

# Good
MAX_BATCH_SIZE = 100
if len(items) > MAX_BATCH_SIZE:
    process_batch(items[:MAX_BATCH_SIZE])
```

**Inconsistent naming** - Mixed conventions:
```python
# Bad
def get_user(id):
    userName = fetch_from_db(id)
    return userName

# Good
def get_user(user_id: int) -> str:
    user_name = fetch_from_db(user_id)
    return user_name
```

### Testing Issues

**Insufficient coverage**:
```python
# Bad - Only happy path tested
def test_divide():
    assert divide(10, 2) == 5

# Good - Edge cases tested
def test_divide_success():
    assert divide(10, 2) == 5

def test_divide_by_zero_raises_error():
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)

def test_divide_negative_numbers():
    assert divide(-10, 2) == -5
```

**Unclear test names**:
```python
# Bad
def test_1():
    ...

# Good
def test_create_task_with_valid_data_succeeds():
    ...
```

### Documentation Issues

**Missing docstrings**:
```python
# Bad
def calculate_score(user, items):
    return sum(i.points for i in items) / user.factor

# Good
def calculate_score(user: User, items: list[Item]) -> float:
    """
    Calculate user's score based on item points.
    
    Args:
        user: User object containing scoring factor
        items: List of items with point values
        
    Returns:
        Average score adjusted by user factor
    """
    return sum(i.points for i in items) / user.factor
```

## Review Best Practices

### For Reviewers

✅ **Be respectful** - Constructive feedback, not criticism  
✅ **Be specific** - Point to exact lines and suggest improvements  
✅ **Be timely** - Review within 24 hours when possible  
✅ **Be thorough** - Don't rubber-stamp, actually review  
✅ **Ask questions** - If unclear, ask rather than assume  
✅ **Acknowledge good work** - Positive feedback is valuable

❌ **Don't be vague** - "This doesn't look right" isn't helpful  
❌ **Don't nitpick** - Focus on important issues  
❌ **Don't rewrite** - Suggest improvements, don't dictate style  
❌ **Don't block on minor issues** - Distinguish critical from nice-to-have

### For Authors

✅ **Self-review first** - Review your own code before requesting review  
✅ **Provide context** - Explain why, not just what  
✅ **Keep PRs focused** - One feature/fix per PR  
✅ **Keep PRs small** - Easier to review <400 lines  
✅ **Respond to feedback** - Address all comments  
✅ **Ask for clarification** - If feedback is unclear, ask

❌ **Don't take it personally** - Feedback is about code, not you  
❌ **Don't get defensive** - Be open to suggestions  
❌ **Don't rush** - Take time to address feedback properly  
❌ **Don't ignore feedback** - Address or discuss every comment

## Tools

### Automated Checks

Use these before requesting review:

```bash
# Format code
make qa/format

# Lint code
make qa/lint

# Run tests
make qa/test

# Check types
make qa/types  # If configured

# All checks
make qa
```

### Review Tools

- **GitHub PR reviews** - Line comments, approval workflow
- **Git diff** - `git diff main...feature-branch`
- **Code coverage reports** - `pytest --cov=src --cov-report=html`

## Related Documentation

- **Testing Guide:** `.opencode/docs/guides/testing.md` - Testing patterns and best practices
- **Commit Guidelines:** `.opencode/docs/guides/commit-guidelines.md` - Commit message format
- **Architecture Guide:** `.opencode/docs/guides/architecture.md` - System architecture overview
- **Inspector Role:** `.opencode/docs/roles/inspector.md` - Primary code review role
