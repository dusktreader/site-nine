import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description:
    "Suggest unused or least-used persona names for a given agent role. " +
    "Returns personas ordered by least-used first, so the first result is the best pick for auto-selection.",
  args: {
    role: tool.schema
      .string()
      .describe("Agent role to suggest personas for (e.g. Engineer, Operator, Architect, Tester, Designer, Documentarian)."),
    count: tool.schema
      .number()
      .optional()
      .describe("Number of suggestions to return (default: 3)."),
  },
  async execute(args, context) {
    const script = path.join(context.worktree, ".opencode/tools/persona_suggest.py")
    const input = JSON.stringify({
      role: args.role,
      count: args.count ?? 3,
    })
    const result = await Bun.$`cd ${context.worktree} && echo ${input} | uv run python3 ${script}`.text()
    return result.trim()
  },
})
