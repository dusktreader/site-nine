import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description: "Show the role-filtered task dashboard for the current agent. Returns available TODO and UNDERWAY tasks for the given role.",
  args: {
    role: tool.schema
      .string()
      .describe("Agent role to filter tasks by (e.g., Engineer, Operator, Architect)"),
  },
  async execute(args, context) {
    const script = path.join(context.worktree, ".opencode/tools/mission_dashboard.py")
    const input = JSON.stringify({ role: args.role })
    const result = await Bun.$`cd ${context.worktree} && echo ${input} | uv run python3 ${script}`.text()
    return result.trim()
  },
})
