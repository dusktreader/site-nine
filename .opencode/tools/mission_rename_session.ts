import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description: "Rename the current OpenCode session title to 'Operation <codename>: <Persona> - <Role>' based on the active mission bound to this session",
  args: {},
  async execute(args, context) {
    const script = path.join(context.worktree, ".opencode/tools/mission_rename_session.py")
    const input = JSON.stringify({ session_id: context.sessionID })
    const result = await Bun.$`cd ${context.worktree} && echo ${input} | uv run python3 ${script}`.text()
    return result.trim()
  },
})
