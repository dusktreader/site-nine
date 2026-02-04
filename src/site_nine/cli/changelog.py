"""Changelog generation commands"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
from loguru import logger
from rich.console import Console
from typerdrive import handle_errors

from site_nine.core.database import Database
from site_nine.core.paths import get_opencode_dir, validate_path_within_project

console = Console()


@handle_errors("Failed to generate changelog")
def changelog_command(
    since: str | None = typer.Option(None, "--since", help="Only include tasks closed since this date (YYYY-MM-DD)"),
    format: str = typer.Option("markdown", "--format", help="Output format: markdown or json"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Write to file instead of stdout"),
) -> None:
    """Generate changelog from completed tasks (typically used by: humans)

    Creates a chronological report of completed work, grouped by date,
    showing what changes were made to the system. Excludes aborted tasks
    and focuses on actual changes/solutions implemented rather than objectives.
    """
    try:
        opencode_dir = get_opencode_dir()
    except FileNotFoundError:
        console.print("[red]Error: .opencode directory not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    db_path = opencode_dir / "data" / "project.db"
    if not db_path.exists():
        console.print("[red]Error: project.db not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    db = Database(db_path)

    # Build query - only COMPLETE tasks (not ABORTED)
    query = """
        SELECT 
            id, 
            title, 
            status, 
            priority, 
            role, 
            category,
            current_mission_id,
            claimed_at,
            closed_at,
            actual_hours,
            file_path,
            objective,
            description,
            notes
        FROM tasks
        WHERE status = 'COMPLETE'
    """

    params: dict[str, Any] = {}
    if since:
        query += " AND date(closed_at) >= :since"
        params["since"] = since

    query += " ORDER BY closed_at DESC, id"

    tasks = db.execute_query(query, params)

    if not tasks:
        console.print("[yellow]No completed tasks found.[/yellow]")
        logger.info("No completed tasks for changelog")
        return

    # Generate output based on format
    if format == "json":
        output_text = _generate_changelog_json(tasks, opencode_dir)
    else:
        output_text = _generate_changelog_markdown(tasks, opencode_dir)

    # Write output
    if output:
        output.write_text(output_text)
        console.print(f"[green]✓[/green] Generated changelog: {output}")
        logger.info(f"Generated changelog to {output}")
    else:
        console.print(output_text)
        logger.info(f"Generated changelog with {len(tasks)} tasks")


def _generate_changelog_markdown(tasks: list[dict], opencode_dir: Path) -> str:
    """Format tasks as markdown changelog focused on changes made"""
    output = []
    output.append("# Changelog")
    output.append("")
    output.append("Generated from completed task records.")
    output.append("")
    output.append("---")
    output.append("")

    # Group by date (using closed_at date)
    tasks_by_date: dict[str, list[dict]] = {}
    for task in tasks:
        if task.get("closed_at"):
            # Handle both ISO format and space-separated format
            closed_at = task["closed_at"]
            if " " in closed_at:
                date = closed_at.split()[0]
            elif "T" in closed_at:
                date = closed_at.split("T")[0]
            else:
                date = closed_at
        else:
            date = "Unknown"

        if date not in tasks_by_date:
            tasks_by_date[date] = []
        tasks_by_date[date].append(task)

    # Output by date (most recent first)
    for date in sorted(tasks_by_date.keys(), reverse=True):
        output.append(f"## {date}")
        output.append("")

        for task in tasks_by_date[date]:
            task_file = _read_task_file(task, opencode_dir)

            output.append(f"### [{task['id']}] {task['title']}")
            output.append("")
            output.append(f"**Priority:** {task['priority']}  ")
            output.append(f"**Role:** {task['role']}  ")
            if task.get("category"):
                output.append(f"**Category:** {task['category']}  ")
            if task.get("current_mission_id"):
                output.append(f"**Mission:** {task['current_mission_id']}  ")
            if task.get("actual_hours"):
                output.append(f"**Time:** {task['actual_hours']} hours  ")

            output.append("")

            # Extract changes from task file
            if task_file:
                # Look for implementation steps, solutions, or changes sections
                sections = _extract_change_sections(task_file)

                if sections.get("implementation"):
                    output.append("**Changes:**")
                    output.append(sections["implementation"])
                    output.append("")

                if sections.get("files_changed"):
                    output.append("**Files Changed:**")
                    output.append(sections["files_changed"])
                    output.append("")

                if sections.get("testing"):
                    output.append("**Testing:**")
                    output.append(sections["testing"])
                    output.append("")
            else:
                # Fallback to database fields if no file exists
                if task.get("description"):
                    output.append("**Changes:**")
                    desc = task["description"]
                    if len(desc) > 500:
                        desc = desc[:500] + "..."
                    output.append(desc)
                    output.append("")

            if task.get("file_path"):
                output.append(f"*See full details: `{task['file_path']}`*")
                output.append("")

            output.append("---")
            output.append("")

    return "\n".join(output)


def _generate_changelog_json(tasks: list[dict], opencode_dir: Path) -> str:
    """Format tasks as JSON changelog"""
    output = []

    for task in tasks:
        task_file = _read_task_file(task, opencode_dir)
        sections = _extract_change_sections(task_file) if task_file else {}

        entry = {
            "id": task["id"],
            "title": task["title"],
            "closed_at": task.get("closed_at"),
            "priority": task["priority"],
            "role": task["role"],
            "category": task.get("category"),
            "mission": task.get("current_mission_id"),
            "hours": task.get("actual_hours"),
            "changes": sections.get("implementation") or task.get("description"),
            "files_changed": sections.get("files_changed"),
            "testing": sections.get("testing"),
            "file_path": task.get("file_path"),
        }
        output.append(entry)

    return json.dumps({"changelog": output}, indent=2)


def _read_task_file(task: dict, opencode_dir: Path) -> str | None:
    """Read task markdown file if it exists"""
    if not task.get("file_path"):
        return None

    # Handle file_path which may include .opencode prefix
    file_path_str = task["file_path"]
    if file_path_str.startswith(".opencode/"):
        file_path = Path(file_path_str)
    else:
        file_path = opencode_dir / file_path_str

    # Validate path to prevent directory traversal
    file_path = validate_path_within_project(file_path)

    if file_path.exists():
        return file_path.read_text()

    return None


def _extract_change_sections(content: str) -> dict[str, str]:
    """Extract relevant sections from task markdown file

    Focuses on implementation steps, files changed, and testing sections.
    Ignores objective and problem statement since we want actual changes.
    """
    sections = {}
    lines = content.split("\n")

    current_section = None
    section_content: list[str] = []

    for line in lines:
        # Check for section headers
        if line.startswith("## Implementation Steps"):
            if current_section and section_content:
                sections[current_section] = "\n".join(section_content).strip()
            current_section = "implementation"
            section_content = []
        elif line.startswith("## Files Changed"):
            if current_section and section_content:
                sections[current_section] = "\n".join(section_content).strip()
            current_section = "files_changed"
            section_content = []
        elif line.startswith("## Testing Performed") or line.startswith("## Testing"):
            if current_section and section_content:
                sections[current_section] = "\n".join(section_content).strip()
            current_section = "testing"
            section_content = []
        elif line.startswith("## "):
            # End of current section
            if current_section and section_content:
                sections[current_section] = "\n".join(section_content).strip()
            current_section = None
            section_content = []
        elif current_section:
            # Skip the header metadata section
            if not line.startswith("**"):
                section_content.append(line)

    # Add last section
    if current_section and section_content:
        sections[current_section] = "\n".join(section_content).strip()

    # Clean up sections - remove placeholder text
    for key in sections:
        content = sections[key]
        if "[" in content and "]" in content:
            # Contains placeholder like [description] or [file path]
            # Only remove if the entire section is just placeholders
            lines = [line.strip() for line in content.split("\n") if line.strip()]
            if all(line.startswith("[") or line.startswith("-") or not line for line in lines):
                sections[key] = ""

    # Remove empty sections
    sections = {k: v for k, v in sections.items() if v}

    return sections
