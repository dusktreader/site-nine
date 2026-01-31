"""Tests for configuration wizard and config management"""

from s9.core.config import (
    AgentRoleConfig,
    CustomizationConfig,
    FeaturesConfig,
    HQueueConfig,
    ProjectConfig,
)


def test_project_config_defaults():
    """Test ProjectConfig default values"""
    config = ProjectConfig(name="test-project")

    assert config.name == "test-project"
    assert config.type == "python"
    assert config.description == ""


def test_features_config_defaults():
    """Test FeaturesConfig default values"""
    config = FeaturesConfig()

    assert config.pm_system is True
    assert config.session_tracking is True
    assert config.commit_guidelines is True
    assert config.daemon_naming is True


def test_features_config_custom():
    """Test FeaturesConfig with custom values"""
    config = FeaturesConfig(
        pm_system=False,
        session_tracking=True,
        commit_guidelines=False,
    )

    assert config.pm_system is False
    assert config.session_tracking is True
    assert config.commit_guidelines is False


def test_agent_role_config():
    """Test AgentRoleConfig"""
    role = AgentRoleConfig(name="builder", enabled=True, description="Builds code")

    assert role.name == "builder"
    assert role.enabled is True
    assert role.description == "Builds code"


def test_agent_role_config_defaults():
    """Test AgentRoleConfig defaults"""
    role = AgentRoleConfig(name="tester")

    assert role.name == "tester"
    assert role.enabled is True
    assert role.description is None


def test_customization_config_defaults():
    """Test CustomizationConfig defaults"""
    config = CustomizationConfig()

    assert config.daemon_names == "mythology"
    assert config.template_dir is None
    assert config.variables == {}


def test_hqueue_config_default():
    """Test HQueueConfig.default() factory method"""
    config = HQueueConfig.default("my-project")

    assert config.project.name == "my-project"
    assert config.project.type == "python"
    assert len(config.agent_roles) == 8
    assert config.features.pm_system is True
    assert config.features.session_tracking is True


def test_hqueue_config_default_roles():
    """Test that default config includes all expected roles"""
    config = HQueueConfig.default("test-project")

    role_names = [role.name for role in config.agent_roles]
    expected_roles = [
        "manager",
        "architect",
        "builder",
        "tester",
        "documentarian",
        "designer",
        "inspector",
        "operator",
    ]

    assert role_names == expected_roles


def test_hqueue_config_to_template_context():
    """Test converting config to template context"""
    config = HQueueConfig.default("test-project")
    config.project.type = "python"
    config.project.description = "A test project"

    context = config.to_template_context()

    assert context["project_name"] == "test-project"
    assert context["project_name_hyphen"] == "test-project"
    assert context["project_name_underscore"] == "test_project"
    assert context["project_type"] == "python"
    assert context["project_description"] == "A test project"
    assert context["has_pm_system"] is True
    assert context["has_session_tracking"] is True
    assert context["has_commit_guidelines"] is True
    assert len(context["agent_roles"]) == 8


def test_template_context_project_name_transformations():
    """Test project name transformations in template context"""
    config = HQueueConfig.default("my_test_project")
    context = config.to_template_context()

    assert context["project_name"] == "my_test_project"
    assert context["project_name_hyphen"] == "my-test-project"
    assert context["project_name_underscore"] == "my_test_project"


def test_template_context_hyphenated_name():
    """Test project name with hyphens"""
    config = HQueueConfig.default("my-test-project")
    context = config.to_template_context()

    assert context["project_name"] == "my-test-project"
    assert context["project_name_hyphen"] == "my-test-project"
    assert context["project_name_underscore"] == "my_test_project"


def test_hqueue_config_custom_agent_roles():
    """Test HQueueConfig with custom agent roles"""
    custom_roles = [
        AgentRoleConfig("custom1", enabled=True),
        AgentRoleConfig("custom2", enabled=False),
    ]

    config = HQueueConfig(
        project=ProjectConfig(name="test"),
        agent_roles=custom_roles,
    )

    assert len(config.agent_roles) == 2
    assert config.agent_roles[0].name == "custom1"
    assert config.agent_roles[1].enabled is False


def test_hqueue_config_custom_features():
    """Test HQueueConfig with custom features"""
    features = FeaturesConfig(
        pm_system=False,
        session_tracking=True,
        commit_guidelines=False,
    )

    config = HQueueConfig(
        project=ProjectConfig(name="test"),
        features=features,
    )

    assert config.features.pm_system is False
    assert config.features.session_tracking is True
    assert config.features.commit_guidelines is False


def test_hqueue_config_customization():
    """Test HQueueConfig with customization options"""
    from pathlib import Path

    custom = CustomizationConfig(
        daemon_names="custom",
        template_dir=Path("/custom/templates"),
        variables={"key1": "value1", "key2": "value2"},
    )

    config = HQueueConfig(
        project=ProjectConfig(name="test"),
        customization=custom,
    )

    assert config.customization.daemon_names == "custom"
    assert config.customization.template_dir == Path("/custom/templates")
    assert config.customization.variables == {"key1": "value1", "key2": "value2"}


def test_template_context_includes_custom_variables():
    """Test that custom variables are included in template context"""
    custom = CustomizationConfig(variables={"custom_var": "custom_value"})

    config = HQueueConfig(
        project=ProjectConfig(name="test"),
        customization=custom,
    )

    context = config.to_template_context()

    assert "custom" in context
    assert context["custom"]["custom_var"] == "custom_value"


def test_template_context_agent_roles_structure():
    """Test that agent roles in context have correct structure"""
    config = HQueueConfig.default("test")

    context = config.to_template_context()

    assert isinstance(context["agent_roles"], list)
    assert all(isinstance(role, dict) for role in context["agent_roles"])
    assert all("name" in role and "enabled" in role for role in context["agent_roles"])


def test_hqueue_config_to_template_context_with_all_features():
    """Test template context with all features enabled"""
    config = HQueueConfig(
        project=ProjectConfig(name="full-featured", type="typescript", description="Full featured project"),
        features=FeaturesConfig(
            pm_system=True,
            session_tracking=True,
            commit_guidelines=True,
            daemon_naming=True,
        ),
        agent_roles=[AgentRoleConfig("custom-role")],
    )

    context = config.to_template_context()

    assert context["project_name"] == "full-featured"
    assert context["project_type"] == "typescript"
    assert context["project_description"] == "Full featured project"
    assert context["has_pm_system"] is True
    assert context["has_session_tracking"] is True
    assert context["has_commit_guidelines"] is True


def test_hqueue_config_to_template_context_minimal():
    """Test template context with minimal features"""
    config = HQueueConfig(
        project=ProjectConfig(name="minimal"),
        features=FeaturesConfig(
            pm_system=False,
            session_tracking=False,
            commit_guidelines=False,
        ),
        agent_roles=[],
    )

    context = config.to_template_context()

    assert context["project_name"] == "minimal"
    assert context["has_pm_system"] is False
    assert context["has_session_tracking"] is False
    assert context["has_commit_guidelines"] is False
    assert context["agent_roles"] == []


def test_hqueue_config_from_yaml(temp_dir):
    """Test loading configuration from YAML file"""

    import yaml

    # Create a test YAML config
    config_data = {
        "project": {"name": "yaml-project", "type": "python", "description": "Test project from YAML"},
        "features": {"pm_system": True, "session_tracking": False, "commit_guidelines": True, "daemon_naming": True},
        "agent_roles": [{"name": "CustomRole", "description": "A custom role"}],
    }

    config_file = temp_dir / "test-config.yaml"
    with open(config_file, "w") as f:
        yaml.safe_dump(config_data, f)

    # Load config from YAML
    config = HQueueConfig.from_yaml(config_file)

    assert config.project.name == "yaml-project"
    assert config.project.type == "python"
    assert config.project.description == "Test project from YAML"
    assert config.features.pm_system is True
    assert config.features.session_tracking is False
    assert len(config.agent_roles) == 1
    assert config.agent_roles[0].name == "CustomRole"
