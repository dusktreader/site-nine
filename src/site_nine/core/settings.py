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
    enable_session_tracking: bool = Field(default=True, description="Enable agent session tracking")
    enable_commit_guidelines: bool = Field(default=True, description="Enable commit guidelines")
    enable_daemon_naming: bool = Field(default=True, description="Enable daemon naming system")

    # Customization
    daemon_names_theme: str = Field(default="mythology", description="Daemon name theme (mythology, tech, etc)")
    template_dir: str = Field(default="", description="Custom template directory (empty = use default)")

    class Config:
        """Pydantic configuration"""

        json_schema_extra = {
            "example": {
                "project_name": "my-project",
                "project_type": "python",
                "enable_pm_system": True,
                "daemon_names_theme": "mythology",
            }
        }
