import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description:
    "Claim a task for the current possession, transitioning it to UNDERWAY status. " +
    "Validates role match, checks for blockers and unmet dependencies before claiming.",
  args: {
    task_id: tool.schema
      .string()
      .describe("The task ID to claim (e.g. ENG-H-0152)"),
    possession_id: tool.schema
      .number()
      .describe("The possession ID claiming the task"),
    role: tool.schema
      .string()
      .describe("The role of the claiming possession (e.g. Engineer, Operator)"),
  },
  async execute(args, context) {
    const script = path.join(context.worktree, ".opencode/tools/task_claim.py")
    const input = JSON.stringify({
      task_id: args.task_id,
      possession_id: args.possession_id,
      role: args.role,
    })
    const result = await Bun.$`cd ${context.worktree} && echo ${input} | uv run python3 ${script}`.text()
    return result.trim()
  },
})
