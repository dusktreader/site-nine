#!/usr/bin/env python3
"""
Migrate old session files to mission format.

Old format (sessions):
- Frontmatter: name, task_summary, status
- Title: "Session: [description]"
- Agent: [Name] (Role)

New format (missions):
- Frontmatter: persona, codename, mission_id, objective
- Title: "Mission: [codename]"
- Persona: [Name] (Role)
"""

import re
import sys
from pathlib import Path


def generate_codename(task_summary: str) -> str:
    """Generate a simple codename from task summary."""
    # Use the task_summary as a simple codename
    return task_summary.replace("_", "-")


def migrate_session_file(session_file: Path, missions_dir: Path, dry_run: bool = False) -> None:
    """Migrate a single session file to mission format."""
    content = session_file.read_text()

    # Extract frontmatter
    frontmatter_match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if not frontmatter_match:
        print(f"⚠️  Skipping {session_file.name} - no frontmatter found")
        return

    frontmatter_text = frontmatter_match.group(1)
    body = content[frontmatter_match.end() :]

    # Parse frontmatter
    frontmatter = {}
    for line in frontmatter_text.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            frontmatter[key.strip()] = value.strip()

    # Check if required fields exist
    if "name" not in frontmatter or "role" not in frontmatter:
        print(f"⚠️  Skipping {session_file.name} - missing name or role")
        return

    # Extract session filename parts: YYYY-MM-DD.HH:MM:SS.role.name.task-summary.md
    filename_parts = session_file.stem.split(".")
    if len(filename_parts) < 5:
        print(f"⚠️  Skipping {session_file.name} - unexpected filename format")
        return

    date_part = filename_parts[0]
    time_part = filename_parts[1]
    role = filename_parts[2]
    persona = filename_parts[3]
    task_summary = ".".join(filename_parts[4:])  # Rejoin any remaining parts

    # Generate codename from task_summary
    codename = generate_codename(task_summary)

    # Build new frontmatter
    new_frontmatter = {
        "date": frontmatter.get("date", date_part),
        "start_time": frontmatter.get("start_time", time_part),
        "end_time": frontmatter.get("end_time", ""),
        "role": frontmatter.get("role", role).capitalize(),
        "persona": persona,
        "codename": codename,
        "mission_id": "migrated",  # Placeholder since we don't have IDs for old sessions
        "objective": frontmatter.get("task_summary", task_summary).replace("_", " ").replace("-", " "),
    }

    # Build new frontmatter text
    new_frontmatter_text = "---\n"
    for key, value in new_frontmatter.items():
        new_frontmatter_text += f"{key}: {value}\n"
    new_frontmatter_text += "---\n"

    # Update body content
    # Replace "Session:" with "Mission:"
    body = re.sub(r"^# Session:", f"# Mission: {codename}", body, flags=re.MULTILINE)

    # Replace "Agent:" with "Persona:"
    body = re.sub(r"\*\*Agent:\*\*", "**Persona:**", body)

    # Replace "Session Started" with "Mission Started"
    body = body.replace("Session Started", "Mission Started")
    body = body.replace("Session Ended", "Mission Ended")
    body = body.replace("session file", "mission file")

    # Build new content
    new_content = new_frontmatter_text + "\n" + body

    # Generate new filename with codename
    new_filename = f"{date_part}.{time_part}.{role.lower()}.{persona}.{codename}.md"
    new_path = missions_dir / new_filename

    # Check if target already exists
    if new_path.exists():
        print(f"⚠️  Skipping {session_file.name} - target {new_filename} already exists")
        return

    # Write or preview
    if dry_run:
        print(f"📝 Would migrate: {session_file.name} -> {new_filename}")
    else:
        new_path.write_text(new_content)
        print(f"✅ Migrated: {session_file.name} -> {new_filename}")


def main():
    """Main migration script."""
    # Get project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent

    sessions_dir = project_root / ".opencode" / "work" / "sessions"
    missions_dir = project_root / ".opencode" / "work" / "missions"

    if not sessions_dir.exists():
        print(f"❌ Sessions directory not found: {sessions_dir}")
        sys.exit(1)

    if not missions_dir.exists():
        print(f"❌ Missions directory not found: {missions_dir}")
        sys.exit(1)

    # Get all session files (exclude README and TEMPLATE)
    session_files = [f for f in sessions_dir.glob("*.md") if f.name not in ("README.md", "TEMPLATE.md")]

    print(f"Found {len(session_files)} session files to migrate")
    print()

    # Check for dry-run flag
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    if dry_run:
        print("🔍 DRY RUN MODE - No files will be modified")
        print()

    # Migrate each file
    migrated_count = 0
    for session_file in sorted(session_files):
        try:
            migrate_session_file(session_file, missions_dir, dry_run)
            migrated_count += 1
        except Exception as e:
            print(f"❌ Error migrating {session_file.name}: {e}")

    print()
    print(f"✅ Migration complete: {migrated_count}/{len(session_files)} files processed")

    if not dry_run:
        print()
        print("Next steps:")
        print("1. Review migrated files in .opencode/work/missions/")
        print("2. If satisfied, remove old sessions directory:")
        print("   rm -rf .opencode/work/sessions/")


if __name__ == "__main__":
    main()
