import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description:
    "Query site-nine tasks. Modes: " +
    "(1) show a single task by ID — supply task_id; " +
    "(2) list tasks with optional filters — supply role, status, and/or mission_id without task_id; " +
    "(3) show tasks owned by a mission — supply mission_id alone; " +
    "(4) generate a summary report — supply report=true.",
  args: {
    task_id: tool.schema
      .string()
      .optional()
      .describe("Task ID to fetch (e.g. ENG-H-0151). If provided, all other args are ignored."),
    role: tool.schema
      .string()
      .optional()
      .describe("Filter by agent role (e.g. Engineer, Operator, Architect, Tester, Designer, Documentarian)."),
    status: tool.schema
      .string()
      .optional()
      .describe("Filter by status: TODO, UNDERWAY, COMPLETE, or ABORTED."),
    mission_id: tool.schema
      .number()
      .optional()
      .describe("Filter by mission ID. When used alone (without task_id/role/status) returns tasks owned by that mission."),
    report: tool.schema
      .boolean()
      .optional()
      .describe("If true, generate a summary report instead of a task list."),
    active_only: tool.schema
      .boolean()
      .optional()
      .describe("When report=true, exclude COMPLETE and ABORTED tasks from the report."),
  },
  async execute(args, context) {
    const script = path.join(context.worktree, ".opencode/tools/task_show.py")
    const input = JSON.stringify({
      task_id: args.task_id ?? null,
      role: args.role ?? null,
      status: args.status ?? null,
      mission_id: args.mission_id ?? null,
      report: args.report ?? false,
      active_only: args.active_only ?? false,
    })
    const result = await Bun.$`cd ${context.worktree} && echo ${input} | uv run python3 ${script}`.text()
    return result.trim()
  },
})
