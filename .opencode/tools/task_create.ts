import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description: "Create a new task in the site-nine task database. Returns the generated task ID and task details.",
  args: {
    title: tool.schema
      .string()
      .describe("Brief task description (e.g., 'Add rate limiting to API endpoints')"),
    role: tool.schema
      .string()
      .describe("Agent role responsible for this task (e.g., Engineer, Operator, Architect, Tester, Designer, Documentarian)"),
    priority: tool.schema
      .string()
      .optional()
      .describe("Task priority: CRITICAL, HIGH, MEDIUM, or LOW"),
    category: tool.schema
      .string()
      .optional()
      .describe("Task category describing the type of work"),
    description: tool.schema
      .string()
      .optional()
      .describe("Detailed description of what needs to be done and why"),
    epic_id: tool.schema
      .string()
      .optional()
      .describe("Epic ID to link this task to (e.g., EPC-H-0001)"),
  },
  async execute(args, context) {
    const script = path.join(context.worktree, ".opencode/tools/task_create.py")
    const input = JSON.stringify({
      title: args.title,
      role: args.role,
      priority: args.priority ?? null,
      category: args.category ?? null,
      description: args.description ?? null,
      epic_id: args.epic_id ?? null,
    })
    const result = await Bun.$`cd ${context.worktree} && echo ${input} | uv run python3 ${script}`.text()
    return result.trim()
  },
})
