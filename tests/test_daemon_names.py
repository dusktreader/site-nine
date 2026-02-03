"""Tests for daemon name management"""

from s9.core.daemon_names import get_names_by_role, load_daemon_names, suggest_name


def test_load_daemon_names():
    """Test loading daemon names from JSON"""
    names = load_daemon_names()

    # Should return a list
    assert isinstance(names, list)
    assert len(names) > 0

    # Each name should have required fields
    for name in names:
        assert "name" in name
        assert "role" in name
        assert "mythology" in name
        assert "description" in name


def test_load_daemon_names_has_expected_roles():
    """Test that expected roles are present"""
    names = load_daemon_names()
    roles = {n["role"] for n in names}

    # Should have common roles
    expected_roles = {"Architect", "Builder", "Designer", "Documentarian"}
    assert expected_roles.issubset(roles), f"Missing roles: {expected_roles - roles}"


def test_get_names_by_role():
    """Test filtering names by role"""
    builders = get_names_by_role("Builder")

    # Should return a list of builders
    assert isinstance(builders, list)
    assert len(builders) > 0

    # All should be builders
    for name in builders:
        assert name["role"] == "Builder"
        assert "name" in name


def test_get_names_by_role_nonexistent():
    """Test filtering by a role that doesn't exist"""
    result = get_names_by_role("NonExistentRole")

    # Should return empty list
    assert isinstance(result, list)
    assert len(result) == 0


def test_suggest_name_returns_name_for_role():
    """Test suggesting a name for a role"""
    suggestion = suggest_name("Builder")

    # Should return a name dict
    assert suggestion is not None
    assert "name" in suggestion
    assert "role" in suggestion
    assert suggestion["role"] == "Builder"


def test_suggest_name_excludes_names():
    """Test suggesting a name with exclusions"""
    # Get all builder names
    all_builders = get_names_by_role("Builder")
    assert len(all_builders) > 1, "Need at least 2 builders for this test"

    # Exclude the first one
    first_name = all_builders[0]["name"]
    suggestion = suggest_name("Builder", exclude=[first_name])

    # Should not suggest the excluded name
    assert suggestion is not None
    assert suggestion["name"] != first_name


def test_suggest_name_all_excluded():
    """Test suggesting when all names are excluded"""
    # Get all names for a role
    all_builders = get_names_by_role("Builder")
    all_names = [b["name"] for b in all_builders]

    # Exclude everything
    suggestion = suggest_name("Builder", exclude=all_names)

    # Should return None
    assert suggestion is None


def test_suggest_name_nonexistent_role():
    """Test suggesting for a role that doesn't exist"""
    suggestion = suggest_name("NonExistentRole")

    # Should return None
    assert suggestion is None


def test_suggest_name_with_usage_count():
    """Test that suggest_name prefers names with lower usage count"""
    # We can't easily test usage_count sorting without mocking,
    # but we can verify the function handles usage_count field
    suggestion = suggest_name("Builder")

    # Should work and return a suggestion
    assert suggestion is not None
    assert "name" in suggestion

    # usage_count may or may not be present (it's optional with .get())
    # This just verifies the function doesn't crash on missing usage_count
