from __future__ import annotations

from dataclasses import dataclass


@dataclass
class InitResult:
    """Result of project initialization."""

    opencode_dir: str
    static_count: int
    template_count: int
    persona_count: int
