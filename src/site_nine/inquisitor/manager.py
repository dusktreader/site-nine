"""Inquisitor manager — orchestrates infrastructure and data integrity checks."""

from __future__ import annotations

from pathlib import Path

from site_nine.core.database import Database
from site_nine.inquisitor.checks import (
    check_abandoned_tasks,
    check_backups,
    check_claimed_timestamps,
    check_closed_timestamps,
    check_crashed_minion_workers,
    check_daemon_incarnations,
    check_daemon_last_possession,
    check_database_exists,
    check_database_integrity,
    check_gitignore,
    check_orphaned_underway,
    check_possession_data,
    check_possession_daemons,
    check_possession_logs,
    check_rogue_possessions,
    check_task_dependencies,
    check_task_files,
    check_task_possession_refs,
    check_temp_files,
)
from site_nine.inquisitor.models import DataCheckResult, DiagnosticReport


# Pass messages for each data check, keyed by label.
# These are displayed when a check finds zero issues.
_PASS_MESSAGES: dict[str, str] = {
    "6a. Possession Daemons": "All possession daemon references are valid",
    "6b. Task Possession Refs": "All task possession references are valid",
    "6c. Task Dependencies": "All task dependencies are valid",
    "7a. Closed Timestamps": "All completed/aborted tasks have closed_at",
    "7b. Claimed Timestamps": "All UNDERWAY tasks have claimed_at",
    "8a. Possession Data": "All possessions have valid data structure",
    "8b. Possession Logs": "All active possession log files exist",
    "9a. Daemon Incarnations": "All daemon incarnation counts are correct",
    "9b. Last Possession Dates": "All last_possession timestamps are correct",
    "10a. Abandoned Tasks": "No tasks abandoned by exorcised possessions",
    "10b. Orphaned Tasks": "No orphaned UNDERWAY tasks",
    "10c. Rogue Possessions": "No rogue ACTIVE/IDLE possessions with stale heartbeats",
    "10d. Crashed Minion Workers": "No crashed minion worker possessions detected",
    "11. Task Files": "All task files exist",
}

# Fail summary messages for checks that include them in the original output.
_FAIL_SUMMARIES: dict[str, str] = {
    "6a. Possession Daemons": "Found {n} possessions with invalid daemon references",
    "6b. Task Possession Refs": "Found {n} orphaned task references",
    "6c. Task Dependencies": "Found {n} invalid dependencies",
    "7a. Closed Timestamps": "Found {n} tasks missing closed_at",
    "7b. Claimed Timestamps": "Found {n} incomplete UNDERWAY tasks",
    "8a. Possession Data": "Found {n} possessions with invalid data",
    "8b. Possession Logs": "Found {n} missing possession log files",
    "9a. Daemon Incarnations": "Found {n} incorrect daemon incarnation counts",
    "9b. Last Possession Dates": "Found {n} incorrect last_possession timestamps",
    "10a. Abandoned Tasks": "Found {n} tasks abandoned by exorcised possessions",
    "10b. Orphaned Tasks": "Found {n} orphaned UNDERWAY tasks",
    "10c. Rogue Possessions": "Found {n} rogue possessions (ACTIVE/IDLE with no recent heartbeat)",
    "10d. Crashed Minion Workers": "Found {n} crashed minion worker possessions",
    "11. Task Files": "Found {n} missing task files",
}

# Extra hint lines appended after the fail summary for some checks.
_FAIL_HINTS: dict[str, list[str]] = {
    "10a. Abandoned Tasks": ["These tasks should be manually reviewed and marked COMPLETE or TODO."],
    "10b. Orphaned Tasks": ["These tasks should be manually reviewed and released or completed."],
    "10c. Rogue Possessions": [
        "Run with --fix to auto-exorcise rogue possessions and release their tasks back to TODO."
    ],
    "10d. Crashed Minion Workers": [
        "Run with --fix to auto-exorcise crashed worker possessions and release their tasks back to TODO."
    ],
    "11. Task Files": ["Run 's9 task sync' to regenerate missing files."],
}


class InquisitorManager:
    """Runs all diagnostic checks and produces a DiagnosticReport."""

    def __init__(self, db: Database, opencode_dir: Path) -> None:
        self.db = db
        self.opencode_dir = opencode_dir
        self.db_path = opencode_dir / "data" / "project.db"

    def run_diagnostics(
        self,
        *,
        verbose: bool = False,
        stale_hours: int = 3,
        stale_minutes_minion: int = 15,
    ) -> DiagnosticReport:
        """Run all infrastructure and data integrity checks.

        Args:
            verbose: Include detailed output in check results.
            stale_hours: Hours threshold for rogue possession detection for
                interactive (non-minion) possessions (default: 3).
            stale_minutes_minion: Minutes threshold for rogue possession
                detection for minion-mode possessions (default: 15).  Minion
                workers emit a heartbeat every 5 minutes when idle, so 15
                minutes of silence reliably indicates a crash or stall.

        Returns:
            A DiagnosticReport with all results aggregated.
        """
        report = DiagnosticReport()

        # ── Infrastructure checks ─────────────────────────────────────────
        report.infra_results.append(check_database_exists(self.db_path))
        report.infra_results.append(check_database_integrity(self.db_path))
        report.infra_results.append(check_gitignore(self.opencode_dir, verbose=verbose))
        report.infra_results.append(check_backups(self.opencode_dir, verbose=verbose))
        report.infra_results.append(check_temp_files(self.db_path, verbose=verbose))

        # ── Data integrity checks ─────────────────────────────────────────
        raw_checks = [
            check_possession_daemons(self.db, verbose=verbose),
            check_task_possession_refs(self.db, verbose=verbose),
            check_task_dependencies(self.db, verbose=verbose),
            check_closed_timestamps(self.db, verbose=verbose),
            check_claimed_timestamps(self.db, verbose=verbose),
            check_possession_data(self.db, verbose=verbose),
            check_possession_logs(self.db, self.opencode_dir, verbose=verbose),
            check_daemon_incarnations(self.db, verbose=verbose),
            check_daemon_last_possession(self.db, verbose=verbose),
            check_abandoned_tasks(self.db, verbose=verbose),
            check_orphaned_underway(self.db, verbose=verbose),
            check_rogue_possessions(
                self.db, verbose=verbose, stale_hours=stale_hours, stale_minutes_minion=stale_minutes_minion
            ),
            check_crashed_minion_workers(self.db, verbose=verbose),
            check_task_files(self.db, self.opencode_dir, verbose=verbose),
        ]

        for label, issues in raw_checks:
            report.data_checks.append(
                DataCheckResult(
                    label=label,
                    issues=issues,
                    pass_message=_PASS_MESSAGES.get(label, "Check passed"),
                )
            )

        return report

    def apply_fixes(self, report: DiagnosticReport) -> tuple[list[str], list[tuple[str, Exception]]]:
        """Apply all fixable issues in the report.

        Returns:
            A tuple of (fixed_descriptions, failed_tuples) where failed_tuples
            are (description, exception) pairs.
        """
        fixed: list[str] = []
        failed: list[tuple[str, Exception]] = []

        for issue in report.fixable_issues:
            if issue.fix_fn is not None:
                try:
                    issue.fix_fn()
                    fixed.append(issue.description)
                    report.issues_fixed.append(issue.description)
                except Exception as e:
                    failed.append((issue.description, e))

        return fixed, failed


def get_fail_summary(label: str, count: int) -> str:
    """Get the failure summary line for a data check."""
    template = _FAIL_SUMMARIES.get(label, "Found {n} issues")
    return template.format(n=count)


def get_fail_hints(label: str) -> list[str]:
    """Get any extra hint lines for a failed data check."""
    return _FAIL_HINTS.get(label, [])
