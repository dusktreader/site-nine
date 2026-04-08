# Best Practices for Working with Agents

This guide provides practical tips and best practices for Directors (human users) working with AI agents in the site-nine system.


## Possession Initialization

### Use `s9 summon` to start possessions

Always start possessions using the `s9 summon <role>` command. This launches OpenCode and triggers the `possession-start` skill, which handles:

- Role selection (or uses the role you specified)
- Daemon selection via LRU auto-claim
- Possession registration in the database
- Session renaming to `Operation <codename>: <Daemon> - <Role>`
- Task assignment (if you specify `--auto-assign`)

This ensures consistency and accountability across all possessions. Each possession creates:

- A unique daemon identity for the agent
- A possession file at `.opencode/work/possessions/`
- Proper tracking in the database
- Commit attribution via `[Daemon: Name - Role]` or `[Operation: codename]`


## Choosing the Right Role

### Start with Administrator when unsure

If you're starting a new task and aren't sure which role is best, choose **Administrator**. The Administrator role understands the project holistically and can coordinate or delegate to specialized agents as needed.

### Choose specific roles for focused work

If you know exactly what type of work needs to be done, pick the specific role:

- **Architect** - Designing new features or refactoring plans
- **Engineer** - Implementing features, fixing bugs, writing tests
- **Tester** - Running test suites, manual validation, regression testing
- **Documentarian** - Writing/updating docs, README updates, API documentation
- **Designer** - CLI output design, UX improvements, user flow planning
- **Inspector** - Code review, finding issues, quality checks
- **Operator** - Updating agent configs, improving dev workflows


## Writing Clear Objectives

### Be specific about goals

The more specific your objectives, the better the agent can help.

**Good examples:**
- "Add rate limiting to database queries with 50/minute limit"
- "Refactor the authentication module to use JWT tokens"
- "Write integration tests for the user registration flow"

**Less effective:**
- "Make it faster"
- "Fix the bugs"
- "Improve the code"


## Understanding Role Responsibilities

### Engineer writes tests, Tester runs them

This is an important distinction in the site-nine system:

- **Engineer**: Implements features AND writes tests (unit and integration tests)
- **Tester**: Runs tests, performs manual testing, and validates behavior

This ensures tests are written as part of implementation, not as a separate phase.


### Approve designs before implementation

When working with multiple agents:

1. Have the **Architect** create a design
2. Review and approve the design as the Director
3. Then have the **Engineer** implement based on the approved design

This saves time by ensuring alignment before code is written.


### Inspector reviews, not just for bugs

Use the **Inspector** role for more than finding bugs:

- Security audits
- Consistency checks
- Finding missing documentation
- Pattern validation
- Code quality reviews


## Tracking and Documentation

### Keep the agent docs updated

The `.opencode/docs/` directory contains patterns and guides that agents read before starting work. Keep these files updated with:

- Project-specific code patterns
- Lessons learned from previous work
- Important conventions or standards
- Common pitfalls to avoid


### Review possession files

Possession files in `.opencode/work/possessions/` document:

- Work performed
- Decisions made
- Files changed
- Tasks claimed and completed

Review these files periodically to:

- Track progress across possessions
- Understand decisions that were made
- Identify patterns or recurring issues
- Generate reports or summaries


## Workflow Best Practices

### Use task artifacts

Task artifacts in `.opencode/work/tasks/` provide detailed tracking. Agents update these as they work, documenting:

- Implementation steps taken
- Files changed and why
- Important observations or decisions
- Testing performed

These artifacts are invaluable for understanding what was done, generating changelogs, knowledge transfer, and future troubleshooting.


### Commit incrementally

Encourage agents to commit work incrementally, not in one large commit. This:

- Makes review easier
- Preserves more granular history
- Allows easier rollbacks if needed
- Provides better context in git history


### End possessions properly

Always use the `possession-end` skill to properly close possessions. This ensures:

- Possession files are complete
- Database records are updated
- Loose ends are documented


## Multi-Agent Workflows

### Feature development pattern

For new features, use multiple specialized agents:

1. **Architect** designs the feature
2. **Designer** creates UI/UX specs (if user-facing)
3. You approve the design
4. **Engineer** implements and writes tests
5. **Tester** validates the implementation
6. **Documentarian** writes documentation
7. **Inspector** reviews the complete work


### Bug fixing pattern

For bug fixes, use a focused workflow:

1. **Tester** reproduces the bug and documents it
2. **Engineer** fixes the bug and writes a regression test
3. **Tester** verifies the fix


### Parallel work

You can run multiple possessions concurrently using different daemons and roles. This is useful for:

- Working on multiple features simultaneously
- Having one agent investigate while another implements
- Separating concerns (e.g., one agent on feature work, another on documentation)


## Common Pitfalls to Avoid

### Don't skip possession initialization

Always use `s9 summon` to start possessions. Manual initialization can lead to:

- Missing tracking data
- Inconsistent daemon assignment
- Lack of database registration
- Poor handoff documentation


### Don't mix roles within a possession

Each possession should stick to its assigned role. If you need different expertise:

- End the current possession using the `possession-end` skill
- Start a new possession with the appropriate role

This maintains clear separation of concerns and better tracking.


### Don't forget to review designs

When using Architect to design, always review and approve before moving to implementation. Catching issues in the design phase is much cheaper than after code is written.


### Don't ignore possession files

Possession files are not just for agents — they're for you too. Review them to:

- Stay informed about progress
- Catch issues early
- Understand decisions being made
- Provide feedback or course corrections


## Getting Help

If you're unsure about:

- **Which role to use** - See `.opencode/docs/roles/`
- **How to use s9 commands** - Run `s9 --help` or see the [CLI Reference](../cli/overview.md)
- **Workflow patterns** - See the [Advanced Topics](../advanced.md) guide
- **Troubleshooting** - See `.opencode/docs/guides/troubleshooting.md`

