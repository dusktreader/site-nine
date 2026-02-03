# Agent Roles

Site-nine provides specialized agent roles, each represented by a daemon from ancient mythology. Choose the appropriate role for your task to leverage specialized knowledge and capabilities.

---

## Administrator

![Mephistopheles](../images/mephistopheles.png){ align=left width="300" }

/// caption
Mephistopheles - Commanding strategist who coordinates projects and manages delegation
///

**When to Use**

- **Project coordination** - Orchestrating multiple agents and tasks
- **Task delegation** - Assigning work to specialized agents
- **Strategic planning** - High-level project direction
- **Workflow management** - Ensuring smooth handoffs
- **Resource allocation** - Balancing workload

**Best Practices**

- Think holistically about the entire project lifecycle
- Delegate effectively to specialized agents
- Track dependencies using the task management system
- Keep dashboard and task status current
- Document strategic decisions

---

## Architect

![Kothar](../images/kothar.png){ align=right width="300" }

/// caption
Kothar - Master designer who creates system architectures and technical decisions
///

**When to Use**

- **System design** - Creating architecture and specifications
- **Technology decisions** - Selecting frameworks and tools
- **Architecture documentation** - Writing ADRs
- **Design patterns** - Establishing coding standards
- **Technical planning** - Breaking down complex features

**Best Practices**

- Document decisions with ADRs
- Think long-term about scalability
- Review existing code before proposing changes
- Create clear diagrams for Builders
- Balance pragmatism with project needs

---

## Builder

![Azazel](../images/azazel.png){ align=left width="300" }

/// caption
Azazel - Creative craftsperson who implements features and writes code
///

**When to Use**

- **Feature implementation** - Writing new code and adding functionality
- **Bug fixes** - Resolving issues and correcting problems
- **Integration work** - Connecting systems, APIs, and services
- **Refactoring** - Improving code quality while preserving functionality
- **API development** - Creating endpoints, services, and data layers

**Best Practices**

- Review architectural specs and ADRs before implementation
- Follow project coding standards and best practices
- Run tests frequently to catch issues early
- Make small, focused commits with clear messages
- Add comments and update docs for complex functionality

---

## Tester

![Eris](../images/eris.png){ align=right width="300" }

/// caption
Eris - Mischievous chaos-bringer who finds bugs and edge cases through creative testing
///

**When to Use**

- **Writing tests** - Creating unit, integration, and end-to-end tests
- **Quality assurance** - Validating that features work as intended
- **Bug discovery** - Finding edge cases and unexpected behaviors
- **Test automation** - Setting up CI/CD pipelines and automated test suites
- **Coverage analysis** - Ensuring adequate test coverage

**Best Practices**

- Don't wait until features are "complete" to start testing
- Consider real-world usage patterns and edge cases
- Explain what each test validates and why it matters
- Make tests repeatable and easy to run
- Prioritize tests that catch real bugs, not just boost coverage

---

## Documentarian

![Nabu](../images/nabu.png){ align=left width="300" }

/// caption
Nabu - Scholarly recorder who writes comprehensive documentation and guides
///

**When to Use**

- **User documentation** - Writing guides, tutorials, and how-to articles
- **API documentation** - Documenting endpoints, parameters, and response formats
- **Code documentation** - Adding docstrings, comments, and inline explanations
- **README files** - Creating project overviews and setup instructions
- **Changelog maintenance** - Recording changes and updates for users

**Best Practices**

- Adjust complexity based on who will read the docs
- Show concrete code samples and real-world usage patterns
- Update docs when code changes; stale docs are worse than none
- Organize docs so users can find what they need quickly
- Follow your own instructions to ensure they actually work

---

## Designer

![Astarte](../images/astarte.png){ align=right width="300" }

/// caption
Astarte - Elegant creator who designs beautiful user interfaces and experiences
///

**When to Use**

- **UI design** - Creating visual layouts, components, and interfaces
- **UX design** - Designing user flows and interaction patterns
- **Visual assets** - Creating icons, images, and graphics
- **Style systems** - Building design tokens, themes, and component libraries
- **Prototyping** - Creating mockups and interactive prototypes

**Best Practices**

- Always consider the end user's needs and context
- Use design systems and established patterns
- Design for all users, including those with disabilities
- Create low-fidelity prototypes before high-fidelity designs
- Work with Builders to ensure designs are implementable

---

## Inspector

![Argus](../images/argus.png){ align=left width="300" }

/// caption
Argus - Watchful guardian who performs code reviews and security audits
///

**When to Use**

- **Code review** - Examining pull requests and providing feedback
- **Security audits** - Identifying vulnerabilities and security issues
- **Quality checks** - Verifying code quality, style, and best practices
- **Dependency audits** - Checking for outdated or vulnerable dependencies
- **Performance analysis** - Finding bottlenecks and optimization opportunities

**Best Practices**

- Focus on improvements, not criticism
- Help others learn by explaining why something should change
- Look for systemic issues, not just individual mistakes
- Always consider security implications of code changes
- Focus on meaningful improvements, not nitpicks

---

## Operator

![Nammu](../images/nammu.png){ align=right width="300" }

/// caption
Nammu - Calm infrastructure maintainer who handles deployment and operations
///

**When to Use**

- **Deployment** - Releasing code to staging, production, and other environments
- **Infrastructure** - Managing servers, containers, and cloud resources
- **Monitoring** - Setting up observability and alerting systems
- **DevOps** - Configuring CI/CD pipelines and automation
- **Troubleshooting** - Diagnosing and resolving production issues

**Best Practices**

- Manual processes are error-prone and don't scale
- Set up alerts before problems become critical
- Create step-by-step guides for common operations
- Validate in staging before pushing to production
- Design systems with redundancy and graceful degradation

---

## Historian

![Mimir](../images/mimir.png){ align=left width="300" }

/// caption
Mimir - Wise chronicler who documents project history and preserves institutional knowledge
///

**When to Use**

- **CHANGELOG maintenance** - Recording changes and updates for users
- **Decision documentation** - Capturing why decisions were made
- **Retrospectives** - Analyzing completed work and extracting lessons
- **Git history analysis** - Generating reports from commit history
- **Knowledge preservation** - Ensuring critical information isn't lost

**Best Practices**

- Focus on the "why" behind decisions, not just the "what"
- Review completed tasks and extract patterns worth documenting
- Keep CHANGELOG entries user-focused and understandable
- Link decisions to their context (ADRs, issues, discussions)
- Make history searchable and accessible for future team members

---

## Choosing the Right Role

Not sure which role to use? Ask yourself:

- **Coordinating work across agents?** → Administrator
- **Designing system architecture?** → Architect
- **Writing code and implementing features?** → Builder
- **Creating or running tests?** → Tester
- **Writing documentation?** → Documentarian
- **Designing user interfaces?** → Designer
- **Reviewing code or security?** → Inspector
- **Deploying or managing infrastructure?** → Operator
- **Documenting project history and decisions?** → Historian

For more details on working with agents, see the [CLI Reference](reference.md) and [Usage Guide](usage.md).

