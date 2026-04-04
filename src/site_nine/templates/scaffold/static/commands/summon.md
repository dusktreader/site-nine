---
description: Start a new agent session with role selection and daemon naming
---

Load and follow the possession-start skill to initialize your possession.

Parameters provided to this command:
- Role: $1
- Daemon flag: $2
- Auto-assign flag: $3
- Task flag: $4
- Desk flag: $5

Use these parameters as context when executing the skill steps:
- If a role was provided, skip role selection (Step 2) and use it directly.
- If `--daemon <name>` was provided, use that daemon name in Step 3.
- If `--auto-assign` was provided, claim the top priority task after initialization.
- If `--task TASK-ID` was provided, claim that specific task after initialization.
- If `--desk` was provided, operate in headless desk worker mode.

skill(name="possession-start")
