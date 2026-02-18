from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from site_nine.core.database import Database
from site_nine.core.models import ProjectConfig
from site_nine.core.templates import TemplateRenderer, copy_static_scaffold, render_scaffold_templates
from site_nine.init.exceptions import InitError
from site_nine.init.models import InitResult

PROJECT_TYPES = ["python", "typescript", "go", "rust", "other"]

WORK_SUBDIRECTORIES = [
    "work/tasks",
    "work/epics",
    "work/missions",
    "work/planning",
    "work/scripts",
    "work/sessions",
    "work/test-plans",
]


class InitManager:
    """Manages project initialization."""

    def __init__(self, target_dir: Path) -> None:
        self.target_dir = target_dir.resolve()
        self.opencode_dir = self.target_dir / ".opencode"

    def validate_target(self) -> None:
        """Validate the target directory exists and is a directory.

        Raises:
            InitError: If target doesn't exist or isn't a directory.
        """
        InitError.require_condition(self.target_dir.exists(), f"Target directory does not exist: {self.target_dir}")
        InitError.require_condition(self.target_dir.is_dir(), f"Target path is not a directory: {self.target_dir}")

    def check_existing(self, force: bool) -> bool:
        """Check if .opencode already exists and handle accordingly.

        Args:
            force: If True, remove existing .opencode directory.

        Returns:
            True if an existing directory was removed, False if none existed.

        Raises:
            InitError: If .opencode exists and force is False.
        """
        if not self.opencode_dir.exists():
            return False

        InitError.require_condition(
            force,
            f".opencode already exists at {self.opencode_dir}. "
            "Use --force to overwrite (this will delete all existing contents)",
        )

        shutil.rmtree(self.opencode_dir)
        return True

    def create_opencode_dir(self) -> None:
        """Create the .opencode directory."""
        self.opencode_dir.mkdir(exist_ok=True)

    def initialize_database(self) -> int:
        """Initialize the database with schema and seed data.

        Returns:
            Number of personas seeded.
        """
        db_path = self.opencode_dir / "data" / "project.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with Database(db_path) as db:
            db.initialize_schema()
            db.seed_data()

        return 256

    def copy_static_files(self) -> int:
        """Copy static scaffold files into .opencode."""
        renderer = TemplateRenderer()
        return copy_static_scaffold(renderer.scaffold_static_dir(), self.opencode_dir)

    def render_templates(self, config: ProjectConfig) -> int:
        """Render Jinja2 scaffold templates into .opencode."""
        renderer = TemplateRenderer()
        context = config.template_context()
        return render_scaffold_templates(renderer, self.opencode_dir, context)

    def create_work_directories(self) -> None:
        """Create empty work subdirectories."""
        for subdir in WORK_SUBDIRECTORIES:
            (self.opencode_dir / subdir).mkdir(parents=True, exist_ok=True)

    def initialize(self, config: ProjectConfig) -> InitResult:
        """Run the full initialization sequence.

        Convenience method that calls all steps in order. Use the individual
        step methods instead if per-step progress reporting is needed.

        Args:
            config: Project configuration for template rendering.

        Returns:
            InitResult with counts of files created.
        """
        self.create_opencode_dir()
        persona_count = self.initialize_database()
        static_count = self.copy_static_files()
        template_count = self.render_templates(config)
        self.create_work_directories()

        return InitResult(
            opencode_dir=str(self.opencode_dir),
            static_count=static_count,
            template_count=template_count,
            persona_count=persona_count,
        )
