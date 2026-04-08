import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description: "Rename the current OpenCode session title to append '[EXORCISED]' suffix when a possession ends",
  args: {},
  async execute(args, context) {
    // The Python script reads the current title, appends [EXORCISED], and writes to OpenCode DB
    const script = path.join(context.worktree, ".opencode/tools/possession_rename_exorcised.py")
    const input = JSON.stringify({ session_id: context.sessionID })
    const raw = await Bun.$`cd ${context.worktree} && echo ${input} | uv run python3 ${script}`.text()
    const result = JSON.parse(raw.trim())
    return JSON.stringify(result)
  },
})
