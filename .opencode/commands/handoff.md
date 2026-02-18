---
description: Hand off work to another agent with full context
---

Load and follow the handoff-workflow skill.

Target role parameter: $1

If the target role parameter is provided (e.g., `/handoff Engineer`), pass it to the skill as
the target role for Step 2.

If the target role parameter is not provided (e.g., `/handoff` with no argument), the skill
should default the target role to the agent's current role (i.e., hand off to the same role).

skill(name="handoff-workflow")
