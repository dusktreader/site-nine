import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description:
    "Release a task back to TODO status, clearing its mission ownership and claimed_at timestamp. " +
    "Use when pausing work on a task so it becomes available for another mission to claim.",
  args: {
    task_id: tool.schema
      .string()
      .describe("Task ID to release (e.g. ENG-H-0155)"),
  },
  async execute(args, context) {
    const script = path.join(context.worktree, ".opencode/tools/task_release.py")
    const input = JSON.stringify({ task_id: args.task_id })
    const result = await Bun.$`cd ${context.worktree} && echo ${input} | uv run python3 ${script}`.text()
    return result.trim()
  },
})
