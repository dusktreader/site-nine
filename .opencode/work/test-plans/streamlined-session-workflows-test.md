# Test Plan: Streamlined Session Workflows

**Created:** 2026-02-03  
**Purpose:** Verify that streamlined session-start and session-end skills work correctly  
**Related Task:** OPR-H-0028  
**Skills Updated:** session-start, session-end

---

## Overview

This test plan verifies that the streamlined session workflows:
- Reduce agent thinking time by 30%+
- Use database-backed handoff commands correctly
- Maintain all essential functionality
- Produce properly formatted mission files

---

## Test 1: Session-Start Workflow

**Objective:** Verify session-start skill works with streamlined instructions

### Setup
1. Start fresh OpenCode session
2. Invoke `/summon <role>` (any role)

### What to Observe

**Step 1 - Dashboard:**
- ✅ `s9 dashboard` runs and shows project status
- ✅ Output is clear and readable

**Step 2 - Role Selection:**
- ✅ Role is accepted from summon parameter OR
- ✅ `s9 mission roles` displays available roles

**Step 3 - Persona Selection:**
- ✅ `s9 name suggest <Role> --count 3` runs
- ✅ Agent presents clear recommendation
- ✅ Agent doesn't get bogged down in verbose explanations

**Step 4 - Register Mission:**
- ✅ `s9 mission start <persona> --role <Role> --task "..."` runs
- ✅ Mission ID returned
- ✅ Mission file created in `.opencode/work/missions/`

**Step 5 - Mythological Background:**
- ✅ Agent shares fun, whimsical paragraph
- ✅ Matches persona's mythology
- ✅ Feels personal and engaging

**Step 6 - Rename Session:**
- ✅ `s9 mission generate-session-uuid` runs
- ✅ UUID captured correctly
- ✅ `s9 mission rename-tui <persona> <Role> --uuid-marker <uuid>` runs
- ✅ OpenCode session renamed successfully

**Step 7 - Check Handoffs:**
- ✅ `s9 handoff list --role <Role> --status pending` runs
- ✅ If handoffs exist, agent can show and accept them
- ✅ If no handoffs, agent continues smoothly

**Step 8 - Check Reviews (Administrator only):**
- ✅ Skipped if not Administrator
- ✅ If Administrator, `s9 review list --status pending` runs

**Step 9 - Ready Message:**
- ✅ Agent presents clear "Mission initialized!" message
- ✅ Message is concise

**Step 10 - Role Dashboard:**
- ✅ `s9 dashboard --role <Role>` runs
- ✅ Agent presents brief summary
- ✅ Agent asks what to work on

### Success Criteria
- [ ] All commands execute successfully
- [ ] Agent thinking time is noticeably faster (estimate 30%+ improvement)
- [ ] No confusion or hesitation from agent
- [ ] Mission file created correctly
- [ ] Session renamed properly
- [ ] Agent doesn't read excessive documentation

### Estimated Time
- **Old workflow:** ~60 seconds of agent thinking
- **New workflow:** ~20-25 seconds of agent thinking
- **Target:** Sub-30 seconds startup time

---

## Test 2: Session-End Workflow

**Objective:** Verify session-end skill works with streamlined instructions

### Setup
1. Use existing mission from Test 1
2. Do some trivial work (edit a file, make a commit)
3. Tell agent to end mission

### What to Observe

**Step 1 - Locate Mission File:**
- ✅ Agent finds mission file quickly
- ✅ No confusion about which file

**Step 2 - Identify Work Completed:**
- ✅ `git status` runs
- ✅ `git log --oneline -10` runs
- ✅ `s9 task mine --mission-id <id>` runs
- ✅ Agent optionally uses `s9 mission summary <id>`

**Step 3 - Update Mission File:**
- ✅ Agent updates Duration
- ✅ Agent fills in Files Changed
- ✅ Agent fills in Outcomes (with ✅ ⚠️ ❌)
- ✅ Agent adds final Work Log entry
- ✅ Agent fills in Next Steps

**Step 4 - Close Tasks:**
- ✅ Agent checks for open tasks
- ✅ `s9 task close <id> --status <status> --notes "..."` runs
- ✅ Task closed successfully

**Step 5 - Complete Handoffs:**
- ✅ If handoff was accepted, `s9 handoff complete <id>` runs
- ✅ If no handoff, step skipped smoothly

**Step 6 - Update Task Artifacts:**
- ✅ Agent verifies task artifacts updated
- ✅ No excessive detail checking

**Step 7 - Final Git Check:**
- ✅ `git status` runs
- ✅ Mission file committed with proper format
- ✅ Commit message includes `[Persona: <Name> - <Role>]`

**Step 8 - End Mission:**
- ✅ `s9 mission end <id>` runs
- ✅ Database updated
- ✅ Mission file frontmatter updated with end_time

**Step 9 - Quality Checks:**
- ✅ Agent optionally runs `make qa`
- ✅ If skipped, no issue

**Step 10 - Goodbye:**
- ✅ Agent presents clear summary
- ✅ Summary includes: duration, files changed, tasks completed
- ✅ Agent shares mythologically appropriate farewell
- ✅ Farewell is creative and matches persona

### Success Criteria
- [ ] All commands execute successfully
- [ ] Agent thinking time is noticeably faster (estimate 30%+ improvement)
- [ ] Mission file properly updated
- [ ] Task closed correctly
- [ ] Handoff completed (if applicable)
- [ ] Mission ended in database
- [ ] Goodbye message is personal and engaging

### Estimated Time
- **Old workflow:** ~90 seconds of agent thinking
- **New workflow:** ~30-40 seconds of agent thinking
- **Target:** Sub-45 seconds closure time

---

## Test 3: Handoff Workflow Integration

**Objective:** Verify handoff commands work in both skills

### Setup
1. Create a test handoff: `s9 handoff create --to-role Tester --task "Test the streamlined workflows" --summary "Verify session-start and session-end work correctly"`
2. Start new mission with Tester role
3. Accept the handoff during session-start
4. Complete work and mark handoff complete during session-end

### What to Observe

**During Session-Start:**
- ✅ `s9 handoff list --role Tester --status pending` shows the handoff
- ✅ Agent asks if user wants to accept
- ✅ `s9 handoff show <id>` displays details clearly
- ✅ `s9 handoff accept <id>` works (requires active mission)
- ✅ Agent summarizes handoff concisely

**During Session-End:**
- ✅ Agent remembers accepted handoff
- ✅ `s9 handoff complete <id>` runs successfully
- ✅ Handoff marked as completed in database

### Success Criteria
- [ ] Handoff discovery works via CLI commands
- [ ] Handoff acceptance smooth and clear
- [ ] Handoff completion works correctly
- [ ] No file manipulation needed
- [ ] Database stays consistent

---

## Test 4: Edge Cases

### Test 4a: Multiple Handoffs
- Create 3 handoffs for same role
- Verify agent lists all three
- Verify agent can show/accept any of them

### Test 4b: No Handoffs
- Start mission with no pending handoffs
- Verify Step 7 skips cleanly
- No error messages or confusion

### Test 4c: Administrator Reviews
- Start mission as Administrator
- Verify Step 8 checks for reviews
- Verify non-Administrator roles skip it

### Test 4d: Incomplete Work
- Start mission, do partial work
- End mission with status PAUSED
- Verify Next Steps filled in appropriately

---

## Overall Success Metrics

**Quantitative:**
- [ ] session-start thinking time reduced by 30%+ (target: <30s)
- [ ] session-end thinking time reduced by 30%+ (target: <45s)
- [ ] Combined skill line count reduced by 50%+ (achieved: 52% and 56%)
- [ ] Zero errors during workflow execution

**Qualitative:**
- [ ] Agent behavior feels faster and more decisive
- [ ] Instructions are clear and actionable
- [ ] No confusion about what to do next
- [ ] Essential functionality preserved
- [ ] User experience improved

---

## Regression Check

**Verify nothing was broken:**
- [ ] Mission files still created correctly
- [ ] Database records accurate
- [ ] Task claiming/closing works
- [ ] Git commits properly formatted
- [ ] Handoff workflow functions end-to-end
- [ ] Session renaming works
- [ ] Role-specific dashboards work

---

## Notes for Tester

**What to look for:**
- Agent speed and responsiveness
- Clear, concise communication
- Proper command execution
- Correct file/database updates
- No verbose explanations that slow things down

**What NOT to expect:**
- Agent should NOT read extensive documentation during startup
- Agent should NOT explain WHY each step matters
- Agent should NOT provide redundant examples
- Agent should NOT get bogged down in conditionals

**Red flags:**
- Agent seems confused about instructions
- Commands fail or produce errors
- Files/database in inconsistent state
- Agent takes too long to think
- Mission file incomplete or malformed

---

## Test Execution Log

**Date:** ___________  
**Tester:** ___________  
**Persona Used:** ___________  
**Role Used:** ___________

### Test 1 Results:
- Startup time: _____ seconds
- Issues found: _________________
- Pass/Fail: _______

### Test 2 Results:
- Closure time: _____ seconds
- Issues found: _________________
- Pass/Fail: _______

### Test 3 Results:
- Handoff workflow: Pass/Fail
- Issues found: _________________

### Test 4 Results:
- Edge cases: Pass/Fail
- Issues found: _________________

### Overall Assessment:
- All tests passed: Yes/No
- Improvements needed: _________________
- Ready for production: Yes/No

---

## Follow-Up Actions

**If tests pass:**
- [ ] Mark OPR-H-0028 as verified
- [ ] Close related handoffs
- [ ] Document lessons learned

**If tests fail:**
- [ ] Document specific failures
- [ ] Create new tasks for fixes
- [ ] Re-test after fixes applied

---

**End of Test Plan**
