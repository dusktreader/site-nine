---
description: Start a new agent session with role selection and persona naming
---

Load and follow the session-start skill.

Role parameter: $1
Persona flag: $2
Auto-assign flag: $3
Task flag: $4

If the role parameter is not empty, use that role directly and skip Step 2 (role selection) of the session-start skill.

If the persona flag is provided as "--persona <name>" (e.g., "--persona atlas"), use that persona name directly in Step 3. If the persona does not exist in the database, the agent will collaborate with the Director to create it by gathering mythology type, description, and generating a bio.

If the persona flag is not provided, automatically select the first unused persona name in Step 3 without prompting the user (auto-name is now default behavior).

If the auto-assign flag is "--auto-assign", automatically claim and start work on the top priority task for the given role without prompting the Director. This requires a role to be specified.

If the task flag is provided as "--task TASK-ID" (e.g., "--task OPR-H-0065"), the agent will:
- Automatically select a persona name (default behavior)
- Claim the specified task ID
- Start work on it immediately
- This flag is mutually exclusive with --auto-assign (cannot use both)
- This flag requires a role to be specified

skill(name="session-start")
