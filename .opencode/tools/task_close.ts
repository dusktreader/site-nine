import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description:
    "Close a task by setting its status to COMPLETE or ABORTED. " +
    "Optionally provide final notes to record on the task.",
  args: {
    task_id: tool.schema
      .string()
      .describe("Task ID to close (e.g. ENG-H-0154)"),
    status: tool.schema
      .string()
      .describe("Final status: COMPLETE or ABORTED"),
    notes: tool.schema
      .string()
      .optional()
      .describe("Optional final notes to record on the task"),
  },
  async execute(args, context) {
    const script = path.join(context.worktree, ".opencode/tools/task_close.py")
    const input = JSON.stringify({
      task_id: args.task_id,
      status: args.status,
      notes: args.notes ?? null,
    })
    const result = await Bun.$`cd ${context.worktree} && echo ${input} | uv run python3 ${script}`.text()
    return result.trim()
  },
})
