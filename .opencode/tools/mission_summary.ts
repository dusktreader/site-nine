import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description: "Generate a summary of files changed, commits, and tasks for the current mission",
  args: {
    mission_id: tool.schema
      .number()
      .optional()
      .describe("Optional mission ID override. If omitted, the mission bound to the current session is used."),
  },
  async execute(args, context) {
    const script = path.join(context.worktree, ".opencode/tools/mission_summary.py")
    const input = JSON.stringify({
      session_id: context.sessionID,
      mission_id: args.mission_id ?? null,
    })
    const result = await Bun.$`cd ${context.worktree} && echo ${input} | uv run python3 ${script}`.text()
    return result.trim()
  },
})
