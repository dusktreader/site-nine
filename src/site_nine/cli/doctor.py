"""Health check, diagnostics, and repair commands"""

from __future__ import annotations

from typing import Annotated

import typer
from snick import conjoin
from typerdrive import handle_errors, terminal_message

from site_nine.cli.utils import CLIError
from site_nine.core.database import Database
from site_nine.core.paths import get_opencode_dir
from site_nine.doctor.manager import DoctorManager, get_fail_hints, get_fail_summary
from site_nine.doctor.models import Severity
from site_nine.doctor.rendering import (
    infra_subject_color,
    render_infra_message,
    render_summary_body,
    render_summary_table,
)
from site_nine.exceptions import SiteNineError


@handle_errors("Failed to run health checks", handle_exc_class=SiteNineError)
def doctor_command(
    fix: Annotated[bool, typer.Option("--fix", help="Apply fixes automatically")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show detailed output")] = False,
) -> None:
    """Run health checks and validate data integrity (typically used by: humans)

    Performs comprehensive checks on the project infrastructure and database:

    Infrastructure checks:
    - Database file existence
    - Database integrity (SQLite PRAGMA integrity_check)
    - Gitignore pattern validation
    - Backup file detection
    - SQLite temporary file detection

    Data integrity checks:
    - Invalid foreign key references
    - Inconsistent task states
    - Mission data issues
    - Incorrect mission counters
    - Missing files
    - Abandoned work detection

    By default, only reports issues. Use --fix to automatically repair safe issues.
    """
    try:
        opencode_dir = get_opencode_dir()
    except FileNotFoundError:
        raise CLIError("No .opencode directory found. Run 's9 init' first.")

    db_path = opencode_dir / "data" / "project.db"

    CLIError.require_condition(
        db_path.exists(),
        conjoin(
            f"Database file not found: {db_path}",
            "Run 's9 init' to initialize the project.",
        ),
    )

    terminal_message("Running diagnostics...", subject="Doctor")

    with Database(db_path) as db:
        manager = DoctorManager(db, opencode_dir)
        report = manager.run_diagnostics(verbose=verbose)

        # ── Render infrastructure results ─────────────────────────────────
        for result in report.infra_results:
            terminal_message(
                render_infra_message(result),
                subject=result.name,
                subject_color=infra_subject_color(result),
            )

        # ── Render data check results ─────────────────────────────────────
        for check in report.data_checks:
            if not check.issues:
                terminal_message(check.pass_message, subject=check.label, subject_color="green")
            else:
                # Determine color based on severities
                severities = {i.severity for i in check.issues}
                if Severity.ERROR in severities:
                    color = "red"
                else:
                    color = "yellow"

                # Build message body
                summary_line = get_fail_summary(check.label, len(check.issues))
                hints = get_fail_hints(check.label)
                detail_lines: list[str] = []
                if verbose:
                    for issue in check.issues:
                        detail_lines.append(f"  {issue.description}")

                body = conjoin(summary_line, *hints, *detail_lines)
                terminal_message(body, subject=check.label, subject_color=color)

        # ── Summary ───────────────────────────────────────────────────────
        terminal_message(render_summary_table(report), indent=False)

        if report.all_clear:
            terminal_message("All checks passed! No issues found.", subject="Result", subject_color="green")
        else:
            terminal_message(render_summary_body(report), subject="Issues Found", subject_color="yellow")

            if report.fixable_issues and not fix:
                terminal_message(
                    "Run with --fix to automatically repair fixable issues.",
                    subject="Hint",
                    subject_color="cyan",
                )

            if report.error_issues:
                terminal_message(
                    "Some issues require manual intervention.",
                    subject="Warning",
                    subject_color="red",
                )

        # ── Apply fixes ───────────────────────────────────────────────────
        if fix and report.fixable_issues:
            terminal_message("Applying fixes...", subject="Fix", subject_color="cyan")

            fixed, failed = manager.apply_fixes(report)

            for desc in fixed:
                terminal_message(f"Fixed: {desc}", subject="OK", subject_color="green")

            for desc, err in failed:
                terminal_message(
                    conjoin(f"Failed to fix: {desc}", f"Error: {err}"),
                    subject="Failed",
                    subject_color="red",
                )

            terminal_message(
                f"Fixed {len(fixed)} issues",
                subject="Fix Complete",
                subject_color="green",
            )

            if failed:
                terminal_message(
                    f"{len(failed)} fixes failed",
                    subject="Warning",
                    subject_color="yellow",
                )
