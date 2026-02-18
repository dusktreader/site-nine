"""Core domain models"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pendulum


@dataclass
class ProjectConfig:
    """Project configuration collected during initialization.

    This is the structured representation of project identity metadata
    used for template rendering and future configuration needs.
    """

    name: str
    type: str = "python"
    description: str = ""

    @property
    def name_hyphen(self) -> str:
        return self.name.lower().replace("_", "-")

    @property
    def name_underscore(self) -> str:
        return self.name.lower().replace("-", "_")

    def template_context(self) -> dict[str, Any]:
        """Build Jinja2 template context for rendering .opencode templates."""
        return {
            "project_name": self.name,
            "project_name_hyphen": self.name_hyphen,
            "project_name_underscore": self.name_underscore,
            "project_type": self.type,
            "project_description": self.description,
            "date": pendulum.now("UTC").format("YYYY-MM-DD"),
            "generated_at": pendulum.now("UTC").to_iso8601_string(),
        }
