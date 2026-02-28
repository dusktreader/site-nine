import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description: "Initialize a new site-nine mission for the current session",
  args: {},
  async execute(args, context) {
    const script = path.join(context.worktree, ".opencode/tools/mission_init.py")
    const input = JSON.stringify({ session_id: context.sessionID })
    const result = await Bun.$`cd ${context.worktree} && echo ${input} | uv run python3 ${script}`.text()
    return result.trim()
  },
})
