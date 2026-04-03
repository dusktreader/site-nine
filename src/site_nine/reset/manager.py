from pathlib import Path

from site_nine.core.database import Database
from site_nine.reset.models import ResetCounts, ResetResult


class ResetManager:
    """Manages project data reset operations"""

    def __init__(self, db: Database) -> None:
        self.db = db

    def get_counts(self) -> ResetCounts:
        """Get current record counts for possessions, tasks, and dependencies."""
        possession_count = self.db.execute_query("SELECT COUNT(*) as count FROM possessions")[0]["count"]
        task_count = self.db.execute_query("SELECT COUNT(*) as count FROM tasks")[0]["count"]
        dep_count = self.db.execute_query("SELECT COUNT(*) as count FROM task_dependencies")[0]["count"]
        return ResetCounts(missions=possession_count, tasks=task_count, dependencies=dep_count)

    def delete_files(self, opencode_dir: Path) -> tuple[int, int, list[str]]:
        """
        Delete possession and task markdown files.

        Returns:
            Tuple of (possession_files_deleted, task_files_deleted, warnings)
        """
        warnings: list[str] = []

        possession_files = self._delete_dir_files(
            opencode_dir / "work" / "possessions",
            skip={"README.md", "TEMPLATE.md"},
            warnings=warnings,
        )

        task_files = self._delete_dir_files(
            opencode_dir / "work" / "tasks",
            skip={"README.md"},
            warnings=warnings,
        )

        return possession_files, task_files, warnings

    def delete_records(self, counts: ResetCounts) -> None:
        """Delete all possession, task, and dependency records, and reset daemon counters."""
        self.db.execute_update("DELETE FROM task_dependencies")
        self.db.execute_update("DELETE FROM tasks")
        self.db.execute_update("DELETE FROM possessions")
        self.db.execute_update("UPDATE daemons SET incarnations = 0, last_possession = NULL")

    def vacuum(self) -> str | None:
        """
        Vacuum the database to reclaim space.

        Returns:
            Warning message if vacuum failed, None on success
        """
        try:
            self.db.execute_update("VACUUM")
            return None
        except Exception as e:
            return f"Failed to vacuum database: {e}"

    def reset(self, opencode_dir: Path) -> ResetResult:
        """
        Perform full project reset: delete files, records, and vacuum.

        Args:
            opencode_dir: Path to the .opencode directory

        Returns:
            ResetResult with counts of deleted items and any warnings
        """
        counts = self.get_counts()

        possession_files, task_files, warnings = self.delete_files(opencode_dir)

        self.delete_records(counts)

        vacuum_warning = self.vacuum()
        if vacuum_warning:
            warnings.append(vacuum_warning)

        return ResetResult(
            mission_files=possession_files,
            task_files=task_files,
            mission_records=counts.missions,
            task_records=counts.tasks,
            dependency_records=counts.dependencies,
            warnings=warnings,
        )

    @staticmethod
    def _delete_dir_files(
        directory: Path,
        skip: set[str] | None = None,
        warnings: list[str] | None = None,
    ) -> int:
        """
        Delete .md files in a directory, optionally skipping specific filenames.

        Returns:
            Number of files successfully deleted
        """
        if warnings is None:
            warnings = []
        skip = skip or set()
        deleted = 0

        if not directory.exists():
            return 0

        for md_file in directory.glob("*.md"):
            if md_file.name in skip:
                continue
            try:
                md_file.unlink()
                deleted += 1
            except Exception as e:
                warnings.append(f"Failed to delete {md_file.name}: {e}")

        return deleted
