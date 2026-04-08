import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description:
    "Signal a minion-mode worker mission to terminate gracefully. " +
    "Sends a high-priority termination message to the target mission, requesting it end its session and close the mission cleanly.",
  args: {
    from_possession_id: tool.schema.number().describe("The possession ID sending the termination signal (typically Admin/Director)"),
    to_possession_id: tool.schema.number().describe("The possession ID of the worker to terminate"),
    reason: tool.schema
      .string()
      .optional()
      .describe("Optional reason for termination (included in the message body)"),
  },
  async execute(args, context) {
    const script = path.join(context.worktree, ".opencode/tools/worker_terminate.py")
    const input = JSON.stringify({
      from_possession_id: args.from_possession_id,
      to_possession_id: args.to_possession_id,
      reason: args.reason ?? null,
    })
    const result = await Bun.$`cd ${context.worktree} && echo ${input} | uv run python3 ${script}`.text()
    return result.trim()
  },
})
