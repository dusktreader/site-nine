import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description:
    "Update fields on an existing task (title, description, priority, category, notes). " +
    "Also supports updating work status (TODO, UNDERWAY, COMPLETE, ABORTED) via the status arg.",
  args: {
    task_id: tool.schema
      .string()
      .describe("Task ID to update (e.g. ENG-H-0153)"),
    title: tool.schema
      .string()
      .optional()
      .describe("New task title"),
    description: tool.schema
      .string()
      .optional()
      .describe("New detailed task description"),
    priority: tool.schema
      .string()
      .optional()
      .describe("New priority: CRITICAL, HIGH, MEDIUM, or LOW"),
    category: tool.schema
      .string()
      .optional()
      .describe("New task category"),
    notes: tool.schema
      .string()
      .optional()
      .describe("Notes to append or set on the task"),
    status: tool.schema
      .string()
      .optional()
      .describe("New work status: TODO, UNDERWAY, COMPLETE, or ABORTED"),
  },
  async execute(args, context) {
    const script = path.join(context.worktree, ".opencode/tools/task_update.py")
    const input = JSON.stringify({
      task_id: args.task_id,
      title: args.title ?? null,
      description: args.description ?? null,
      priority: args.priority ?? null,
      category: args.category ?? null,
      notes: args.notes ?? null,
      status: args.status ?? null,
    })
    const result = await Bun.$`cd ${context.worktree} && echo ${input} | uv run python3 ${script}`.text()
    return result.trim()
  },
})
