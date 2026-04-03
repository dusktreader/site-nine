import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description: "Generate a summary of files changed, commits, and tasks for the current possession",
  args: {
    possession_id: tool.schema
      .number()
      .optional()
      .describe("Optional possession ID override. If omitted, the possession bound to the current session is used."),
  },
  async execute(args, context) {
    const script = path.join(context.worktree, ".opencode/tools/possession_summary.py")
    const input = JSON.stringify({
      session_id: context.sessionID,
      possession_id: args.possession_id ?? null,
    })
    const result = await Bun.$`cd ${context.worktree} && echo ${input} | uv run python3 ${script}`.text()
    return result.trim()
  },
})
