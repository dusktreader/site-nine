# Epic Files

Each epic generates a markdown file at `.opencode/work/epics/{EPIC_ID}.md`. These files provide human-readable documentation of the epic's status, progress, and subtasks.


## File Location and Naming

Epic files use a consistent naming pattern based on the epic ID. For example, epic `EPC-H-0001` creates the file `.opencode/work/epics/EPC-H-0001.md`. This predictable structure makes it easy to find epic documentation and allows tools to automatically locate the correct file.


## File Structure

Epic markdown files contain several sections that serve different purposes:


### Auto-Generated Sections

The file header, progress indicators, and subtasks table are all automatically generated and updated by the system. Any manual edits to these sections will be overwritten when the file regenerates (which happens whenever epic or task status changes).

The header includes the epic's current status (TODO, UNDERWAY, COMPLETE, or ABORTED), priority level, creation timestamp, and last update timestamp. The progress section shows task completion as both percentage and count, with a visual progress bar. The subtasks table lists all tasks belonging to the epic with their IDs, titles, current statuses, assigned roles, and priorities.


### Director-Editable Sections

Several sections are preserved when the file regenerates, allowing Directors and agents to add context and planning information:

**Description** - High-level summary of what the epic is trying to accomplish. This is typically set during epic creation but can be updated as understanding evolves.

**Goals** - Bullet list of specific objectives the epic aims to achieve. Goals provide context for agents working on subtasks and help everyone understand the big picture.

**Success Criteria** - Measurable outcomes that define when the epic is truly complete. These might include technical requirements ("All endpoints passing integration tests"), quality gates ("Security audit passed"), or deliverables ("Documentation complete and published").

**Notes** - Free-form section for recording decisions, blockers, important discussions, or any other context that doesn't fit elsewhere. This becomes particularly valuable for historical reference when reviewing completed epics.


## When Files Regenerate

Epic files automatically regenerate whenever epic status changes, task status changes for any subtask, tasks are added to or removed from the epic, or epic metadata (title, description, priority) is updated.

This automatic regeneration ensures the file always reflects current reality without requiring manual updates. The regeneration process preserves Director-editable sections while updating the auto-generated content.


## Reading Epic Files

Epic files are designed to be human-readable. Directors can open them directly to review epic status, understand what tasks remain, see which tasks are blocked or in progress, and read goals, success criteria, and notes added during planning.

Agents also read epic files when working on related tasks, giving them context about the larger initiative they're contributing to.


## Editing Epic Files

Directors can edit the Description, Goals, Success Criteria, and Notes sections directly in their text editor. These edits are preserved across file regenerations. However, avoid editing the header, progress, or subtasks sections - those changes will be lost when the file next regenerates.

The typical workflow is to add goals and success criteria during initial planning (often with an Architect agent's help), update notes throughout execution as decisions are made or blockers emerge, and potentially refine the description if understanding of the initiative changes.


## Example Epic File

Here's what a typical epic file looks like:

```markdown
# Epic EPC-H-0001: User Authentication System

**Status:** 🚧 UNDERWAY
**Priority:** HIGH
**Created:** 2026-02-04 10:30:00
**Updated:** 2026-02-04 15:45:00

## Progress

**Tasks:** 3/5 complete (60%)
[████████████████████░░░░░░░░░░] 60%

## Subtasks

| Task ID    | Title                      | Status      | Role          | Priority |
|------------|----------------------------|-------------|---------------|----------|
| ARC-H-0015 | Design auth architecture   | ✅ COMPLETE | Architect     | HIGH     |
| ENG-H-0016 | Implement login endpoint   | ✅ COMPLETE | Engineer      | HIGH     |
| ENG-H-0017 | Implement registration     | 🔵 UNDERWAY | Engineer      | HIGH     |
| TST-M-0018 | Write auth tests           | ⬜ TODO     | Tester        | MEDIUM   |
| DOC-M-0019 | Document auth API          | ⬜ TODO     | Documentarian | MEDIUM   |

## Description

Implement complete user authentication including login, registration, and password reset

## Goals

- Secure user authentication with JWT tokens
- Password reset flow via email
- Account registration with email verification
- Session management

## Success Criteria

- All auth endpoints fully implemented and tested
- Security audit passed
- Documentation complete
- Integration tests passing

## Notes

### 2026-02-04 11:00 - Architecture Decision

Decided to use JWT tokens instead of session cookies for better scalability with future microservices architecture.

### 2026-02-04 14:30 - Blocker Resolved

Email service integration issue resolved. Password reset flow can now proceed.
```


## File Sync

Epic files normally stay synchronized automatically, but in rare cases where manual regeneration is needed, agents can sync files through conversation:

```
Director: The epic file seems out of sync
Agent: I'll regenerate the epic files to sync them with the database
```

This is rarely necessary but available if file and database state somehow diverge.


## Next Steps

Now that you understand how epics work, explore the [overview](overview.md) for conceptual information, learn about [planning epics](planning.md) with agents, or dive into [tracking progress](tracking.md) on active initiatives.
