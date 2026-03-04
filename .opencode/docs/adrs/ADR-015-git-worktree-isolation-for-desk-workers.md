# ADR-015: Git Worktree Isolation for Desk Workers

**Status:** PROPOSED
**Date:** 2026-03-04
**Deciders:** Tucker (Director), Kothar (Architect, Mission #191 stellar-cipher)
**Related ADRs:** ADR-013 (Site-nine as OpenCode Integration Platform), ADR-014 (Message-Driven Coordination)
**Task:** ARC-H-0251


## Context

### Current State

All desk-mode workers (background OpenCode agents launched via `worker_spawn` or `s9 summon --desk`) run from
the same working directory: the repo root. The `DeskWorker` class in
`src/site_nine/workers/desk_worker.py` does not set a `cwd` parameter on `subprocess.Popen`, so every
`opencode run` invocation inherits the shell's current directory, which is always the project root.

`worker_spawn.py` does set `cwd=str(repo_root)` when launching `desk_worker.py`, but `desk_worker.py` in
turn hard-codes no `cwd` on its own `opencode run` calls — they all run from whatever directory the
`desk-worker` process inherited.

This means:

1. Every worker shares a single working tree and git index
2. Workers doing file edits can overwrite each other's changes
3. A worker mid-way through a multi-file refactor cannot coexist with another that is also editing files
4. `git checkout`, staging, and commits in one worker affect the state visible to all others
5. Long-running tasks that span multiple `opencode run` invocations share the same git state

### Why This Matters Now

The message-driven coordination model in ADR-014 is designed for parallel worker execution. An Admin
assigns independent tasks to multiple workers and coordinates their results. In practice, this is
constrained to tasks that do not touch the filesystem simultaneously, because git state is shared.

The canonical motivating case: an Admin dispatches an Engineer to implement a feature on a new branch
while simultaneously dispatching a Tester to run the existing test suite on main. With a shared working
tree, the Engineer's `git checkout -b feat/new-feature` immediately changes what the Tester sees.

### What Git Worktrees Provide

`git worktree add` creates an additional linked working tree for an existing repository. Each worktree:

- Has its own checkout of a branch (or any commit ref)
- Has its own independent index (staging area)
- Has its own `HEAD`
- Shares the object store, refs, and history with the main worktree
- Is listed by `git worktree list` and can be removed with `git worktree remove`

This provides exactly the isolation needed: each worker operates in its own directory on its own branch,
while all workers share the same git history, remote configuration, and object store.


## Problem Statement

The site-nine agent system needs a model for assigning isolated git working environments to desk workers
such that:

1. **Multiple workers can operate in parallel** without filesystem or git state conflicts
2. **Each worker's branch work is contained** until explicitly merged or submitted
3. **Workers can be cleaned up deterministically** when their mission ends
4. **The shared database and `.opencode/` tooling remain accessible** from every worker's worktree
5. **`find_opencode_dir()` continues to work** — it walks up from CWD; each worktree must contain a
   `.opencode/` directory that resolves to the shared database


## Decision

We will adopt **per-mission git worktrees for desk workers**. Each desk-mode worker mission is assigned
a dedicated git worktree for the duration of its work. The worktree is:

- Created by `worker_spawn.py` before the first `opencode run` is invoked for that worker
- Placed at: `<repo-root>/../.s9-workers/<mission-id>/`
- Checked out on a new branch: `worker/<mission-id>/<role-slug>`
- Passed as `cwd` to all `opencode run` invocations for that worker
- Removed with `git worktree remove` when the worker mission ends

Interactive (non-desk) missions are **not** affected; they run from wherever the Director launched them.


## Proposed Design

### 1. Worktree Lifecycle

#### Creation

A new `src/site_nine/workers/worktree.py` module provides the lifecycle functions. The worktree is
created before `DeskWorker.initialize()` is called:

```python
import os
import shutil
import subprocess
from pathlib import Path


def provision_worktree(repo_root: Path, mission_id: int, role: str, base_branch: str | None = None) -> Path:
    """
    Create a git worktree for a worker mission.

    Args:
        repo_root:    Project root directory (parent of .opencode/)
        mission_id:   Database mission ID — used for unique path and branch name
        role:         Worker role slug (lowercase, e.g. "engineer")
        base_branch:  Branch to base the worktree on (defaults to current HEAD)

    Returns:
        Path to the new worktree directory
    """
    worktree_dir = repo_root.parent / ".s9-workers" / str(mission_id)
    branch_name  = f"worker/{mission_id}/{role.lower()}"

    cmd = ["git", "worktree", "add", "-b", branch_name, str(worktree_dir)]
    if base_branch:
        cmd.append(base_branch)

    subprocess.run(cmd, cwd=repo_root, check=True)

    # Point shared mutable state at the canonical locations
    link_shared_dirs(worktree_dir, repo_root)
    link_venv(worktree_dir, repo_root)

    return worktree_dir
```

#### Shared-State Symlinks

The `.opencode/` directory is committed to the repository and is therefore checked out as a real
directory in every worktree. This is correct for tools, skills, docs, and commands — each worktree gets
its own independent copy of those files, which is desirable (the worker can edit them without affecting
the main tree).

However, two subdirectories contain **shared mutable state** that must not be duplicated:

| Directory | Reason |
|---|---|
| `.opencode/data/` | Contains `project.db` — the single source of truth for all missions, tasks, and messages |
| `.opencode/work/` | Contains mission files, epic files, and task files shared across agents |

After the worktree is checked out, `provision_worktree()` replaces these with symlinks:

```python
def link_shared_dirs(worktree_path: Path, repo_root: Path) -> None:
    """Replace .opencode/data/ and .opencode/work/ with symlinks to the main worktree."""
    for subdir in ("data", "work"):
        worker_dir    = worktree_path / ".opencode" / subdir
        canonical_dir = repo_root    / ".opencode" / subdir

        if worker_dir.exists() and not worker_dir.is_symlink():
            shutil.rmtree(worker_dir)
        elif worker_dir.is_symlink():
            worker_dir.unlink()

        os.symlink(canonical_dir, worker_dir)
```

This ensures:
- `find_opencode_dir()` walks up from the worktree root and finds `.opencode/` — no code change needed
- `get_db_path()` resolves to `<worktree>/.opencode/data/project.db`, which is a symlink to the
  canonical database — Python's `Path` and SQLite follow symlinks transparently
- `validate_path_within_project()` works correctly: it calls `get_project_root()` which calls
  `find_opencode_dir()`, giving the worktree root as project root; paths like `.opencode/work/...`
  resolve within the worktree, which is correct since that subdir is symlinked to the shared location

#### Python Virtual Environment

Tools are invoked via `uv run python3 <script>`. `uv` resolves the virtual environment by walking up
from CWD to find `pyproject.toml`. Each worktree contains a checked-out copy of `pyproject.toml`, so
`uv` would create a fresh `.venv` per worktree — wasteful and slow on first use.

Solution: symlink the worktree's `.venv` to the main worktree's `.venv`:

```python
def link_venv(worktree_path: Path, repo_root: Path) -> None:
    """Symlink the worker's .venv to the main worktree's .venv."""
    worker_venv    = worktree_path / ".venv"
    canonical_venv = repo_root    / ".venv"

    if worker_venv.exists() and not worker_venv.is_symlink():
        shutil.rmtree(worker_venv)
    elif worker_venv.is_symlink():
        worker_venv.unlink()

    os.symlink(canonical_venv, worker_venv)
```

#### Usage (During Worker Lifetime)

`DeskWorker` passes `self.worktree_path` as `cwd` to every `opencode run` subprocess invocation:

```python
# In DeskWorker.initialize():
cmd = ["opencode", "run", "--format", "json", "--model", self.model, init_message]
process = subprocess.Popen(cmd, cwd=str(self.worktree_path or self.repo_root), ...)

# In DeskWorker.process_message():
cmd = ["opencode", "run", "--session", self.session_id, "--model", self.model, message.body]
process = subprocess.Popen(cmd, cwd=str(self.worktree_path or self.repo_root), ...)
```

Because OpenCode sets `context.worktree` to the process's working directory, all tool invocations
automatically resolve paths relative to the worktree. No changes to tool implementations are needed.

#### Cleanup (At Worker Shutdown)

`DeskWorker.handle_shutdown()` removes the worktree after the mission ends:

```python
def cleanup_worktree(self) -> None:
    if self.worktree_path and self.worktree_path.exists():
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(self.worktree_path)],
            cwd=str(self.repo_root),
            check=False,  # best-effort — do not block shutdown on failure
        )
        self.worktree_path = None
```

`--force` is used intentionally: workers that are terminated abruptly should not leave debris.
Any work the Director wants to preserve must be committed (to the worker's branch) before
termination is signalled. The Admin receives the branch name in the completion message and can
cherry-pick or merge at their discretion.

### 2. Mission ID Sequencing

There is a sequencing constraint: the worktree must be named (and created) using the mission ID, but
the mission ID is assigned by `mission_init` during the worker's first `opencode run` invocation — which
happens inside the worktree.

**Solution: use a UUID-named staging directory, rename after mission ID is known.**

```python
# worker_spawn.py

import uuid

staging_name = f"pending-{uuid.uuid4().hex[:8]}"
staging_path = repo_root.parent / ".s9-workers" / staging_name

# 1. Create worktree with a provisional directory name and branch
provisional_branch = f"worker/pending-{staging_name.split('-')[1]}/{role.lower()}"
subprocess.run(
    ["git", "worktree", "add", "-b", provisional_branch, str(staging_path), base_branch or "HEAD"],
    cwd=str(repo_root), check=True
)
link_shared_dirs(staging_path, repo_root)
link_venv(staging_path, repo_root)

# 2. Launch DeskWorker from staging_path
worker = DeskWorker(role=role, worktree_path=staging_path, repo_root=repo_root, ...)
worker.initialize()  # runs opencode run; mission_init creates the DB record

# 3. Rename directory and branch to use the real mission ID
final_path = repo_root.parent / ".s9-workers" / str(worker.mission_id)
final_branch = f"worker/{worker.mission_id}/{role.lower()}"

staging_path.rename(final_path)
subprocess.run(
    ["git", "branch", "-m", provisional_branch, final_branch],
    cwd=str(repo_root), check=True
)
subprocess.run(
    ["git", "worktree", "repair", str(final_path)],
    cwd=str(repo_root), check=True
)
worker.worktree_path = final_path

# 4. Persist worktree_path on the mission record
db.execute_update(
    "UPDATE missions SET worktree_path = :path WHERE id = :id",
    {"path": str(final_path), "id": worker.mission_id}
)
```

`git worktree repair` re-links the worktree metadata after the directory rename. This is a standard
supported operation (`git help worktree`).

### 3. Database Schema Change

One new column on the `missions` table (added via migration):

```sql
ALTER TABLE missions ADD COLUMN worktree_path TEXT;
-- NULL for interactive missions and workers using isolated=false
-- Non-NULL for isolated desk workers; cleared (set to NULL) after cleanup
```

`s9 doctor` uses this column to detect stale entries:
- `worktree_path IS NOT NULL` and mission `status = 'ENDED'` → cleanup was incomplete
- `worktree_path IS NOT NULL` and directory no longer exists → already cleaned up, clear the column

### 4. `worker_spawn.py` Path Resolution in Worktrees

`worker_spawn.py` currently resolves `repo_root` as:

```python
tool_dir = Path(__file__).resolve().parent   # .opencode/tools/
repo_root = tool_dir.parent.parent           # two levels up
```

When `worker_spawn.py` is executing inside an agent that is itself in a worktree, `__file__` resolves
to the worktree's `.opencode/tools/worker_spawn.py`. `parent.parent` gives the worktree root —
which is not the repo root (it is `../.s9-workers/<id>/`).

The fix: walk up from `__file__` using `find_opencode_dir()` logic, then find the **main** worktree
root via `git worktree list --porcelain`:

```python
def get_main_worktree_root() -> Path:
    """Return the path of the main (first) git worktree, regardless of CWD."""
    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=Path(__file__).parent,
        capture_output=True, text=True, check=True
    )
    # First "worktree" line is always the main worktree
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            return Path(line[len("worktree "):].strip())
    raise RuntimeError("Could not determine main worktree path")
```

This is used wherever `worker_spawn.py` needs the canonical repo root (for creating new worktrees,
for locating `desk_worker.py`, and for `cwd` of the spawned worker process).

### 5. Branch Strategy

| Event | Action |
|---|---|
| Worker spawned | `worker/<id>/<role>` branch created from Admin's current branch |
| Worker works | Commits accumulate on the worker's branch |
| Worker task complete | Worker notifies Admin via `worker_message` with branch name |
| Admin reviews | Can diff, cherry-pick, or merge the worker's branch |
| Worker terminated | Worktree removed with `--force`; **branch is kept** |
| Cleanup | Director or `s9 worker cleanup` deletes orphaned worker branches |

Worker branches are **not** deleted at worktree removal. This preserves the Admin's ability to review
commits from a recently terminated worker. The `s9 doctor` command surfaces orphaned worker branches
(branch present, no corresponding ACTIVE mission) for cleanup.

Base branch is captured at spawn time via:

```python
base_branch = subprocess.run(
    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
    cwd=str(repo_root), capture_output=True, text=True, check=True
).stdout.strip()
```

### 6. `worker_spawn` Tool: `isolated` Flag

Not all workers need isolation. Read-only tasks (test runs, reports, inspections) add overhead without
benefit. The `worker_spawn` tool accepts an optional `isolated` flag (default: `true`):

```typescript
// worker_spawn.ts — new optional arg
isolated: tool.schema
  .boolean()
  .optional()
  .describe(
    "If true (default), worker runs in a dedicated git worktree on its own branch. " +
    "Set false for read-only tasks that do not need file isolation."
  ),
```

When `isolated: false`, the worker runs from the repo root (current behavior). Appropriate for:
- Read-only tasks (running tests, generating reports, reviewing code)
- Tasks that must see the current checked-out state of the main branch
- Debugging and investigative work

### 7. `s9 doctor` Extensions

Two new checks are added:

1. **Stale worktrees** — `worktree_path IS NOT NULL` and (`status = 'ENDED'` or directory absent):
   ```
   ⚠ Stale worktree: mission #42 (ended 3h ago), path still set: ../.s9-workers/42/
   ```

2. **Orphaned worker branches** — `git worktree list` shows no worktree for a `worker/*` branch,
   and no ACTIVE mission matches the ID in the branch name:
   ```
   ⚠ Orphaned worker branch: worker/42/engineer (no active mission #42)
   ```

A new `s9 worker cleanup [--all | --mission-id N]` sub-command removes stale worktrees (if the
directory still exists) and deletes orphaned branches.


## Consequences

### Positive

- **True parallel work**: Workers editing files concurrently without conflict
- **Branch isolation**: Each worker's commits are contained until Admin reviews and merges
- **Clean git history**: Worker branches are clearly namespaced as `worker/<id>/<role>`
- **No tool contract changes**: `context.worktree` already drives path resolution; tool code is unchanged
- **Transparent to agents**: Agents have no knowledge of being in a worktree; `find_opencode_dir()`
  simply works because `.opencode/` is present in the worktree root
- **Deterministic cleanup**: Worktrees are removed at shutdown; stale ones surface in `s9 doctor`

### Negative / Trade-offs

- **Disk overhead**: Each worktree is a full working-tree checkout (~same as repo size). Workers that
  do not need file isolation should use `isolated: false`.
- **Spawn latency**: `git worktree add` + directory rename + `git worktree repair` adds ~1–3s to worker
  initialization. Acceptable as a one-time setup cost.
- **Rename/repair step**: The UUID-to-mission-ID rename requires `git worktree repair`. This is a
  supported operation but adds complexity.
- **Symlink fragility**: The `.opencode/data/`, `.opencode/work/`, and `.venv/` symlinks are broken by
  `git clean -fdx` inside the worktree. Worker agents must not run `git clean`.
- **`worker_spawn.py` path resolution fix required**: Without the `get_main_worktree_root()` fix, a
  worker spawning sub-workers (an Admin in a worktree) will compute the wrong repo root and may create
  worktrees inside the wrong directory. This fix must ship before nested spawning is used.
- **Merge responsibility**: Workers never auto-merge; the Admin must review and integrate. This is
  intentional but adds coordination overhead.

### Not Changed

- Interactive (non-desk) missions: unaffected
- Shared database: all workers continue to share `project.db` via symlink
- Tool TypeScript and Python implementations: unchanged
- `context.worktree` semantics: unchanged; OpenCode continues to pass the worker's CWD


## Implementation Plan

### Phase 1: Infrastructure

**Tasks:**
1. Add `worktree_path` column to `missions` table (DB migration + schema.sql update)
2. Implement `src/site_nine/workers/worktree.py` with:
   - `provision_worktree()`
   - `link_shared_dirs()`
   - `link_venv()`
   - `cleanup_worktree()`
   - `get_main_worktree_root()`
3. Write unit tests using a temp git repo (pytest + `tmp_path`)

**Acceptance criteria:** `provision_worktree()` creates a valid worktree with correct symlinks; DB
migration runs without error on the existing database.

### Phase 2: DeskWorker Integration

**Tasks:**
1. Add `worktree_path: Path | None` and `repo_root: Path` parameters to `DeskWorker.__init__()`
2. Pass `cwd=self.worktree_path or self.repo_root` to all `subprocess.Popen` calls in `initialize()`,
   `process_message()`, and `handle_shutdown()`
3. Add `cleanup_worktree()` call at the end of `handle_shutdown()`, before `SystemExit`

**Acceptance criteria:** A desk worker started manually with a pre-provisioned worktree runs correctly;
shutdown removes the worktree; tools resolve paths correctly from the worker's CWD.

### Phase 3: `worker_spawn` Integration

**Tasks:**
1. Add `get_main_worktree_root()` to `worktree.py`; update `worker_spawn.py` to use it instead of
   `tool_dir.parent.parent`
2. Implement the UUID-staging → mission-ID rename flow in `worker_spawn.py`
3. Add `isolated: bool = True` argument to `worker_spawn.py` and `worker_spawn.ts`
4. Store `worktree_path` on the mission record after rename
5. Pass `worktree_path` and `repo_root` through to `DeskWorker`

**Acceptance criteria:** `worker_spawn({ role: "Engineer" })` creates a desk worker in an isolated
worktree; `worker_spawn({ role: "Tester", isolated: false })` creates a worker in the repo root
(current behavior); an Admin agent running inside a worktree can spawn sub-workers correctly.

### Phase 4: `s9 doctor` Extensions

**Tasks:**
1. Stale worktree detection: query `worktree_path IS NOT NULL` with `status = 'ENDED'` or missing path
2. Orphaned branch detection: cross-reference `git worktree list` with active missions
3. `s9 worker cleanup [--all | --mission-id N]`: remove stale worktrees + delete orphaned branches

**Acceptance criteria:** `s9 doctor` reports stale worktrees; `s9 worker cleanup` removes them;
`git worktree list` returns to baseline after cleanup.

### Phase 5: Testing and Documentation

**Tasks:**
1. End-to-end integration test: Admin spawns two Engineers in parallel; both edit different files;
   Admin merges both branches; no conflicts
2. Write `.opencode/docs/guides/worker-worktrees.md` guide for Admin agents
3. Update `mission-start` skill to note that isolated desk workers run in dedicated worktrees
4. Update `worker_spawn` tool description to mention the `isolated` flag and branch naming

**Acceptance criteria:** Integration test passes; documentation accurately reflects the implemented
system.


## Alternatives Considered

### A: No Isolation (Status Quo)

Workers share the repo root. Parallel file editing is serialized by convention — Admins must not
dispatch concurrent file-editing tasks. Acceptable at the current level of parallelism but fails as
ADR-014 message-driven orchestration is used more aggressively.

### B: Full `git clone` Per Worker

Each worker gets a full `git clone`. Provides strong isolation but is expensive in disk space and
requires push/pull to share work. Overkill for intra-session coordination within a single project.

### C: Docker Container Per Worker

Each worker runs in a container with the repo bind-mounted. Strong process isolation but requires
Docker, adds operational complexity, and introduces latency that conflicts with the lightweight
design philosophy of site-nine.

### D: Sparse Checkout Per Worker

Use `git sparse-checkout` to limit each worker to a subset of the tree. Reduces disk overhead but
adds configuration complexity and does not eliminate the git-index sharing problem — branch isolation
is still needed, which worktrees already provide.

### E: Bare Repo with Worktrees

Convert the repo to a bare clone and treat all checkouts as worktrees (the approach described in the
Medium article). This is cleaner from a git-model perspective but requires changing the existing repo
layout, which is a large disruption. We adopt the worktree approach without the bare-repo conversion.


## References

- **ADR-013**: Site-nine as OpenCode Integration Platform — established `context.worktree` as the
  path resolution mechanism for tools
- **ADR-014**: Message-Driven Coordination Architecture — the coordination model motivating parallel workers
- **`DeskWorker` implementation**: `src/site_nine/workers/desk_worker.py`
- **`find_opencode_dir()` / `validate_path_within_project()`**: `src/site_nine/core/paths.py`
- **`worker_spawn` tool**: `.opencode/tools/worker_spawn.py`, `.opencode/tools/worker_spawn.ts`
- **Database schema**: `src/site_nine/data/schema.sql`
- **Git worktree documentation**: `git help worktree`
- **Medium article**: https://medium.com/@mabd.dev/git-worktrees-the-secret-weapon-for-running-multiple-ai-coding-agents-in-parallel-e9046451eb96
