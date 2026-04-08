import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description:
    "Spawn a minion-mode worker for a given role. The minion runs in the background, " +
    "polls for messages, and stays alive for continuous work. Returns the summoned possession ID " +
    "for subsequent coordination via worker_message. This is the ONLY way for agents to " +
    "summon minions - never use 's9 summon' CLI directly.",
  args: {
    role: tool.schema
      .string()
      .describe(
        "Minion role to summon: Administrator, Architect, Engineer, Tester, Documentarian, Designer, Inspector, Operator, or Historian"
      ),
    daemon: tool.schema.string().optional().describe("Optional specific daemon name. If omitted, auto-selected."),
    model: tool.schema.string().optional().describe("Optional OpenCode model to use (default: claude-sonnet-4.6)"),
    poll_interval: tool.schema
      .number()
      .optional()
      .describe("Optional polling interval in seconds (default: 30)"),
  },
  async execute(args, context) {
    const script = path.join(context.worktree, ".opencode/tools/summon_minion.py")
    const input = JSON.stringify({
      role: args.role,
      daemon: args.daemon ?? null,
      model: args.model ?? null,
      poll_interval: args.poll_interval ?? null,
    })
    const result = await Bun.$`cd ${context.worktree} && echo ${input} | uv run python3 ${script}`.text()
    return result.trim()
  },
})
