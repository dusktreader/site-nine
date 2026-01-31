"""Integration tests for site-nine init command and template rendering"""

from pathlib import Path

from s9.cli.main import app
from s9.core.config import HQueueConfig
from s9.core.templates import TemplateRenderer
from typer.testing import CliRunner

runner = CliRunner()


def test_init_command_creates_opencode_directory(project_dir: Path):
    """Test that init command creates .opencode directory"""
    result = runner.invoke(
        app,
        ["init"],
        input="\n".join(
            [
                "test-project",
                "python",
                "",
                "y",
                "y",
                "y",
                "y",
            ]
        ),
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    opencode_dir = project_dir / ".opencode"
    assert opencode_dir.exists()
    assert opencode_dir.is_dir()


def test_init_command_creates_database(project_dir: Path):
    """Test that init command creates database"""
    result = runner.invoke(
        app,
        ["init"],
        input="\n".join(
            [
                "test-project",
                "python",
                "",
                "y",
                "y",
                "y",
                "y",
            ]
        ),
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    db_file = project_dir / ".opencode" / "data" / "project.db"
    assert db_file.exists()


def test_init_command_renders_all_templates(project_dir: Path):
    """Test that init command renders all expected templates"""
    result = runner.invoke(
        app,
        ["init"],
        input="\n".join(
            [
                "test-project",
                "python",
                "",
                "y",
                "y",
                "y",
                "y",
            ]
        ),
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    opencode_dir = project_dir / ".opencode"

    # Check root files
    assert (opencode_dir / "README.md").exists()
    assert (opencode_dir / "opencode.json").exists()

    # Check agent roles
    agents_dir = opencode_dir / "agents"
    assert agents_dir.exists()
    expected_agents = [
        "manager",
        "architect",
        "builder",
        "tester",
        "documentarian",
        "designer",
        "inspector",
        "operator",
    ]
    for agent in expected_agents:
        assert (agents_dir / f"{agent}.md").exists(), f"Missing agent: {agent}"

    # Check guides
    guides_dir = opencode_dir / "guides"
    assert guides_dir.exists()
    assert (guides_dir / "AGENTS.md").exists()
    assert (guides_dir / "architecture.md").exists()
    assert (guides_dir / "design-philosophy.md").exists()
    assert (guides_dir / "README.md").exists()

    # Check procedures
    procedures_dir = opencode_dir / "procedures"
    assert procedures_dir.exists()
    assert (procedures_dir / "COMMIT_GUIDELINES.md").exists()
    assert (procedures_dir / "WORKFLOWS.md").exists()
    assert (procedures_dir / "TROUBLESHOOTING.md").exists()
    assert (procedures_dir / "TASK_WORKFLOW.md").exists()
    assert (procedures_dir / "README.md").exists()

    # Check commands
    commands_dir = opencode_dir / "commands"
    assert commands_dir.exists()
    assert (commands_dir / "README.md").exists()
    assert (commands_dir / "summon.md").exists()
    assert (commands_dir / "dismiss.md").exists()
    assert (commands_dir / "handoff.md").exists()
    assert (commands_dir / "commit.md").exists()
    assert (commands_dir / "tasks.md").exists()
    assert (commands_dir / "claim-task.md").exists()
    assert (commands_dir / "close-task.md").exists()
    assert (commands_dir / "create-task.md").exists()
    assert (commands_dir / "update-task.md").exists()

    # Check skills
    skills_dir = opencode_dir / "skills"
    assert skills_dir.exists()
    assert (skills_dir / "session-start" / "SKILL.md").exists()
    assert (skills_dir / "session-start" / "daemon-names.md").exists()
    assert (skills_dir / "session-end" / "SKILL.md").exists()
    assert (skills_dir / "handoff-workflow" / "SKILL.md").exists()
    assert (skills_dir / "task-management" / "SKILL.md").exists()
    assert (skills_dir / "tasks-report" / "SKILL.md").exists()

    # Check sessions
    sessions_dir = opencode_dir / "sessions"
    assert sessions_dir.exists()
    assert (sessions_dir / "README.md").exists()
    assert (sessions_dir / "TEMPLATE.md").exists()

    # Check empty directories
    assert (opencode_dir / "planning").exists()
    assert (opencode_dir / "scripts").exists()


def test_init_command_renders_project_name_in_templates(project_dir: Path):
    """Test that project name is correctly inserted into templates"""
    result = runner.invoke(
        app,
        ["init"],
        input="\n".join(
            [
                "my-awesome-project",
                "python",
                "An awesome test project",
                "y",
                "y",
                "y",
                "y",
            ]
        ),
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    readme = (project_dir / ".opencode" / "README.md").read_text()
    assert "my-awesome-project" in readme


def test_init_command_populates_daemon_names(project_dir: Path):
    """Test that init command populates daemon names in database"""
    result = runner.invoke(
        app,
        ["init"],
        input="\n".join(
            [
                "test-project",
                "python",
                "",
                "y",
                "y",
                "y",
                "y",
            ]
        ),
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    # Check database has daemon names
    from s9.core.database import Database

    db = Database(project_dir / ".opencode" / "data" / "project.db")
    daemon_names = db.execute_query("SELECT COUNT(*) as count FROM daemon_names")
    assert daemon_names[0]["count"] > 0


def test_init_command_fails_if_opencode_exists(project_dir: Path):
    """Test that init command fails if .opencode already exists"""
    # Create .opencode directory first
    (project_dir / ".opencode").mkdir()

    result = runner.invoke(
        app,
        ["init"],
        input="\n".join(
            [
                "test-project",
                "python",
                "",
                "y",
                "y",
                "y",
                "y",
            ]
        ),
    )

    assert result.exit_code != 0
    assert ".opencode already exists" in result.stdout or "already exists" in result.stdout.lower()


def test_template_renderer_with_context():
    """Test template renderer with custom context"""
    renderer = TemplateRenderer()

    # Test rendering a simple template string
    template_str = "Hello {{ name }}!"
    result = renderer.env.from_string(template_str).render(name="World")
    assert result == "Hello World!"


def test_template_renderer_renders_all_jinja_templates(temp_dir: Path):
    """Test that all Jinja templates can be rendered without errors"""
    renderer = TemplateRenderer()
    output_dir = temp_dir / "output"
    output_dir.mkdir()

    context = {
        "project_name": "test-project",
        "project_name_hyphen": "test-project",
        "project_name_underscore": "test_project",
        "project_type": "python",
        "project_description": "A test project",
        "has_pm_system": True,
        "has_session_tracking": True,
        "has_commit_guidelines": True,
        "agent_roles": [
            {"name": "manager", "enabled": True},
            {"name": "architect", "enabled": True},
            {"name": "builder", "enabled": True},
            {"name": "tester", "enabled": True},
            {"name": "documentarian", "enabled": True},
            {"name": "designer", "enabled": True},
            {"name": "inspector", "enabled": True},
            {"name": "operator", "enabled": True},
        ],
    }

    # Test each template can be rendered
    templates = [
        "base/README.md.jinja",
        "base/opencode.json.jinja",
        "base/agents/manager.md.jinja",
        "base/agents/architect.md.jinja",
        "base/agents/builder.md.jinja",
        "base/agents/tester.md.jinja",
        "base/agents/documentarian.md.jinja",
        "base/agents/designer.md.jinja",
        "base/agents/inspector.md.jinja",
        "base/agents/operator.md.jinja",
        "base/guides/AGENTS.md.jinja",
        "base/guides/architecture.md.jinja",
        "base/guides/design-philosophy.md.jinja",
        "base/guides/README.md.jinja",
        "base/procedures/COMMIT_GUIDELINES.md.jinja",
        "base/procedures/WORKFLOWS.md.jinja",
        "base/procedures/TROUBLESHOOTING.md.jinja",
        "base/procedures/TASK_WORKFLOW.md.jinja",
        "base/procedures/README.md.jinja",
        "base/commands/README.md.jinja",
        "base/skills/session-start/SKILL.md.jinja",
        "base/skills/session-start/daemon-names.md.jinja",
        "base/skills/session-end/SKILL.md.jinja",
        "base/skills/handoff-workflow/SKILL.md.jinja",
        "base/skills/task-management/SKILL.md.jinja",
        "base/skills/tasks-report/SKILL.md.jinja",
        "base/sessions/README.md.jinja",
        "base/sessions/TEMPLATE.md.jinja",
    ]

    for template_name in templates:
        output_path = output_dir / template_name.replace("base/", "").replace(".jinja", "")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Should not raise an exception
        renderer.render_to_file(template_name, output_path, context)
        assert output_path.exists(), f"Template {template_name} did not create output file"
        assert output_path.stat().st_size > 0, f"Template {template_name} created empty file"


def test_hqueue_config_to_template_context():
    """Test that HQueueConfig generates correct template context"""

    config = HQueueConfig.default("my-test-project")
    config.project.type = "python"
    config.project.description = "A test description"

    context = config.to_template_context()

    assert context["project_name"] == "my-test-project"
    assert context["project_name_hyphen"] == "my-test-project"
    assert context["project_name_underscore"] == "my_test_project"
    assert context["project_type"] == "python"
    assert context["project_description"] == "A test description"
    assert context["has_pm_system"] is True
    assert context["has_session_tracking"] is True
    assert context["has_commit_guidelines"] is True
    assert len(context["agent_roles"]) == 8


def test_init_without_pm_system(project_dir: Path):
    """Test init command without PM system"""
    result = runner.invoke(
        app,
        ["init"],
        input="\n".join(
            [
                "test-project",
                "python",
                "",
                "n",  # No PM system
                "y",
                "y",
                "y",
            ]
        ),
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    opencode_dir = project_dir / ".opencode"

    # Task workflow should still exist (it's always created)
    assert (opencode_dir / "procedures" / "TASK_WORKFLOW.md").exists()


def test_init_with_typescript_project(project_dir: Path):
    """Test init command with TypeScript project type"""
    result = runner.invoke(
        app,
        ["init"],
        input="\n".join(
            [
                "typescript-project",
                "typescript",
                "",
                "y",
                "y",
                "y",
                "y",
            ]
        ),
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    opencode_dir = project_dir / ".opencode"
    assert opencode_dir.exists()


def test_template_renderer_list_templates():
    """Test listing all available templates"""
    from s9.core.templates import TemplateRenderer

    renderer = TemplateRenderer()
    templates = renderer.list_templates()

    # Should return a list
    assert isinstance(templates, list)
    # Should have templates
    assert len(templates) > 0
    # Should include some expected templates
    template_names = [t for t in templates]
    assert any("opencode.json.jinja" in t for t in template_names)


def test_get_default_context():
    """Test getting default template context"""
    from s9.core.templates import get_default_context

    context = get_default_context("test-project")

    assert context["project_name"] == "test-project"
    assert context["project_name_hyphen"] == "test-project"
    assert context["project_name_underscore"] == "test_project"
    assert "generated_at" in context
    assert context["has_pm_system"] is True
