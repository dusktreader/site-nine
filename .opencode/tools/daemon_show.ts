import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description: "Show daemon details including mythology, description, and whimsical bio. Returns null bio field if no bio has been generated yet.",
  args: {
    name: tool.schema
      .string()
      .describe("Daemon name to look up (e.g., azazel)"),
  },
  async execute(args, context) {
    const script = path.join(context.worktree, ".opencode/tools/daemon_show.py")
    const input = JSON.stringify({ name: args.name })
    const result = await Bun.$`cd ${context.worktree} && echo ${input} | uv run python3 ${script}`.text()
    return result.trim()
  },
})
