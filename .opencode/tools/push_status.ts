import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description:
    "Push a short status message to the director's toast queue. " +
    "Use this to let the director know what you're doing — task started, " +
    "task complete, going to sleep, blocked, etc. Messages appear as toast " +
    "notifications in the TUI. Keep messages under 120 characters.",
  args: {
    mission_id: tool.schema.number().describe("Your mission ID"),
    message: tool.schema.string().describe("Short status message (under 120 chars)"),
  },
  async execute(args, context) {
    const script = path.join(context.worktree, ".opencode/tools/push_status.py")
    const input = JSON.stringify({
      mission_id: args.mission_id,
      message: args.message,
    })
    const result = await Bun.$`cd ${context.worktree} && echo ${input} | uv run python3 ${script}`.text()
    return result.trim()
  },
})
