import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description:
    "Return a list of active worker possessions for a given role. " +
    "Useful for Admin orchestration to discover which desk-mode workers are currently running.",
  args: {
    role: tool.schema
      .string()
      .optional()
      .describe("Filter by role (e.g., Engineer, Operator). If omitted, returns all active possessions."),
  },
  async execute(args, context) {
    const script = path.join(context.worktree, ".opencode/tools/worker_status.py")
    const input = JSON.stringify({ role: args.role ?? null })
    const result = await Bun.$`cd ${context.worktree} && echo ${input} | uv run python3 ${script}`.text()
    return result.trim()
  },
})
