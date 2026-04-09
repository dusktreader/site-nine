-- Migration 004: Add worker_pid column to possessions table
--
-- Adds worker_pid to support Inquisitor crash detection for minion workers.
-- The column stores the OS PID of the minion_worker.py process so the Inquisitor
-- can check liveness with os.kill(pid, 0) instead of waiting for heartbeat staleness.
--
-- NULL for interactive possessions and after clean shutdown.
-- Set to os.getpid() by minion_worker.py after minion mode is enabled.
-- Cleared to NULL in handle_shutdown() before SystemExit.
--
-- ADR-016, Fix 4: Worker PID Registration and Crash Detection

ALTER TABLE possessions ADD COLUMN worker_pid INTEGER;
