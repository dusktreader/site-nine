Load and follow the session-start skill.

Role parameter: $1
Auto-name flag: $2
Auto-assign flag: $3

If the role parameter is not empty, use that role directly and skip Step 2 (role selection) of the session-start skill.

If the auto-name flag is "--auto-name", automatically select the first unused persona name in Step 3 without prompting the user.

If the auto-assign flag is "--auto-assign", automatically claim and start work on the top priority task for the given role without prompting the Director. This requires a role to be specified.

skill(name="session-start")
