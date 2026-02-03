#!/usr/bin/env python3
"""
Extract templates from CROL Troll .opencode and convert to Jinja2

This script:
1. Reads CROL Troll .opencode files
2. Identifies CROL-specific content
3. Converts to Jinja2 templates with variables
4. Saves to hyper-queue templates directory
"""

import re
from pathlib import Path

CROL_TROLL_PATH = Path.home() / "src/mhe/assess-crol-troll/.opencode"
TEMPLATES_OUTPUT = Path(__file__).parent.parent / "src/hq/templates/base"

# Patterns to replace with Jinja2 variables
REPLACEMENTS = [
    (r"Crol Troll", "{{ project_name }}"),
    (r"crol-troll", "{{ project_name_hyphen }}"),
    (r"crol_troll", "{{ project_name_underscore }}"),
    (r"MCP Server", "{{ project_type }}"),
    # Keep CROL references that are domain-specific in comments
]


def should_skip_file(filename: str) -> bool:
    """Check if file should be skipped (domain-specific)"""
    skip_patterns = [
        "MIGRATION_",
        "SERVICEREGISTRY_",
        "TESTING_SERVICE_REGISTRY",
        "database.md",  # Too domain-specific
        "knowledge-base.md",  # Too domain-specific
        "testing-gateway-mcp-relay.md",  # Too domain-specific
    ]
    return any(pattern in filename for pattern in skip_patterns)


def extract_file(source: Path, dest: Path, apply_templates: bool = True) -> None:
    """Extract and genericize a single file"""
    content = source.read_text()

    if apply_templates:
        # Apply replacements
        for pattern, replacement in REPLACEMENTS:
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)

    # Write with .jinja extension for markdown files
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.suffix == ".md":
        dest_file = dest.with_suffix(dest.suffix + ".jinja")
    elif dest.suffix == ".json":
        dest_file = dest.with_suffix(dest.suffix + ".jinja")
    else:
        dest_file = dest

    dest_file.write_text(content)
    print(f"Extracted: {source.name} -> {dest_file.relative_to(TEMPLATES_OUTPUT)}")


def main():
    """Extract all templates"""
    print(f"Extracting templates from {CROL_TROLL_PATH}")
    print(f"Output directory: {TEMPLATES_OUTPUT}\n")

    # Agent definitions
    print("Extracting agent definitions...")
    agents_dir = CROL_TROLL_PATH / "agents"
    for agent_file in agents_dir.glob("*.md"):
        extract_file(agent_file, TEMPLATES_OUTPUT / "agents" / agent_file.name)

    # Guides (selective - skip domain-specific ones)
    print("\nExtracting guides...")
    guides_dir = CROL_TROLL_PATH / "guides"
    for guide_file in guides_dir.glob("*.md"):
        if not should_skip_file(guide_file.name):
            extract_file(guide_file, TEMPLATES_OUTPUT / "guides" / guide_file.name)
        else:
            print(f"Skipped (domain-specific): {guide_file.name}")

    # Procedures (selective)
    print("\nExtracting procedures...")
    proc_dir = CROL_TROLL_PATH / "procedures"
    for proc_file in proc_dir.glob("*.md"):
        if not should_skip_file(proc_file.name):
            extract_file(proc_file, TEMPLATES_OUTPUT / "procedures" / proc_file.name)
        else:
            print(f"Skipped (domain-specific): {proc_file.name}")

    # README
    print("\nExtracting README...")
    extract_file(CROL_TROLL_PATH / "README.md", TEMPLATES_OUTPUT / "README.md")

    # opencode.json
    print("\nExtracting opencode.json...")
    extract_file(CROL_TROLL_PATH / "opencode.json", TEMPLATES_OUTPUT / "opencode.json")

    print("\n✓ Template extraction complete!")
    print(f"Templates saved to: {TEMPLATES_OUTPUT}")


if __name__ == "__main__":
    main()
