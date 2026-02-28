import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description:
    "Claim a task for the current mission, transitioning it to UNDERWAY status. " +
    "Validates role match, checks for blockers and unmet dependencies before claiming.",
  args: {
    task_id: tool.schema
      .string()
      .describe("The task ID to claim (e.g. ENG-H-0152)"),
    mission_id: tool.schema
      .number()
      .describe("The mission ID claiming the task"),
    role: tool.schema
      .string()
      .describe("The role of the claiming mission (e.g. Engineer, Operator)"),
  },
  async execute(args, context) {
    const script = path.join(context.worktree, ".opencode/tools/task_claim.py")
    const input = JSON.stringify({
      task_id: args.task_id,
      mission_id: args.mission_id,
      role: args.role,
    })
    const result = await Bun.$`cd ${context.worktree} && echo ${input} | uv run python3 ${script}`.text()
    return result.trim()
  },
})
