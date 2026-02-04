Load and follow the session-start skill.

Role parameter: $1
Auto-name flag: $2

If the role parameter is not empty, use that role directly and skip Step 2 (role selection) of the session-start skill.

If the auto-name flag is "--auto-name", automatically select the first unused persona name in Step 3 without prompting the user.

skill(name="session-start")
