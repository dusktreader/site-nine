"""Doctor diagnostic models.

These dataclasses capture the results of infrastructure and data integrity
checks. The CLI layer uses them to render output; the manager layer produces them.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    """How serious a diagnostic issue is."""

    ERROR = "error"
    WARNING = "warning"
    FIXABLE = "fixable"


@dataclass
class DiagnosticIssue:
    """A single issue found during diagnostics."""

    category: str
    severity: Severity
    description: str
    fix_fn: Callable[[], None] | None = None


@dataclass
class InfraResult:
    """Result of a single infrastructure check."""

    name: str
    passed: bool
    warning: bool = False
    message: str = ""
    detail_lines: list[str] = field(default_factory=list)


@dataclass
class DataCheckResult:
    """Result of a single data integrity check, preserving its label."""

    label: str
    issues: list[DiagnosticIssue] = field(default_factory=list)
    pass_message: str = ""


@dataclass
class DiagnosticReport:
    """Aggregated results from all diagnostic checks."""

    infra_results: list[InfraResult] = field(default_factory=list)
    data_checks: list[DataCheckResult] = field(default_factory=list)
    issues_fixed: list[str] = field(default_factory=list)

    @property
    def all_issues(self) -> list[DiagnosticIssue]:
        """Flat list of all data integrity issues."""
        result: list[DiagnosticIssue] = []
        for check in self.data_checks:
            result.extend(check.issues)
        return result

    @property
    def infra_passed(self) -> int:
        return sum(1 for r in self.infra_results if r.passed and not r.warning)

    @property
    def infra_warnings(self) -> int:
        return sum(1 for r in self.infra_results if r.warning)

    @property
    def infra_failed(self) -> int:
        return sum(1 for r in self.infra_results if not r.passed and not r.warning)

    @property
    def fixable_issues(self) -> list[DiagnosticIssue]:
        return [i for i in self.all_issues if i.severity == Severity.FIXABLE and i.fix_fn is not None]

    @property
    def warning_issues(self) -> list[DiagnosticIssue]:
        return [i for i in self.all_issues if i.severity == Severity.WARNING]

    @property
    def error_issues(self) -> list[DiagnosticIssue]:
        return [i for i in self.all_issues if i.severity == Severity.ERROR]

    @property
    def has_issues(self) -> bool:
        return bool(self.all_issues) or self.infra_failed > 0 or self.infra_warnings > 0

    @property
    def all_clear(self) -> bool:
        return not self.has_issues
