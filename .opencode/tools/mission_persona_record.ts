import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description: "Record the persona selection for a pending mission, transitioning from PERSONA_PENDING to ACTIVE. If persona is omitted, atomically claims the least-used persona for the mission's role.",
  args: {
    mission_id: tool.schema
      .number()
      .describe("The mission ID to update"),
    persona: tool.schema
      .string()
      .optional()
      .describe("The persona name to assign (must exist in the personas table). If omitted, automatically claims least-used persona for the mission's role."),
  },
  async execute(args, context) {
    const script = path.join(context.worktree, ".opencode/tools/mission_persona_record.py")
    const input = JSON.stringify({ mission_id: args.mission_id, persona: args.persona })
    const result = await Bun.$`cd ${context.worktree} && echo ${input} | uv run python3 ${script}`.text()
    return result.trim()
  },
})
