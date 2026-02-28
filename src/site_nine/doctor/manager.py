"""Doctor manager — orchestrates infrastructure and data integrity checks."""

from __future__ import annotations

from pathlib import Path

from site_nine.core.database import Database
from site_nine.doctor.checks import (
    check_abandoned_tasks,
    check_backups,
    check_claimed_timestamps,
    check_closed_timestamps,
    check_database_exists,
    check_database_integrity,
    check_gitignore,
    check_last_mission_dates,
    check_mission_counts,
    check_mission_data,
    check_mission_files,
    check_mission_personas,
    check_orphaned_underway,
    check_stale_missions,
    check_task_dependencies,
    check_task_files,
    check_task_mission_refs,
    check_temp_files,
)
from site_nine.doctor.models import DataCheckResult, DiagnosticReport


# Pass messages for each data check, keyed by label.
# These are displayed when a check finds zero issues.
_PASS_MESSAGES: dict[str, str] = {
    "6a. Mission Personas": "All mission persona_names are valid",
    "6b. Task Mission Refs": "All task mission references are valid",
    "6c. Task Dependencies": "All task dependencies are valid",
    "7a. Closed Timestamps": "All completed/aborted tasks have closed_at",
    "7b. Claimed Timestamps": "All UNDERWAY tasks have claimed_at",
    "8a. Mission Data": "All missions have valid data structure",
    "8b. Mission Files": "All mission files exist",
    "9a. Mission Counts": "All mission counts are correct",
    "9b. Last Mission Dates": "All last_mission_at timestamps are correct",
    "10a. Abandoned Tasks": "No tasks abandoned by ended missions",
    "10b. Orphaned Tasks": "No orphaned UNDERWAY tasks",
    "10c. Stale Missions": "No stale SUSPENDED or ACTIVE missions",
    "11. Task Files": "All task files exist",
}

# Fail summary messages for checks that include them in the original output.
_FAIL_SUMMARIES: dict[str, str] = {
    "6a. Mission Personas": "Found {n} invalid mission references",
    "6b. Task Mission Refs": "Found {n} orphaned task references",
    "6c. Task Dependencies": "Found {n} invalid dependencies",
    "7a. Closed Timestamps": "Found {n} tasks missing closed_at",
    "7b. Claimed Timestamps": "Found {n} incomplete UNDERWAY tasks",
    "8a. Mission Data": "Found {n} missions with invalid data",
    "8b. Mission Files": "Found {n} missing mission files",
    "9a. Mission Counts": "Found {n} incorrect mission counts",
    "9b. Last Mission Dates": "Found {n} incorrect last_mission_at timestamps",
    "10a. Abandoned Tasks": "Found {n} tasks abandoned by ended missions",
    "10b. Orphaned Tasks": "Found {n} orphaned UNDERWAY tasks",
    "10c. Stale Missions": "Found {n} stale missions (SUSPENDED >7d or ACTIVE with no recent activity)",
    "11. Task Files": "Found {n} missing task files",
}

# Extra hint lines appended after the fail summary for some checks.
_FAIL_HINTS: dict[str, list[str]] = {
    "10a. Abandoned Tasks": ["These tasks should be manually reviewed and marked COMPLETE or TODO."],
    "10b. Orphaned Tasks": ["These tasks should be manually reviewed and released or completed."],
    "10c. Stale Missions": [
        "Suspended missions can be resumed with 's9 mission resume <id>' or ended with 's9 mission end <id>'."
    ],
    "11. Task Files": ["Run 's9 task sync' to regenerate missing files."],
}


class DoctorManager:
    """Runs all diagnostic checks and produces a DiagnosticReport."""

    def __init__(self, db: Database, opencode_dir: Path) -> None:
        self.db = db
        self.opencode_dir = opencode_dir
        self.db_path = opencode_dir / "data" / "project.db"

    def run_diagnostics(self, *, verbose: bool = False, stale_days: int = 7) -> DiagnosticReport:
        """Run all infrastructure and data integrity checks.

        Args:
            verbose: Include detailed output in check results.
            stale_days: Number of days after which a mission is considered stale (default: 7)

        Returns:
            A DiagnosticReport with all results aggregated.
        """
        report = DiagnosticReport()

        # ── Infrastructure checks ─────────────────────────────────────────
        # NOTE: The CLI layer guards against missing db_path before calling us,
        # so check_database_exists will always pass here. We still include it
        # so the "Database file exists" message appears in the output.
        report.infra_results.append(check_database_exists(self.db_path))
        report.infra_results.append(check_database_integrity(self.db_path))
        report.infra_results.append(check_gitignore(self.opencode_dir, verbose=verbose))
        report.infra_results.append(check_backups(self.opencode_dir, verbose=verbose))
        report.infra_results.append(check_temp_files(self.db_path, verbose=verbose))

        # ── Data integrity checks ─────────────────────────────────────────
        raw_checks = [
            check_mission_personas(self.db, verbose=verbose),
            check_task_mission_refs(self.db, verbose=verbose),
            check_task_dependencies(self.db, verbose=verbose),
            check_closed_timestamps(self.db, verbose=verbose),
            check_claimed_timestamps(self.db, verbose=verbose),
            check_mission_data(self.db, verbose=verbose),
            check_mission_files(self.db, self.opencode_dir, verbose=verbose),
            check_mission_counts(self.db, verbose=verbose),
            check_last_mission_dates(self.db, verbose=verbose),
            check_abandoned_tasks(self.db, verbose=verbose),
            check_orphaned_underway(self.db, verbose=verbose),
            check_stale_missions(self.db, self.opencode_dir, verbose=verbose, stale_days=stale_days),
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
