# ADR-017: Unified Possession Journal

**Status:** PROPOSED
**Date:** 2026-04-08
**Deciders:** Tucker (Director), Phenex (Engineer, Possession #23)
**Related ADRs:** ADR-016 (Minion Worker Robustness and Observability)
**Supersedes:** ADR-016 Fix 1 (per-possession journal for minion workers only)


## Context

ADR-016 Fix 1 (implemented in ENG-H-0258) introduced `DeskWorkerJournal`: a
per-possession markdown journal written by `minion_worker.py` during background
worker execution. This replaced the role-scoped flat log file with a structured,
timestamped, crash-safe journal inside `.opencode/work/possessions/`.

The implementation works for minion workers, but it creates a two-tier system:

**Interactive possessions** use a manually maintained possession file:
- Path computed in `possession_daemon_record` and stored in `possessions.possession_log`
- File is never created programmatically; the agent (via the `possession-start` skill)
  writes free-form prose to it at its own discretion
- Format is unstructured: no consistent timestamps, no guaranteed front-matter
- No flush discipline; entries are written when the agent remembers to write them
- The file may be empty or missing entirely if the agent skips it

**Minion workers** use `DeskWorkerJournal`:
- Opened immediately at worker startup with a pending UUID-keyed path
- Renamed to a final possession-scoped path after `possession_daemon_record` completes
- Front-matter and section headings written programmatically
- Every entry timestamped and flushed immediately
- Shutdown section written on clean exit; journal left at last entry on crash

The result is that minion possession journals are structured and reliable, while
interactive possession journals are optional and freeform. Both are supposed to be
the authoritative record of what a possession did.

There is also a naming inconsistency. Interactive possession files use a `codename`
component that does not appear in minion journal filenames. Minion journals use
`possession_id` instead. The `.journal.md` suffix distinguishes them, but the
directory still mixes two filename conventions.

The `codename` field itself is worth reconsidering. It was introduced as a
human-friendly label for the possession, but the values it produces (operation
codenames from an Ars Goetia tradition) are esoteric and not immediately
meaningful. A better friendly identifier already exists in the system: the daemon's
incarnation number. `daemons.incarnations` is incremented atomically per daemon in
`possession_daemon_record` when a daemon is claimed. Converting that counter to a
Roman numeral at claim time gives each possession a label like `Phenex XIV` that is
readable, meaningful (the fourteenth time Phenex was summoned), and computed
deterministically from data already in the DB.

The right fix is to converge on a single journal system that works for both
possession types, and to replace the codename field with a Roman numeral incarnation
label derived from `daemons.incarnations` at claim time.


## Decision

Replace the current two-tier system with a single `PossessionJournal` class used
by all possessions, interactive and minion alike. The journal is opened
programmatically, not by the agent, and structured entries are written by the
tools themselves at key lifecycle points. Replace the `codename` field with a
Roman numeral incarnation label computed at daemon claim time.

---

### Roman numeral incarnation label

`possession_daemon_record` already increments `daemons.incarnations` atomically
when a daemon is claimed. The post-increment value is the ordinal of the current
possession for that daemon. Convert it to a Roman numeral immediately and store
it in `possessions.incarnation_label`.

Add `to_roman(n: int) -> str` to `src/site_nine/core/roman.py`. This is a small
pure function with no external dependencies; a lookup-table approach handles any
realistic incarnation count. It is not computed on the fly from the session or
from the agent — the tool computes it, stores it, and returns it. No agent input
required.

```python
# src/site_nine/core/roman.py

_THRESHOLDS = [
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
    (100,  "C"), (90,  "XC"), (50,  "L"), (40,  "XL"),
    (10,   "X"), (9,   "IX"), (5,   "V"), (4,   "IV"),
    (1,    "I"),
]

def to_roman(n: int) -> str:
    """
    Convert a positive integer to its Roman numeral representation.

    Parameters:
        n: A positive integer (1 or greater).
    """
    if n < 1:
        raise ValueError(f"Roman numerals are defined for positive integers only, got {n}")
    result = []
    for value, numeral in _THRESHOLDS:
        while n >= value:
            result.append(numeral)
            n -= value
    return "".join(result)
```

The session title format becomes `Phenex XIV - Engineer`. The `codename` column
is removed from `possessions`; `incarnation_label` replaces it.
`possession_rename_session` reads `incarnation_label` from the DB instead of
`codename`. The DB schema migration is a simple `ALTER TABLE` plus a one-time
backfill for any active possessions.

---

### Journal class

Rename `DeskWorkerJournal` to `PossessionJournal` and move it to
`src/site_nine/possessions/journal.py`. The public API is unchanged except:

- `open_pending(possessions_dir, role)` becomes the shared factory for both
  interactive and minion startup
- `make_final_path(...)` drops the `.journal.md` suffix distinction; all
  possession files use the same naming convention (see below)

---

### Unified filename convention

All possession files, interactive and minion, use:

```
.opencode/work/possessions/YYYY-MM-DD.HH-MM-SS.<role>.<daemon>.<incarnation_label>.md
```

Example:
```
2026-04-08.14-23-11.engineer.halphas.XIV.md
```

The `codename` component is replaced by the Roman numeral incarnation label. The
possession ID is not in the filename; it is stored in the front-matter and in
`possessions.possession_log`. The incarnation label is a better human identifier:
readable, meaningful (the fourteenth summoning of this daemon), and unique within
a daemon's history.

The pending filename convention is:
```
.opencode/work/possessions/possession-<uuid8>.pending.md
```

The role and daemon components are omitted from the pending name since neither is
known until `possession_daemon_record` completes and the pending file is renamed.

---

### Tool integration

The journal lifecycle is driven by the possession tools, not by the agent:

**`possession_init`:** Opens a pending journal immediately after creating the
possession record. Writes the first entry:
```
- **HH:MM:SS** Possession initialized (session: ses_abc123)
```
Returns the pending journal path alongside the possession ID so downstream tools
can locate the file.

**`possession_daemon_record`:** Renames the pending journal to its final path once
the daemon and possession timestamps are known. Writes the front-matter header and
the daemon assignment entry:
```
- **HH:MM:SS** Daemon assigned: Halphas (Engineer)
```
Stores the final path in `possessions.possession_log`.

**`task_claim`:** Appends a structured entry:
```
- **HH:MM:SS** Task claimed: ENG-H-0150 — Implement feature X
```

**`task_close`:** Appends a structured entry with final status:
```
- **HH:MM:SS** Task closed: ENG-H-0150 — COMPLETE
```

**`possession_end`:** Writes the Shutdown section and final timestamp before
marking the possession ENDED in the database.

Agents may still write free-form notes via a new `journal_append` tool (see
below), but they are no longer responsible for the structural entries.

---

### New `journal_append` tool

Add `.opencode/tools/journal_append.py`:

```
journal_append({ text: "Decided to use approach X because Y" })
```

Looks up the current possession's `possession_log` path from the database,
opens the file in append mode, writes a timestamped bullet entry, and flushes.
No arguments beyond `text` are required; the tool resolves the path from session
context automatically.

This replaces the ad-hoc convention of agents editing their possession file
directly via the Edit tool. Using a dedicated tool ensures consistent formatting
and eliminates the risk of the agent mangling the front-matter.

---

### Minion worker changes

`minion_worker.py` no longer creates a `PossessionJournal` directly. Instead:

- It calls the `possession_init` tool (via `opencode run`) as before; the tool
  opens the pending journal
- It calls `possession_daemon_record` (via `opencode run`) as before; the tool
  renames the journal
- After initialization, `minion_worker.py` looks up `possession_log` from the DB
  and holds a `PossessionJournal` instance pointing to that path for its own
  structured entries (poll cycles, message processing events, heartbeats)

The worker-side structured entries (poll cycle, message processing, heartbeat,
shutdown) stay in `minion_worker.py` because those events happen outside of any
`opencode run` subprocess.

---

### `possession-start` skill changes

The skill no longer instructs the agent to write to the possession file directly.
The structural entries are now written by the tools. The skill still instructs
the agent to use `journal_append` for session-specific notes and decisions.

The "Treat it as a living document" guidance in the skill is updated to describe
`journal_append` usage rather than Edit-based prose writing.


## Alternatives considered

### Keep two separate systems

The simplest option: leave minion workers with `DeskWorkerJournal` and interactive
sessions with manual possession files.

Rejected because the inconsistency causes real problems: agents viewing the
`.opencode/work/possessions/` directory see two different file formats with no
clear relationship between them. Tooling (e.g., the TUI possession screen) would
need to handle both formats separately. Any future feature that reads journal
content (search, summarization, inquisitor checks) must branch on possession type.

### Structured journal for interactive, flat log for minion

Keep interactive possession files freeform but give them better structure via the
`journal_append` tool. Keep minion workers on their own journal format.

Rejected for the same reasons as above: two formats, two code paths, two places
to look.

### Agent-only journal writes (no tool integration)

Add `journal_append` but keep the structural entries agent-written rather than
tool-written.

Rejected because agents forget to write entries, write them inconsistently, or
write them in the wrong format. The structural entries (task claim, task close,
shutdown) have a fixed set of triggers that map directly to tool calls; there is
no reason to delegate them to the agent.


## Consequences

### Positive

- **Single format:** all possession files, interactive or minion, share one
  naming convention and one structural format. The TUI, inquisitor, and any
  future tooling only need to handle one case.
- **Reliable structural entries:** key lifecycle events (daemon assignment, task
  claim, task close, shutdown) are written by tools unconditionally, not by agents
  opportunistically.
- **Meaningful human identifier:** `Phenex XIV` is immediately readable and
  tells you both who and which incarnation, without any lookup table or esoteric
  tradition to decode.
- **Agent cognitive load reduced:** agents call `journal_append` for notes;
  everything else is automatic.
- **Crash-safe for all possessions:** the tool-side journal uses the same
  flush-on-write discipline as the minion worker journal.

### Negative / trade-offs

- **Schema migration:** removing `codename` and adding `incarnation_label`
  requires an `ALTER TABLE` migration and a backfill for any active possessions.
  The codename generation logic can be deleted entirely.
- **Migration of existing files:** possession files in the old format are not
  converted. The directory will contain a mix of old and new formats until the old
  ones age out. Acceptable; possession files are not queried programmatically today.
- **Tool surface grows:** `journal_append` is a new tool agents must know about.
  It replaces a pattern (Edit the possession file) that agents already understand.
  The `possession-start` skill update handles the transition.
- **`possession_daemon_record` complexity increases:** the tool now computes
  the incarnation label, opens/renames a file, and writes to it, in addition to its
  DB work. This is a reasonable addition given it already owns the moment when all
  that information first becomes available.
- **Minion worker pre-init entries remain Python-side:** the worker's earliest
  entries (process start, session ID extraction) are written directly to the
  pending journal by `minion_worker.py`, not via a tool call. This is unchanged
  from the ENG-H-0258 implementation and is an acceptable exception.


## Implementation plan

| Task | Role | Priority | Description |
|---|---|---|---|
| ENG-H-XXXX | Engineer | HIGH | Add `src/site_nine/core/roman.py` with `to_roman()`; DB migration to add `incarnation_label`, drop `codename`; update `possession_daemon_record` to compute and store label |
| ENG-H-XXXX | Engineer | HIGH | Rename `DeskWorkerJournal` to `PossessionJournal`, move to `src/site_nine/possessions/journal.py`; update `make_final_path` to use incarnation label; update pending filename convention |
| ENG-H-XXXX | Engineer | HIGH | Integrate `PossessionJournal` into `possession_init` (open pending) and `possession_daemon_record` (rename, write header with incarnation label) |
| ENG-H-XXXX | Engineer | HIGH | Add `journal_append` tool; update `task_claim` and `task_close` to write journal entries; update `possession_end` to write shutdown section |
| ENG-M-XXXX | Engineer | MEDIUM | Update `minion_worker.py` to look up `possession_log` from DB after init instead of managing its own journal instance |
| ENG-M-XXXX | Engineer | MEDIUM | Update `possession_rename_session` to use `incarnation_label`; update `possession-start` skill to describe `journal_append` usage |
| TST-M-XXXX | Tester | MEDIUM | Tests for `to_roman()`, `PossessionJournal`, tool integration, and concurrent write safety |

Implementation order: DB migration and `to_roman` first (everything else depends on
the label existing), then journal class rename/move, then tool integration, then
minion worker update, then session title and skill updates, then tests.


## References

- `src/site_nine/workers/journal.py` — `DeskWorkerJournal` (to be renamed/moved)
- `src/site_nine/workers/minion_worker.py` — minion worker integration
- `.opencode/tools/possession_init.py` — possession initialization tool
- `.opencode/tools/possession_daemon_record.py` — daemon assignment and label computation
- `.opencode/tools/possession_rename_session.py` — session title tool (reads `codename` today)
- `.opencode/tools/possession_end.py` — possession close tool
- `src/site_nine/data/schema.sql` — database schema
- ADR-016, Fix 1 — per-possession journal for minion workers (superseded by this ADR)
