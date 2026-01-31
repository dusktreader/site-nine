"""Daemon name management"""

import json
from pathlib import Path
from typing import Any


def load_daemon_names() -> list[dict[str, Any]]:
    """Load daemon names from embedded JSON"""
    data_file = Path(__file__).parent.parent / "data" / "daemon_names.json"
    with open(data_file) as f:
        return json.load(f)


def get_names_by_role(role: str) -> list[dict[str, Any]]:
    """Get daemon names filtered by role"""
    all_names = load_daemon_names()
    return [n for n in all_names if n["role"] == role]


def suggest_name(role: str, exclude: list[str] | None = None) -> dict[str, Any] | None:
    """Suggest an unused or least-used name for a role"""
    names = get_names_by_role(role)
    exclude = exclude or []

    # Filter out excluded
    available = [n for n in names if n["name"] not in exclude]

    if not available:
        return None

    # Sort by usage count (ascending) - prefer unused names
    available.sort(key=lambda n: n.get("usage_count", 0))
    return available[0]
