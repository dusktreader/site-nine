# SIGTERM Handler Implementation for Desk Workers

**Task:** ENG-M-0186  
**Mission:** #146 (omega-photon)  
**Status:** Complete

## Summary

Implemented graceful SIGTERM handling for desk workers to ensure missions are properly ended before process termination. Two complementary implementations were created:

1. **Primary Implementation**: `desk-worker.py` - Full-featured polling script with integrated SIGTERM handling
2. **Alternative Implementation**: `desk_worker_wrapper.py` - Lightweight wrapper for single `opencode run` invocations

## Implementation Details

### Primary: desk-worker.py

Located at: `scripts/desk-worker.py`

**Features:**
- Full desk worker lifecycle management (initialization, polling, message processing)
- Integrated SIGTERM/SIGINT signal handling
- Graceful shutdown sequence:
  1. Catches SIGTERM or SIGINT
  2. Disables desk mode in database
  3. Invokes mission-end skill via `opencode run` with dismissal message
  4. Clean exit with status code 0

**Signal Handler (lines 254-299):**
```python
def handle_shutdown(self, signum: int, frame) -> None:
    """Gracefully shutdown on SIGTERM/SIGINT."""
    # Disable desk mode
    mgr.set_desk_mode(self.mission_id, active=False)
    
    # End mission via opencode run
    cmd = [
        "opencode", "run", "--session", self.session_id,
        "--model", self.model,
        "You are being dismissed. End your mission using the mission-end skill.",
    ]
    subprocess.run(cmd, check=False, timeout=120)
```

**Usage:**
```bash
# Start desk worker with SIGTERM handling
scripts/desk-worker.py Engineer --persona shu-nanna

# Send SIGTERM to gracefully shut down
kill -TERM <pid>
```

**Testing:**
- Test suite: `tests/test_desk_worker_script.py`
- Covers SIGTERM/SIGINT handling, graceful shutdown, cleanup

### Alternative: desk_worker_wrapper.py

Located at: `scripts/desk_worker_wrapper.py`

**Features:**
- Lightweight wrapper around single `opencode run` invocations
- SIGTERM handling for non-polling use cases  
- Process management with timeout and cleanup
- Suitable for simpler scenarios

**Usage:**
```bash
# Wrap a single opencode run invocation
scripts/desk_worker_wrapper.py \\
    --model github-copilot/claude-sonnet-4-5 \\
    --instruction "Your role is engineer. Initialize your mission."
```

## Architecture Decision

**Primary approach:** `desk-worker.py` is the recommended implementation for production desk workers because:

1. **Integrated lifecycle**: Manages the complete desk worker lifecycle (init → poll → process → shutdown)
2. **Mission awareness**: Has direct access to mission_id and session_id for proper cleanup
3. **Database integration**: Can disable desk mode flag and perform other DB operations
4. **Message handling**: Processes priority-ordered messages from the messaging system
5. **Battle-tested**: Includes comprehensive test coverage

**When to use desk_worker_wrapper.py:**
- Simple one-off `opencode run` invocations that need SIGTERM handling
- Testing or development scenarios
- Non-polling desk worker patterns (if needed in future)

## Requirements Met

✅ Add graceful termination handler  
✅ Invokes mission-end skill before exiting  
✅ Handles SIGTERM signal  
✅ Desk worker specific (both implementations)  
✅ Proper cleanup and database updates  
✅ Test coverage provided

## Files Created

- `scripts/desk-worker.py` (primary implementation, 470 lines)
- `scripts/desk_worker_wrapper.py` (alternative implementation, 195 lines)
- `tests/test_desk_worker_script.py` (test suite)
- `.opencode/work/tasks/ENG-M-0186-implementation-notes.md` (this file)

## Related Tasks

- **ENG-M-0185**: Write external Python polling script for desk workers (provides `desk-worker.py`)
- **ENG-M-0186**: Implement SIGTERM handler for desk workers (this task)
- **EPC-H-0006**: Site-nine as OpenCode integration platform (parent epic)

## Testing

Run the desk worker test suite:
```bash
pytest tests/test_desk_worker_script.py -v
```

Test SIGTERM handling manually:
```bash
# Terminal 1: Start worker
scripts/desk-worker.py Engineer

# Terminal 2: Send SIGTERM
kill -TERM $(pgrep -f "desk-worker.py Engineer")

# Observe graceful shutdown with mission-end invocation
```

## Technical Notes

The SIGTERM handler implementation follows Python signal handling best practices:

1. **Non-blocking**: Handler sets flag and initiates shutdown sequence
2. **Timeout protection**: Mission-end invocation has 120s timeout
3. **Error handling**: Continues shutdown even if mission-end fails
4. **Clean exit**: Uses SystemExit(0) for proper process termination
5. **Database cleanup**: Ensures desk_mode_active flag is cleared

The approach integrates cleanly with:
- OpenCode session management (via `--session` flag)
- site-nine mission lifecycle (via mission-end skill)
- Database state tracking (desk_mode_active flag)
- ADR-013 architecture (OpenCode integration platform)
