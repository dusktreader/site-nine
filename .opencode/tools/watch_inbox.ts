import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description:
    "Block until a new message arrives in the possession inbox, or until timeout expires. " +
    "Returns immediately when a message is received. Use this instead of polling on a " +
    "fixed schedule — it wakes up as soon as a worker sends a status update.",
  args: {
    possession_id: tool.schema.number().describe("The possession ID to watch the inbox for"),
    timeout: tool.schema
      .number()
      .optional()
      .describe("Maximum seconds to wait before returning (default: 300)"),
    poll_interval: tool.schema
      .number()
      .optional()
      .describe("Seconds between inbox checks (default: 5)"),
  },
  async execute(args, context) {
    const script = path.join(context.worktree, ".opencode/tools/watch_inbox.py")
    const input = JSON.stringify({
      possession_id: args.possession_id,
      timeout: args.timeout ?? null,
      poll_interval: args.poll_interval ?? null,
    })
    const result = await Bun.$`cd ${context.worktree} && echo ${input} | uv run python3 ${script}`.text()
    return result.trim()
  },
})
