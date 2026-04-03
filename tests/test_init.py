"""Integration tests for site-nine init command and template rendering"""

from pathlib import Path

from site_nine.__main__ import app
from site_nine.core.templates import TemplateRenderer
from typer.testing import CliRunner

runner = CliRunner()


def test_init_command_creates_opencode_directory(project_dir: Path):
    """Test that init command creates .opencode directory"""
    result = runner.invoke(
        app,
        ["init", "--name", "test-project", "--type", "python"],
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"
    opencode_dir = project_dir / ".opencode"
    assert opencode_dir.exists()
    assert opencode_dir.is_dir()


def test_init_command_creates_database(project_dir: Path):
    """Test that init command creates database"""
    result = runner.invoke(
        app,
        ["init", "--name", "test-project", "--type", "python"],
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"
    db_file = project_dir / ".opencode" / "data" / "project.db"
    assert db_file.exists()


def test_init_command_copies_static_files(project_dir: Path):
    """Test that init copies all expected static files"""
    result = runner.invoke(
        app,
        ["init", "--name", "test-project", "--type", "python"],
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"
    opencode_dir = project_dir / ".opencode"

    assert (opencode_dir / "README.md").exists()

    commands_dir = opencode_dir / "commands"
    assert commands_dir.exists()
    expected_commands = [
        "summon.md",
        "dismiss.md",
        "handoff.md",
        "commit.md",
        "tasks.md",
        "claim-task.md",
        "close-task.md",
        "create-task.md",
        "update-task.md",
        "README.md",
    ]
    for cmd in expected_commands:
        assert (commands_dir / cmd).exists(), f"Missing command: {cmd}"

    skills_dir = opencode_dir / "skills"
    assert skills_dir.exists()
    expected_skills = [
        "handoff-workflow",
        "session-end",
        "session-start",
        "task-claim",
        "task-close",
        "task-create",
        "task-query",
        "task-update",
        "tasks-report",
    ]
    for skill in expected_skills:
        assert (skills_dir / skill / "SKILL.md").exists(), f"Missing skill: {skill}"

    assert (opencode_dir / "docs" / "guides" / "code-review.md").exists()
    assert (opencode_dir / "docs" / "guides" / "tasks.md").exists()
    assert (opencode_dir / "docs" / "guides" / "file-organization.md").exists()


def test_init_command_renders_templates(project_dir: Path):
    """Test that init renders all expected Jinja2 templates"""
    result = runner.invoke(
        app,
        ["init", "--name", "test-project", "--type", "python"],
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"
    opencode_dir = project_dir / ".opencode"

    roles_dir = opencode_dir / "docs" / "roles"
    assert roles_dir.exists()
    expected_roles = [
        "README.md",
        "administrator.md",
        "architect.md",
        "designer.md",
        "documentarian.md",
        "engineer.md",
        "inspector.md",
        "operator.md",
        "tester.md",
    ]
    for role in expected_roles:
        assert (roles_dir / role).exists(), f"Missing role: {role}"

    guides_dir = opencode_dir / "docs" / "guides"
    expected_rendered_guides = [
        "README.md",
        "adr-workflow.md",
        "commit-guidelines.md",
        "markdown-style.md",
        "task-sizing.md",
        "testing.md",
        "troubleshooting.md",
    ]
    for guide in expected_rendered_guides:
        assert (guides_dir / guide).exists(), f"Missing guide: {guide}"


def test_init_command_renders_project_name_in_templates(project_dir: Path):
    """Test that project name is correctly inserted into templates"""
    result = runner.invoke(
        app,
        ["init", "--name", "my-awesome-project", "--type", "python", "--description", "An awesome test project"],
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"

    roles_readme = (project_dir / ".opencode" / "docs" / "roles" / "README.md").read_text()
    assert "my-awesome-project" in roles_readme

    engineer = (project_dir / ".opencode" / "docs" / "roles" / "engineer.md").read_text()
    assert "my-awesome-project" in engineer


def test_init_command_creates_empty_work_dirs(project_dir: Path):
    """Test that init creates empty work directories"""
    result = runner.invoke(
        app,
        ["init", "--name", "test-project", "--type", "python"],
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"
    opencode_dir = project_dir / ".opencode"

    assert (opencode_dir / "work" / "tasks").exists()
    assert (opencode_dir / "work" / "epics").exists()
    assert (opencode_dir / "work" / "possessions").exists()
    assert (opencode_dir / "work" / "planning").exists()
    assert (opencode_dir / "work" / "scripts").exists()
    assert (opencode_dir / "work" / "sessions").exists()
    assert (opencode_dir / "work" / "test-plans").exists()


def test_init_command_populates_daemon_names(project_dir: Path):
    """Test that init command populates personas in database"""
    result = runner.invoke(
        app,
        ["init", "--name", "test-project", "--type", "python"],
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"

    from site_nine.core.database import Database

    with Database(project_dir / ".opencode" / "data" / "project.db") as db:
        daemons = db.execute_query("SELECT COUNT(*) as count FROM daemons")
        assert daemons[0]["count"] > 0


def test_init_command_fails_if_opencode_exists(project_dir: Path):
    """Test that init command fails if .opencode already exists"""
    (project_dir / ".opencode").mkdir()

    result = runner.invoke(
        app,
        ["init", "--name", "test-project", "--type", "python"],
    )

    assert result.exit_code != 0
    assert "already exists" in result.output.lower()


def test_init_command_force_removes_existing(project_dir: Path):
    """Test that --force removes existing .opencode before reinitializing"""
    opencode_dir = project_dir / ".opencode"
    opencode_dir.mkdir()
    sentinel = opencode_dir / "should_be_gone.txt"
    sentinel.write_text("old content")

    result = runner.invoke(
        app,
        ["init", "--force", "--name", "test-project", "--type", "python"],
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert not sentinel.exists(), "Force should have wiped old contents"
    assert opencode_dir.exists(), ".opencode should be recreated"
    assert (opencode_dir / "data" / "project.db").exists()


def test_init_command_with_directory_option(tmp_path: Path):
    """Test that --directory creates .opencode in a specified directory"""
    target = tmp_path / "my-project"
    target.mkdir()

    result = runner.invoke(
        app,
        ["init", "--directory", str(target), "--name", "my-project", "--type", "python"],
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert (target / ".opencode").exists()
    assert (target / ".opencode" / "data" / "project.db").exists()


def test_init_command_directory_not_found(tmp_path: Path):
    """Test that init fails when --directory points to a nonexistent path"""
    result = runner.invoke(
        app,
        ["init", "--directory", str(tmp_path / "nope"), "--name", "x", "--type", "python"],
    )

    assert result.exit_code != 0
    assert "does not exist" in result.output.lower()


def test_template_renderer_with_context():
    """Test template renderer with custom context"""
    renderer = TemplateRenderer()

    template_str = "Hello {{ name }}!"
    result = renderer.env.from_string(template_str).render(name="World")
    assert result == "Hello World!"


def test_template_renderer_renders_scaffold_templates(temp_dir: Path):
    """Test that all scaffold Jinja2 templates render without errors"""
    renderer = TemplateRenderer()
    output_dir = temp_dir / "output"
    output_dir.mkdir()

    context = {
        "project_name": "test-project",
        "project_name_hyphen": "test-project",
        "project_name_underscore": "test_project",
        "project_type": "python",
        "project_description": "A test project",
    }

    scaffold_templates = renderer.scaffold_templates()
    assert len(scaffold_templates) > 0, "No scaffold templates found"

    for template_name in scaffold_templates:
        rel_path = template_name.removeprefix("scaffold/templates/").removesuffix(".jinja")
        output_path = output_dir / rel_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        renderer.render_to_file(template_name, output_path, **context)
        assert output_path.exists(), f"Template {template_name} did not create output file"
        assert output_path.stat().st_size > 0, f"Template {template_name} created empty file"


def test_scaffold_static_dir_exists():
    """Test that the scaffold static directory exists and has files"""
    renderer = TemplateRenderer()
    static_dir = renderer.scaffold_static_dir()
    assert static_dir.exists(), f"Static dir not found: {static_dir}"
    static_files = list(static_dir.rglob("*"))
    assert len([f for f in static_files if f.is_file()]) > 0


def test_init_with_typescript_project(project_dir: Path):
    """Test init command with TypeScript project type"""
    result = runner.invoke(
        app,
        ["init", "--name", "typescript-project", "--type", "typescript"],
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"
    opencode_dir = project_dir / ".opencode"
    assert opencode_dir.exists()


def test_template_renderer_list_templates():
    """Test listing all available templates"""
    renderer = TemplateRenderer()
    templates = renderer.list_templates()

    assert isinstance(templates, list)
    assert len(templates) > 0
    assert any("README.md.jinja" in t for t in templates)


def test_get_default_context():
    """Test getting default template context"""
    from site_nine.core.templates import get_default_context

    context = get_default_context("test-project")

    assert context["project_name"] == "test-project"
    assert context["project_name_hyphen"] == "test-project"
    assert context["project_name_underscore"] == "test_project"
    assert "generated_at" in context
