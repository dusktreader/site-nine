import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description:
    "End the current site-nine possession bound to this session, transitioning it to ENDED status. " +
    "Uses the session's bound possession automatically; supply possession_id only to override.",
  args: {
    possession_id: tool.schema
      .number()
      .optional()
      .describe("Optional possession ID override. If omitted, the possession bound to the current session is used."),
  },
  async execute(args, context) {
    const script = path.join(context.worktree, ".opencode/tools/possession_end.py")
    const input = JSON.stringify({
      session_id: context.sessionID,
      possession_id: args.possession_id ?? null,
    })
    const result = await Bun.$`cd ${context.worktree} && echo ${input} | uv run python3 ${script}`.text()
    return result.trim()
  },
})
