"""Configuration management for site-nine"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ProjectConfig:
    """Project configuration"""

    name: str
    type: str = "python"
    description: str = ""


@dataclass
class FeaturesConfig:
    """Feature flags"""

    pm_system: bool = True
    session_tracking: bool = True
    commit_guidelines: bool = True
    daemon_naming: bool = True


@dataclass
class CustomizationConfig:
    """Customization options"""

    personas_theme: str = "mythology"
    template_dir: Path | None = None
    variables: dict[str, Any] = field(default_factory=dict)


@dataclass
class SiteNineConfig:
    """Main site-nine configuration"""

    project: ProjectConfig
    features: FeaturesConfig = field(default_factory=FeaturesConfig)
    customization: CustomizationConfig = field(default_factory=CustomizationConfig)

    @classmethod
    def from_yaml(cls, path: Path) -> "SiteNineConfig":
        """Load configuration from YAML file"""
        with open(path) as f:
            data = yaml.safe_load(f)

        return cls(
            project=ProjectConfig(**data["project"]),
            features=FeaturesConfig(**data.get("features", {})),
            customization=CustomizationConfig(**data.get("customization", {})),
        )

    @classmethod
    def default(cls, project_name: str) -> "SiteNineConfig":
        """Create default configuration"""
        return cls(
            project=ProjectConfig(name=project_name),
        )

    def to_template_context(self) -> dict[str, Any]:
        """Convert config to Jinja2 template context"""
        from datetime import datetime

        return {
            "project_name": self.project.name,
            "project_name_hyphen": self.project.name.lower().replace("_", "-"),
            "project_name_underscore": self.project.name.lower().replace("-", "_"),
            "project_type": self.project.type,
            "project_description": self.project.description,
            "has_pm_system": self.features.pm_system,
            "has_session_tracking": self.features.session_tracking,
            "has_commit_guidelines": self.features.commit_guidelines,
            "custom": self.customization.variables,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "generated_at": datetime.now().isoformat(),
        }
