from pydantic import BaseModel, Field

DEFAULT_MODEL = "github-copilot/claude-sonnet-4.6"


class SiteNineSettings(BaseModel):
    default_model: str = Field(default=DEFAULT_MODEL, description="Default model for s9 summon command")
