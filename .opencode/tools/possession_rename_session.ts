import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description: "Rename the current OpenCode session title to 'Operation <codename>: <Persona> - <Role>' based on the active mission bound to this session",
  args: {},
  async execute(args, context) {
    // The Python script computes the title and writes it directly to the OpenCode DB
    const script = path.join(context.worktree, ".opencode/tools/possession_rename_session.py")
    const input = JSON.stringify({ session_id: context.sessionID })
    const raw = await Bun.$`cd ${context.worktree} && echo ${input} | uv run python3 ${script}`.text()
    const result = JSON.parse(raw.trim())
    return JSON.stringify(result)
  },
})
