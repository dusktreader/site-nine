import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description: "Set or update the whimsical bio for a daemon. The bio should be 3-5 sentences, first-person, playful tone with mythological flavour.",
  args: {
    name: tool.schema
      .string()
      .describe("Daemon name to update (e.g., azazel)"),
    bio: tool.schema
      .string()
      .describe("Whimsical first-person bio text (3-5 sentences, playful tone, mythological details)"),
  },
  async execute(args, context) {
    const script = path.join(context.worktree, ".opencode/tools/daemon_set_bio.py")
    const input = JSON.stringify({ name: args.name, bio: args.bio })
    const result = await Bun.$`cd ${context.worktree} && echo ${input} | uv run python3 ${script}`.text()
    return result.trim()
  },
})
