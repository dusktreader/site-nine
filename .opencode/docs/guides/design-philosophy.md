# Design Philosophy

## Core Principles

### 1. Bootstrap, Don't Prescribe

**Philosophy:** site-nine provides a starting point, not a rigid framework.

**What this means:**
- Templates are suggestions, not requirements
- Users can modify any generated file
- No "magic" - everything is readable Markdown and SQLite
- Easy to eject: Just keep using the `.opencode/` structure manually

**Example:**
```bash
# site-nine generates standard agent roles
s9 init  # Creates Administrator, Builder, Tester, etc.

# But you can add your own
echo "# SecurityAuditor" > .opencode/agents/security-auditor.md
```

---

### 2. Agent-Friendly First

**Philosophy:** Every file is designed to be parsed and understood by AI agents.

**What this means:**
- Markdown format (universal, LLM-friendly)
- Clear structure (headings, lists, code blocks)
- Consistent conventions (task IDs, commit formats, session file names)
- Rich context (guides, examples, procedures)

**Why:**
- Agents work best with structured, readable documentation
- Reduces hallucination when agents have clear context
- Makes handoffs between agents smoother

**Example:**
```markdown
# Task: BLD-H-0003 - Implement Login

## Objective
Build user authentication system with email/password

## Acceptance Criteria
- [ ] User can register with email
- [ ] User can log in
- [ ] Session management works

## Agent: Azazel (Builder)
## Status: IN_PROGRESS
```

---

### 3. Local-First, Git-Friendly

**Philosophy:** Everything lives in the repo. No external dependencies.

**What this means:**
- All data in `.opencode/` directory
- SQLite database (single file, portable)
- Markdown files for human readability
- Git version control for full history

**Why:**
- **Privacy:** No cloud services, no data leaks
- **Offline:** Works without internet
- **Ownership:** Users control their data
- **Portability:** Clone repo = get everything

**Trade-offs:**
- ✅ Zero config, no accounts needed
- ✅ Works everywhere (local, CI, air-gapped)
- ❌ No real-time collaboration (by design)
- ❌ No web dashboard (future: local web UI)

---

### 4. Convention Over Configuration

**Philosophy:** Sensible defaults, minimal setup required.

**What this means:**
- `s9 init` works with zero config
- Task IDs follow standard format (`ROLE-PRIORITY-NUMBER`)
- Session files follow naming convention (`YYYY-MM-DD.HH:MM:SS.role.name.task.md`)
- Directory structure is predictable

**Example conventions:**
```
Task IDs:     BLD-H-0003 (Builder, High priority, task #3)
              TST-M-0001 (Tester, Medium priority, task #1)

Session files: 2026-02-02.14:30:00.builder.azazel.implement-auth.md

Daemon names:  azazel (first use)
               azazel-ii (second use)
               azazel-iii (third use)
```

**Benefits:**
- Easy to understand at a glance
- Grep-friendly (search by role, priority, agent)
- Sortable by date/time
- Clear audit trail

---

## Key Design Decisions

### Decision 1: CLI Tool vs. Library

**Chosen:** CLI tool (`s9` command)  
**Alternative:** Python library (`import s9`)

**Rationale:**
- **Language agnostic:** Works for Python, TypeScript, Go, Rust projects
- **Better UX:** Command-line is natural for project setup
- **Clear interface:** Commands are discoverable (`s9 --help`)
- **Shell integration:** Easy to use in scripts, CI/CD

**Trade-off:**
- ✅ Works in any environment
- ❌ Can't be imported in Python code (not the goal)

---

### Decision 2: SQLite vs. File-Based Storage

**Chosen:** SQLite for relational data  
**Alternative:** JSON/YAML files

**Rationale:**
- **Relations matter:** Tasks depend on other tasks, agents claim tasks
- **ACID transactions:** Prevent data corruption
- **Query capabilities:** `s9 task search`, `s9 task next` need SQL
- **Integrity:** Foreign keys enforce consistency

**What goes in SQLite:**
- Structured data (tasks, agents, daemon names)
- Relations (task dependencies, agent assignments)
- Metadata (timestamps, status, priority)

**What stays as files:**
- Documentation (task artifacts, session logs)
- Human-readable content (guides, procedures)
- Context for agents (descriptions, notes, learnings)

**Benefits:**
- Best of both worlds: database for data, files for docs
- SQLite is portable (single file)
- Markdown is readable in Git diffs

---

### Decision 3: Jinja2 Templates vs. Static Files

**Chosen:** Jinja2 template engine  
**Alternative:** Copy static files

**Rationale:**
- **Customization:** Inject project name, roles, features
- **Conditional logic:** Enable/disable sections based on config
- **Maintainability:** Update templates, regenerate projects
- **Flexibility:** Users can override templates

**Example:**
```jinja
# Agent: {{ role_name }}

{% if features.session_tracking %}
## Session Tracking
Track your work in `.opencode/work/sessions/`
{% endif %}

{% if features.commit_guidelines %}
## Commit Format
Use conventional commits: `feat:`, `fix:`, `docs:`
{% endif %}
```

**Benefits:**
- One template → many variations
- Easy to add new features without duplicating files
- Users can customize without forking site-nine

---

### Decision 4: 145+ Daemon Names vs. Simple Naming

**Chosen:** Rich mythology-based daemon naming system  
**Alternative:** Simple numbering (Agent1, Agent2, etc.)

**Rationale:**
- **Identity:** Names give agents personality and identity
- **Memorable:** Easier to remember "Azazel fixed auth" than "Agent42 fixed auth"
- **Fun:** Makes development more enjoyable
- **Cultural:** Draws from 8+ mythologies (Greek, Norse, Egyptian, Japanese, etc.)

**How it works:**
- 145+ pre-populated names in database
- Suggests unused names first
- Adds roman numerals for reuse (azazel, azazel-ii, azazel-iii)
- `s9 name suggest Builder` shows unused names for role

**Trade-off:**
- ✅ Memorable, distinctive, fun
- ✅ Rich cultural references
- ❌ Slightly more complex than numbering

---

### Decision 5: Markdown Task Artifacts vs. Database-Only

**Chosen:** Dual storage (database + markdown files)  
**Alternative:** Store everything in database

**Rationale:**
- **Database:** Structured queries, relationships, status tracking
- **Markdown:** Context, notes, learnings, commit history

**What agents write to markdown:**
```markdown
## Implementation Steps

1. Created User model with email/password fields
2. Added bcrypt for password hashing
3. Implemented JWT token generation
4. Added login/register endpoints

## Files Changed
- `src/models/user.py` - User model
- `src/auth/jwt.py` - Token generation
- `tests/test_auth.py` - Auth tests

## Key Learnings
- bcrypt rounds=12 is good balance of security/performance
- JWT expiry should be configurable per environment
```

**Benefits:**
- Git diffs show what changed in tasks
- Rich context for future agents
- Human-readable project history
- Database stays clean (no huge text blobs)

---

## Philosophy in Practice

### Example: Task Workflow

**Principle applied:** Convention + Agent-Friendly + Local-First

```bash
# 1. Create task (standard ID format)
s9 task create --title "Add rate limiting" --role Builder --priority HIGH
# → Creates BLD-H-0004 in database + markdown file

# 2. Agent claims task
s9 task claim BLD-H-0004 --agent azazel
# → Updates database, agent can now work on it

# 3. Agent documents work in markdown
# .opencode/work/tasks/BLD-H-0004.md gets updated with:
# - Implementation steps
# - Files changed
# - Commit SHAs
# - Key learnings

# 4. Agent completes task
s9 task close BLD-H-0004 --status COMPLETE
# → Updates database, preserves markdown history

# 5. Generate changelog
s9 changelog --since 2026-02-01
# → Reads completed tasks from database + markdown
```

---

## Trade-offs We Made

### Local-First = No Real-Time Collaboration

**Chosen:** Local `.opencode/` directory  
**Sacrificed:** Real-time team collaboration

**Why:**
- Privacy and ownership matter more
- Git provides async collaboration
- Most development is solo or small team
- Future: Optional cloud sync

---

### CLI Tool = No Programmatic API

**Chosen:** Command-line interface  
**Sacrificed:** Python import API

**Why:**
- CLI is universal (works for all languages)
- Shell commands are composable
- API surface would be huge
- Future: HTTP API mode (`s9 serve`)

---

### Rich Metadata = Larger Database

**Chosen:** Comprehensive task/agent/session tracking  
**Sacrificed:** Minimal storage

**Why:**
- Context is valuable for agents
- History helps debugging
- SQLite is efficient (typical DB: <1MB)
- Disk space is cheap

---

## Anti-Patterns to Avoid

### ❌ Don't Make site-nine a Replacement for Git

**Bad:** Store code in site-nine database  
**Good:** Use site-nine for orchestration, Git for code

site-nine tracks *work* (tasks, sessions), not *code*.

---

### ❌ Don't Make Tasks Too Granular

**Bad:** "Fix typo in line 42"  
**Good:** "Improve error messages in auth module"

Tasks should represent meaningful units of work.

---

### ❌ Don't Skip Documentation in Task Artifacts

**Bad:** Close task with just "Done"  
**Good:** Document what changed, why, learnings

Future agents (and humans) benefit from context.

---

## Success Metrics

### How do we know site-nine is working?

1. **Time to first agent session:** <5 minutes from `s9 init`
2. **Task completion rate:** >80% of claimed tasks get completed
3. **Documentation quality:** Task artifacts have useful context
4. **Adoption:** Teams use it for >60% of development work
5. **Satisfaction:** Engineers find it helpful, not burdensome

---

## Future Philosophy

### Planned Improvements

1. **Plugin System**
   - Allow community-contributed agent roles
   - Custom templates without forking
   - Extension points for new commands

2. **Optional Cloud Sync**
   - Opt-in sync for teams
   - Keep local-first default
   - Privacy controls

3. **Enhanced Tooling**
   - Local web dashboard
   - Task dependency visualization
   - Timeline views

### Principles We Won't Compromise

- ✅ Local-first remains default
- ✅ No required external services
- ✅ Git-friendly file formats
- ✅ Agent-friendly documentation
- ✅ Privacy and data ownership

---

## Summary

site-nine is designed to:
- **Bootstrap** AI agent orchestration quickly
- **Support** agents with structured, readable files
- **Preserve** work history in Git
- **Remain** flexible and customizable
- **Respect** user privacy and control

All design decisions support these goals.
