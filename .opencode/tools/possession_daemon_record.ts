import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description: "Record the daemon selection for a DAEMON_PENDING possession, transitioning it to ACTIVE. If daemon is omitted, atomically claims the least-used daemon for the possession's role using a 3-day LRU threshold. When all daemons for the role have been used within the last 3 days, returns {action: 'invent_required', role, possession_id, prompt, instructions} — OpenCode must then generate a new daemon name + personality + daemonology, call add_daemon to insert it, and call this tool again with the invented name.",
  args: {
    possession_id: tool.schema
      .number()
      .describe("The possession ID to update"),
    daemon: tool.schema
      .string()
      .optional()
      .describe("The daemon name to assign (must exist in the daemons table). If omitted, automatically claims least-used daemon for the possession's role."),
  },
  async execute(args, context) {
    const script = path.join(context.worktree, ".opencode/tools/possession_daemon_record.py")
    const input = JSON.stringify({ possession_id: args.possession_id, daemon: args.daemon })
    const result = await Bun.$`cd ${context.worktree} && echo ${input} | uv run python3 ${script}`.text()
    return result.trim()
  },
})
