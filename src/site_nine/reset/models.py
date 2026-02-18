from dataclasses import dataclass, field


@dataclass
class ResetCounts:
    """Pre-reset record counts"""

    missions: int
    tasks: int
    dependencies: int

    @property
    def is_empty(self) -> bool:
        return self.missions == 0 and self.tasks == 0


@dataclass
class ResetResult:
    """Summary of what was deleted during reset"""

    mission_files: int = 0
    handoff_files: int = 0
    task_files: int = 0
    mission_records: int = 0
    task_records: int = 0
    dependency_records: int = 0
    warnings: list[str] = field(default_factory=list)
