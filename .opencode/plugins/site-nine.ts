/**
 * site-nine.ts
 *
 * OpenCode plugin that manages the site-nine possession lifecycle automatically.
 *
 * Responsibilities (ADR-013, Phase 4):
 *
 * 1. Activity tracking: On session.updated events, update the possession's
 *    last_heartbeat_at timestamp. Throttled to a maximum of one DB write per
 *    minute per session to prevent excessive load.
 *
 * 2. Status toasts: On every session.updated event, pop any pending messages
 *    from the status_queue table and surface them as TUI toast notifications.
 *    Desk-mode sessions are skipped — only the interactive director session
 *    pops the queue. Workers push to the queue via the push_status tool.
 *
 * 3. Auto-exorcise on session close: On session.deleted events, look up whether
 *    an active possession is bound to the session and, if so, exorcise it
 *    (set status → EXORCISED, record end_time) and release any UNDERWAY tasks
 *    back to TODO. If the DB operation fails, retried with exponential backoff
 *    before giving up.
 *
 * All DB operations are delegated to Python scripts:
 *   - plugin_activity_update.py     (activity timestamp update)
 *   - plugin_pop_status.py          (status queue pop + desk-mode check)
 *   - plugin_session_exorcise.py    (session.deleted handler — exorcise + task release)
 *
 * IMPORTANT: This plugin must NEVER write to stderr (no console.warn, .error,
 * .info, .log) — any stderr output corrupts the OpenCode TUI rendering.
 * All error handling and logging is done in the Python scripts, which write
 * to the typerdrive log file (~/.local/state/site-nine/logs/app.log).
 */

import type { Plugin } from "@opencode-ai/plugin"
import path from "path"

/** Maximum of one activity DB write per minute per session. */
const ACTIVITY_THROTTLE_MS = 60_000

/**
 * Exponential backoff configuration for session.deleted retry.
 * Delays (ms): 500, 1000, 2000, 4000 → total ~7.5s of retries.
 */
const EXORCISE_RETRY_DELAYS_MS = [500, 1_000, 2_000, 4_000]

/** Per-session timestamps of last activity write (for throttling). */
const lastActivityWriteAt = new Map<string, number>()

/** Sleep helper. */
const sleep = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms))

export const SiteNinePlugin: Plugin = async ({ $, worktree, client }) => {
  const activityScript = path.join(worktree, ".opencode/tools/plugin_activity_update.py")
  const popStatusScript = path.join(worktree, ".opencode/tools/plugin_pop_status.py")
  const exorciseScript = path.join(worktree, ".opencode/tools/plugin_session_exorcise.py")
  const python = path.join(worktree, ".venv/bin/python3")

  /**
   * Call a Python script with a JSON payload via stdin.
   * Returns the parsed JSON output, or null on error.
   * Never writes to stderr — errors are silently swallowed here since
   * the Python scripts log to the app log file.
   */
  const callPython = async (script: string, payload: Record<string, string>): Promise<Record<string, unknown> | null> => {
    try {
      const input = JSON.stringify(payload)
      const result = await $`echo ${input} | ${python} ${script}`.text()
      const output = result.trim()
      if (!output) return null
      return JSON.parse(output) as Record<string, unknown>
    } catch {
      return null
    }
  }

  /**
   * Pop pending status messages and show each as a toast.
   * Returns silently if the session is desk-mode or the queue is empty.
   */
  const popStatusAndToast = async (sessionID: string): Promise<void> => {
    const result = await callPython(popStatusScript, { session_id: sessionID })
    if (!result) return

    const status = result.status as string
    if (status !== "messages") return

    const messages = result.messages as Array<{
      id: number
      daemon_name: string | null
      message: string
    }>

    for (const msg of messages) {
      const sender = msg.daemon_name ?? "worker"
      const preview = msg.message.length > 120 ? msg.message.slice(0, 117) + "…" : msg.message
      try {
        await client.tui.showToast({ body: { message: `[${sender}] ${preview}`, variant: "success" } })
      } catch {
        // Toast delivery failed — nothing we can do without stderr
      }
    }
  }

  /**
   * Handle session.updated: pop status queue and toast, then update activity
   * timestamp (throttled to once per minute).
   */
  const handleSessionUpdated = async (sessionID: string): Promise<void> => {
    // Always pop and toast — workers can push at any moment.
    await popStatusAndToast(sessionID)

    // Activity heartbeat is throttled to once per minute.
    const now = Date.now()
    const lastWrite = lastActivityWriteAt.get(sessionID) ?? 0
    if (now - lastWrite < ACTIVITY_THROTTLE_MS) {
      return
    }
    lastActivityWriteAt.set(sessionID, now)

    await callPython(activityScript, { session_id: sessionID })
  }

  /**
   * Handle session.deleted: exorcise the active possession bound to this session
   * and release any UNDERWAY tasks back to TODO.
   * Retries with exponential backoff on failure.
   */
  const handleSessionDeleted = async (sessionID: string): Promise<void> => {
    lastActivityWriteAt.delete(sessionID)

    const payload = {
      session_id: sessionID,
    }

    for (let attempt = 0; attempt <= EXORCISE_RETRY_DELAYS_MS.length; attempt++) {
      const result = await callPython(exorciseScript, payload)

      if (result) {
        const status = result.status as string

        if (status === "exorcised" || status === "no_possession" || status === "skipped") {
          return
        } else if (status === "error") {
          const isLastAttempt = attempt >= EXORCISE_RETRY_DELAYS_MS.length
          if (isLastAttempt) return
          await sleep(EXORCISE_RETRY_DELAYS_MS[attempt])
        }
      } else {
        const isLastAttempt = attempt >= EXORCISE_RETRY_DELAYS_MS.length
        if (isLastAttempt) return
        await sleep(EXORCISE_RETRY_DELAYS_MS[attempt])
      }
    }
  }

  return {
    event: async ({ event }) => {
      try {
        if (event.type === "session.updated") {
          const sessionID = event.properties.info.id
          await handleSessionUpdated(sessionID)
        } else if (event.type === "session.deleted") {
          const sessionID = event.properties.info.id
          await handleSessionDeleted(sessionID)
        }
      } catch {
        // Silently swallow — Python scripts handle their own logging
      }
    },
  }
}
