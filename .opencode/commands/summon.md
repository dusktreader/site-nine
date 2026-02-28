---
description: Start a new agent session with role selection and persona naming
---

Load and follow the mission-start skill to initialize your mission.

Parameters provided to this command:
- Role: $1
- Persona flag: $2
- Auto-assign flag: $3
- Task flag: $4
- Desk flag: $5

Use these parameters as context when executing the skill steps:
- If a role was provided, skip role selection (Step 2) and use it directly.
- If `--persona <name>` was provided, use that persona name in Step 4.
- If `--auto-assign` was provided, execute Step 10 (auto-assign) after initialization.
- If `--task TASK-ID` was provided, claim that specific task in Step 10.
- If `--desk` was provided, operate in headless desk worker mode.

skill(name="mission-start")
