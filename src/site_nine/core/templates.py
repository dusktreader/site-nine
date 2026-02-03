"""Template rendering for site-nine"""

from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape


class TemplateRenderer:
    """Renders Jinja2 templates for .opencode structure"""

    def __init__(self) -> None:
        self.env = Environment(
            loader=PackageLoader("site_nine", "templates"),
            autoescape=select_autoescape(),
            keep_trailing_newline=True,
        )

    def render_template(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a template with given context"""
        template = self.env.get_template(template_name)
        return template.render(**context)

    def render_to_file(self, template_name: str, output_path: Path, context: dict[str, Any]) -> None:
        """Render template and write to file"""
        content = self.render_template(template_name, context)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)

    def list_templates(self) -> list[str]:
        """List all available templates"""
        return self.env.list_templates()


def get_default_context(project_name: str = "my-project") -> dict[str, Any]:
    """Get default template context"""
    return {
        "project_name": project_name,
        "project_name_hyphen": project_name.lower().replace("_", "-"),
        "project_name_underscore": project_name.lower().replace("-", "_"),
        "project_type": "software project",
        "project_description": "",
        "generated_at": datetime.now().isoformat(),
        "has_pm_system": True,
        "has_session_tracking": True,
        "has_commit_guidelines": True,
    }
