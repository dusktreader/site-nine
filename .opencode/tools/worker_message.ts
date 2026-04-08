import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description:
    "Send a message to another active possession (e.g., a minion-mode worker). " +
    "Uses the site-nine messaging system to deliver the message via conversation.",
  args: {
    from_possession_id: tool.schema.number().describe("The possession ID of the sender"),
    to_possession_id: tool.schema.number().describe("The possession ID of the recipient"),
    body: tool.schema.string().describe("Message body (markdown supported)"),
    priority: tool.schema
      .string()
      .optional()
      .describe("Message priority: CRITICAL, HIGH, MEDIUM, or LOW (default: MEDIUM)"),
    task_id: tool.schema
      .string()
      .optional()
      .describe("Optional related task ID to attach to the message"),
  },
  async execute(args, context) {
    const script = path.join(context.worktree, ".opencode/tools/worker_message.py")
    const input = JSON.stringify({
      from_possession_id: args.from_possession_id,
      to_possession_id: args.to_possession_id,
      body: args.body,
      priority: args.priority ?? null,
      task_id: args.task_id ?? null,
    })
    const result = await Bun.$`cd ${context.worktree} && echo ${input} | uv run python3 ${script}`.text()
    return result.trim()
  },
})
