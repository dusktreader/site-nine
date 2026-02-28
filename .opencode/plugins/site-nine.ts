/**
 * site-nine.ts
 *
 * OpenCode plugin that manages the site-nine mission lifecycle automatically.
 *
 * Responsibilities (ADR-013, Phase 4):
 *
 * 1. Activity tracking: On session.updated events, update the mission's
 *    last_activity_at timestamp. Throttled to a maximum of one DB write per
 *    minute per session to prevent excessive load.
 *
 * 2. Auto-suspend on session close: On session.deleted events, look up whether
 *    an active mission is bound to the session and, if so, transition it to
 *    SUSPENDED status. If the DB operation fails, retried with exponential
 *    backoff before giving up.
 *
 * 3. Comprehensive logging: All plugin operations are logged at appropriate
 *    levels so issues can be diagnosed from OpenCode logs.
 *
 * All DB operations are delegated to Python scripts:
 *   - plugin_activity_update.py  (session.updated handler)
 *   - plugin_session_suspend.py  (session.deleted handler)
 *
 * This plugin supersedes mission-lifecycle.ts, which used the s9 CLI.
 * Agents must never use s9 CLI commands — all business logic goes through
 * Python scripts that import from site_nine directly (ADR-013).
 */

import type { Plugin } from "@opencode-ai/plugin"
import path from "path"

/** Maximum of one activity DB write per minute per session. */
const ACTIVITY_THROTTLE_MS = 60_000

/**
 * Exponential backoff configuration for session.deleted retry.
 * Delays (ms): 500, 1000, 2000, 4000 → total ~7.5s of retries.
 */
const SUSPEND_RETRY_DELAYS_MS = [500, 1_000, 2_000, 4_000]

/** Per-session timestamps of last activity write (for throttling). */
const lastActivityWriteAt = new Map<string, number>()

/** Sleep helper. */
const sleep = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms))

export const SiteNinePlugin: Plugin = async ({ $, worktree }) => {
  const activityScript = path.join(worktree, ".opencode/tools/plugin_activity_update.py")
  const suspendScript = path.join(worktree, ".opencode/tools/plugin_session_suspend.py")
  const python = path.join(worktree, ".venv/bin/python3")

  /**
   * Call a Python script with a JSON payload via stdin.
   * Returns the parsed JSON output, or null on error.
   */
  const callPython = async (script: string, payload: Record<string, string>): Promise<Record<string, unknown> | null> => {
    try {
      const input = JSON.stringify(payload)
      const result = await $`echo ${input} | ${python} ${script}`.text()
      const output = result.trim()
      if (!output) {
        console.warn(`[site-nine] Empty output from ${path.basename(script)}`)
        return null
      }
      return JSON.parse(output) as Record<string, unknown>
    } catch (err) {
      console.error(`[site-nine] Error calling ${path.basename(script)}: ${err}`)
      return null
    }
  }

  /**
   * Handle session.updated: update last_activity_at for the bound mission.
   * Throttled to one write per minute per session.
   */
  const handleSessionUpdated = async (sessionID: string): Promise<void> => {
    const now = Date.now()
    const lastWrite = lastActivityWriteAt.get(sessionID) ?? 0
    const elapsed = now - lastWrite

    if (elapsed < ACTIVITY_THROTTLE_MS) {
      return
    }

    const result = await callPython(activityScript, { session_id: sessionID })
    if (!result) return

    lastActivityWriteAt.set(sessionID, now)

    const status = result.status as string
    if (status === "updated") {
      // Activity timestamp updated — no output needed.
    } else if (status === "no_mission") {
      // No active mission — expected when session has no claimed task. Silent.
    } else if (status === "error") {
      console.warn(`[site-nine] activity update error for session ${sessionID}: ${result.message}`)
    }
  }

  /**
   * Handle session.deleted: suspend the active mission bound to this session.
   * Retries with exponential backoff on failure.
   */
  const handleSessionDeleted = async (sessionID: string): Promise<void> => {
    console.info(`[site-nine] session.deleted — attempting auto-suspend for session ${sessionID}`)

    const payload = {
      session_id: sessionID,
      reason: "OpenCode session closed",
    }

    // Clean up throttle tracking for this session
    lastActivityWriteAt.delete(sessionID)

    for (let attempt = 0; attempt <= SUSPEND_RETRY_DELAYS_MS.length; attempt++) {
      const result = await callPython(suspendScript, payload)

      if (result) {
        const status = result.status as string

        if (status === "suspended") {
          console.info(
            `[site-nine] auto-suspended mission ${result.mission_id} (${result.codename}) for session ${sessionID}`
          )
          return
        } else if (status === "no_mission") {
          console.debug(`[site-nine] no active mission for session ${sessionID}, no suspension needed`)
          return
        } else if (status === "skipped") {
          console.debug(
            `[site-nine] suspension skipped for mission ${result.mission_id}: ${result.reason}`
          )
          return
        } else if (status === "error") {
          const isLastAttempt = attempt >= SUSPEND_RETRY_DELAYS_MS.length
          if (isLastAttempt) {
            console.error(
              `[site-nine] auto-suspend failed after ${attempt + 1} attempt(s) for session ${sessionID}: ${result.message}`
            )
            return
          }

          const delayMs = SUSPEND_RETRY_DELAYS_MS[attempt]
          console.warn(
            `[site-nine] auto-suspend attempt ${attempt + 1} failed for session ${sessionID}: ${result.message} — retrying in ${delayMs}ms`
          )
          await sleep(delayMs)
        }
      } else {
        // callPython returned null (script call itself failed)
        const isLastAttempt = attempt >= SUSPEND_RETRY_DELAYS_MS.length
        if (isLastAttempt) {
          console.error(
            `[site-nine] auto-suspend gave up after ${attempt + 1} attempt(s) for session ${sessionID} (script call failed)`
          )
          return
        }

        const delayMs = SUSPEND_RETRY_DELAYS_MS[attempt]
        console.warn(
          `[site-nine] auto-suspend attempt ${attempt + 1} failed (script call) for session ${sessionID} — retrying in ${delayMs}ms`
        )
        await sleep(delayMs)
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
      } catch (err) {
        // Top-level guard: never let plugin errors crash OpenCode
        console.error(`[site-nine] Unhandled error in event handler (${event.type}): ${err}`)
      }
    },
  }
}
