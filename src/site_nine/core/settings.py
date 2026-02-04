"""Typerdrive settings for site-nine"""

from pydantic import BaseModel, Field


class SiteNineSettings(BaseModel):
    """Main site-nine settings for typerdrive integration"""

    # Project settings
    project_name: str = Field(default="my-project", description="Project name")
    project_type: str = Field(default="python", description="Project type")
    project_description: str = Field(default="", description="Project description")

    # Feature flags
    enable_pm_system: bool = Field(default=True, description="Enable project management system")
    enable_session_tracking: bool = Field(default=True, description="Enable mission tracking")
    enable_commit_guidelines: bool = Field(default=True, description="Enable commit guidelines")
    enable_persona_naming: bool = Field(default=True, description="Enable persona system")

    # Customization
    persona_theme: str = Field(default="mythology", description="Persona theme (mythology, tech, etc)")
    template_dir: str = Field(default="", description="Custom template directory (empty = use default)")
    default_model: str = Field(
        default="github-copilot/claude-sonnet-4.5", description="Default model for s9 summon command"
    )

    class Config:
        """Pydantic configuration"""

        json_schema_extra = {
            "example": {
                "project_name": "my-project",
                "project_type": "python",
                "enable_pm_system": True,
                "persona_theme": "mythology",
            }
        }


def get_default_model() -> str:
    """Get the default model from user settings"""
    from pathlib import Path
    import json
    from typerdrive import get_typerdrive_config

    # Get the settings file path
    config = get_typerdrive_config()
    settings_path = Path(config.settings_path)

    # Load from file if it exists
    if settings_path.exists():
        try:
            data = json.loads(settings_path.read_text())
            return data.get("default_model", "github-copilot/claude-sonnet-4.5")
        except Exception:
            pass

    # Fallback if settings can't be loaded
    return "github-copilot/claude-sonnet-4.5"
