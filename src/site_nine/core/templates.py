"""Template rendering for site-nine"""

import shutil
from importlib.resources import files
from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape

from site_nine.core.models import ProjectConfig


class TemplateRenderer:
    """Renders Jinja2 templates for .opencode structure"""

    def __init__(self) -> None:
        self.env = Environment(
            loader=PackageLoader("site_nine", "templates"),
            autoescape=select_autoescape(),
            keep_trailing_newline=True,
        )

    def render_template(self, template_name: str, **context: Any) -> str:
        """Render a template with given context"""
        template = self.env.get_template(template_name)
        return template.render(**context)

    def render_to_file(self, template_name: str, output_path: Path, **context: Any) -> None:
        """Render template and write to file"""
        content = self.render_template(template_name, **context)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)

    def list_templates(self) -> list[str]:
        """List all available templates"""
        return self.env.list_templates()

    def scaffold_static_dir(self) -> Path:
        """Return the path to the scaffold static files directory."""
        ref = files("site_nine") / "templates" / "scaffold" / "static"
        return Path(str(ref))

    def scaffold_templates(self) -> list[str]:
        """List scaffold Jinja2 templates (relative to the templates package root)."""
        return [t for t in self.env.list_templates() if t.startswith("scaffold/templates/")]


def copy_static_scaffold(static_dir: Path, output_dir: Path) -> int:
    """Recursively copy all static scaffold files into the output directory.

    Returns the number of files copied.
    """
    count = 0
    for src_file in static_dir.rglob("*"):
        if not src_file.is_file():
            continue
        rel = src_file.relative_to(static_dir)
        dest = output_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dest)
        count += 1
    return count


def render_scaffold_templates(renderer: TemplateRenderer, output_dir: Path, context: dict[str, Any]) -> int:
    """Render all scaffold Jinja2 templates into the output directory.

    Template names follow the pattern ``scaffold/templates/<path>.jinja``.
    The ``.jinja`` suffix is stripped and ``scaffold/templates/`` prefix is
    removed to produce the output path relative to *output_dir*.

    Returns the number of files rendered.
    """
    count = 0
    for template_name in renderer.scaffold_templates():
        rel_path = template_name.removeprefix("scaffold/templates/").removesuffix(".jinja")
        renderer.render_to_file(template_name, output_dir / rel_path, **context)
        count += 1
    return count


def get_default_context(project_name: str = "my-project") -> dict[str, Any]:
    """Get default template context.

    .. deprecated::
        Use ``ProjectConfig(name=project_name).template_context()`` instead.
    """
    return ProjectConfig(name=project_name, type="software project").template_context()
