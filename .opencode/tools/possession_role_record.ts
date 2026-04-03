import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description: "Record the role selection for a pending possession, transitioning from ROLE_PENDING to DAEMON_PENDING",
  args: {
    possession_id: tool.schema
      .number()
      .describe("The possession ID to update"),
    role: tool.schema
      .string()
      .describe("The role to assign (Administrator, Architect, Engineer, Tester, Documentarian, Designer, Inspector, Operator, Historian)"),
  },
  async execute(args, context) {
    const script = path.join(context.worktree, ".opencode/tools/possession_role_record.py")
    const input = JSON.stringify({ possession_id: args.possession_id, role: args.role })
    const result = await Bun.$`cd ${context.worktree} && echo ${input} | uv run python3 ${script}`.text()
    return result.trim()
  },
})
