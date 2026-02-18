"""Rich rendering helpers for doctor diagnostic output.

These functions produce Rich renderables from DiagnosticReport data.
The CLI layer calls these and passes results to terminal_message.
"""

from __future__ import annotations

from rich.table import Table
from snick import conjoin

from site_nine.doctor.models import DiagnosticReport, InfraResult


# =============================================================================
# Infrastructure result rendering
# =============================================================================


def infra_subject_color(result: InfraResult) -> str:
    """Determine the subject color for an infrastructure result."""
    if result.warning:
        return "yellow"
    if result.passed:
        return "green"
    return "red"


def render_infra_message(result: InfraResult) -> str:
    """Build the message body for an infrastructure result, including detail lines."""
    if result.detail_lines:
        return conjoin(result.message, *result.detail_lines)
    return result.message


# =============================================================================
# Summary table
# =============================================================================


def render_summary_table(report: DiagnosticReport) -> Table:
    """Build the summary table showing passed/warnings/failed counts."""
    table = Table(title="Summary", show_header=True, header_style="bold")
    table.add_column("Category", style="bold")
    table.add_column("Passed", justify="center")
    table.add_column("Warnings", justify="center")
    table.add_column("Failed", justify="center")

    table.add_row(
        "Infrastructure",
        f"[green]{report.infra_passed}[/green]",
        f"[yellow]{report.infra_warnings}[/yellow]",
        f"[red]{report.infra_failed}[/red]",
    )
    table.add_row(
        "Data Integrity",
        "[green]--[/green]",
        f"[yellow]{len(report.warning_issues) + len(report.fixable_issues)}[/yellow]",
        f"[red]{len(report.error_issues)}[/red]",
    )

    return table


def render_summary_body(report: DiagnosticReport) -> str:
    """Build the summary body text listing issue counts by type."""
    body_lines: list[str] = []
    if report.fixable_issues:
        body_lines.append(f"{len(report.fixable_issues)} fixable issues")
    if report.warning_issues:
        body_lines.append(f"{len(report.warning_issues)} warnings")
    if report.error_issues:
        body_lines.append(f"{len(report.error_issues)} errors requiring manual fix")
    if report.infra_warnings:
        body_lines.append(f"{report.infra_warnings} infrastructure warnings")
    if report.infra_failed:
        body_lines.append(f"{report.infra_failed} infrastructure failures")
    return conjoin(*body_lines)
