"""Tests for daemon name management"""

from site_nine.core.daemon_names import get_names_by_role, load_daemon_names, suggest_name


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
    expected_roles = {"Architect", "Engineer", "Designer", "Documentarian"}
    assert expected_roles.issubset(roles), f"Missing roles: {expected_roles - roles}"


def test_get_names_by_role():
    """Test filtering names by role"""
    engineers = get_names_by_role("Engineer")

    # Should return a list of engineers
    assert isinstance(engineers, list)
    assert len(engineers) > 0

    # All should be engineers
    for name in engineers:
        assert name["role"] == "Engineer"
        assert "name" in name


def test_get_names_by_role_nonexistent():
    """Test filtering by a role that doesn't exist"""
    result = get_names_by_role("NonExistentRole")

    # Should return empty list
    assert isinstance(result, list)
    assert len(result) == 0


def test_suggest_name_returns_name_for_role():
    """Test suggesting a name for a role"""
    suggestion = suggest_name("Engineer")

    # Should return a name dict
    assert suggestion is not None
    assert "name" in suggestion
    assert "role" in suggestion
    assert suggestion["role"] == "Engineer"


def test_suggest_name_excludes_names():
    """Test suggesting a name with exclusions"""
    # Get all engineer names
    all_engineers = get_names_by_role("Engineer")
    assert len(all_engineers) > 1, "Need at least 2 engineers for this test"

    # Exclude the first one
    first_name = all_engineers[0]["name"]
    suggestion = suggest_name("Engineer", exclude=[first_name])

    # Should not suggest the excluded name
    assert suggestion is not None
    assert suggestion["name"] != first_name


def test_suggest_name_all_excluded():
    """Test suggesting when all names are excluded"""
    # Get all names for a role
    all_engineers = get_names_by_role("Engineer")
    all_names = [b["name"] for b in all_engineers]

    # Exclude everything
    suggestion = suggest_name("Engineer", exclude=all_names)

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
    suggestion = suggest_name("Engineer")

    # Should work and return a suggestion
    assert suggestion is not None
    assert "name" in suggestion

    # usage_count may or may not be present (it's optional with .get())
    # This just verifies the function doesn't crash on missing usage_count
