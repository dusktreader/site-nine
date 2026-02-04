"""Persona name management"""

import json
from pathlib import Path
from typing import Any


def load_personas() -> list[dict[str, Any]]:
    """Load persona names from embedded JSON"""
    data_file = Path(__file__).parent.parent / "data" / "personas.json"
    with open(data_file) as f:
        return json.load(f)


def get_personas_by_role(role: str) -> list[dict[str, Any]]:
    """Get persona names filtered by role"""
    all_personas = load_personas()
    return [p for p in all_personas if p["role"] == role]


def suggest_persona(role: str, exclude: list[str] | None = None) -> dict[str, Any] | None:
    """Suggest an unused or least-used persona for a role"""
    personas = get_personas_by_role(role)
    exclude = exclude or []

    # Filter out excluded
    available = [p for p in personas if p["name"] not in exclude]

    if not available:
        return None

    # Sort by mission count (ascending) - prefer unused personas
    available.sort(key=lambda p: p.get("mission_count", 0))
    return available[0]
