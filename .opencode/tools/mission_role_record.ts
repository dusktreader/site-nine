import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description: "Record the role selection for a pending mission, transitioning from ROLE_PENDING to PERSONA_PENDING",
  args: {
    mission_id: tool.schema
      .number()
      .describe("The mission ID to update"),
    role: tool.schema
      .string()
      .describe("The role to assign (Administrator, Architect, Engineer, Tester, Documentarian, Designer, Inspector, Operator, Historian)"),
  },
  async execute(args, context) {
    const script = path.join(context.worktree, ".opencode/tools/mission_role_record.py")
    const input = JSON.stringify({ mission_id: args.mission_id, role: args.role })
    const result = await Bun.$`cd ${context.worktree} && echo ${input} | uv run python3 ${script}`.text()
    return result.trim()
  },
})
