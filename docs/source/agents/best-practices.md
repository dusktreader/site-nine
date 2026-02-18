# Best Practices for Working with Agents

This guide provides practical tips and best practices for Directors (human users) working with AI agents in the site-nine system.


## Mission Initialization

### Use the `/summon` command

Always start missions using the `/summon` command in your agentic coding platform (OpenCode, Cursor, Windsurf, etc.). This command loads the `session-start` skill, which handles:

- Role selection (or uses role from `/summon <role>`)
- Persona selection (automatic or via `--persona` flag)
- Mission registration in the database
- Task assignment (via `--task` or `--auto-assign` flags)
- Setting up the mission file

This ensures consistency and accountability across all missions. Each mission creates:

- A unique persona identity for the agent
- Proper tracking in the mission file
- Registration in the database
- Commit attribution via `[Persona: Name - Role]` or `[Mission: codename]`


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

### Keep agents.md updated

The file `.opencode/docs/guides/agents.md` contains patterns that agents read before starting work. Keep it updated with:

- Project-specific code patterns
- Lessons learned from previous work
- Important conventions or standards
- Common pitfalls to avoid


### Review mission files

Mission files in `.opencode/work/missions/` document:

- Work performed
- Decisions made
- Files changed
- Time spent
- Tasks claimed/completed

Review these files periodically to:

- Track progress across missions
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

These artifacts are invaluable for:

- Understanding what was done
- Generating changelogs
- Knowledge transfer
- Future troubleshooting


### Commit incrementally

Encourage agents to commit work incrementally, not in one large commit. This:

- Makes review easier
- Preserves more granular history
- Allows easier rollbacks if needed
- Provides better context in git history


### End missions properly

Always use the `/handoff` command or the `session-end` skill to properly close missions. This ensures:

- Mission files are complete
- Database records are updated
- Handoff documentation is created if needed
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

You can run multiple missions concurrently using different personas and roles. This is useful for:

- Working on multiple features simultaneously
- Having one agent investigate while another implements
- Separating concerns (e.g., one agent on feature work, another on documentation)


## Common Pitfalls to Avoid

### Don't skip mission initialization

Always use `/summon` to start missions. Manual initialization can lead to:

- Missing tracking data
- Inconsistent persona assignment
- Lack of database registration
- Poor handoff documentation


### Don't mix roles within a mission

Each mission should stick to its assigned role. If you need different expertise:

- End the current mission
- Start a new mission with the appropriate role

This maintains clear separation of concerns and better tracking.


### Don't forget to review designs

When using Architect to design, always review and approve before moving to implementation. Catching issues in the design phase is much cheaper than after code is written.


### Don't ignore mission files

Mission files are not just for agents - they're for you too. Review them to:

- Stay informed about progress
- Catch issues early
- Understand decisions being made
- Provide feedback or course corrections


## Getting Help

If you're unsure about:

- **Which role to use** - See `.opencode/docs/roles/README.md`
- **How to use s9 commands** - Run `s9 --help` or see `.opencode/data/README.md`
- **Workflow patterns** - See `.opencode/docs/procedures/WORKFLOWS.md`
- **Troubleshooting** - See `.opencode/docs/guides/troubleshooting.md`

The agent system is designed to make your development workflow more organized and trackable. Use these best practices to get the most out of it!
