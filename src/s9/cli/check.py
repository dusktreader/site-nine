"""Infrastructure health checks and validation commands"""

from __future__ import annotations

import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typerdrive import handle_errors

from s9.core.database import Database
from s9.core.paths import get_opencode_dir

console = Console()


@handle_errors("Failed to run infrastructure checks")
def check_command(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
) -> None:
    """Run infrastructure health checks

    Performs checks on the .opencode directory structure:
    - Database integrity (SQLite PRAGMA integrity_check)
    - Session file existence validation
    - Gitignore pattern validation
    - Database file existence
    - Backup file detection
    """
    try:
        opencode_dir = get_opencode_dir()
    except FileNotFoundError:
        console.print("[red]Error: .opencode directory not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    db_path = opencode_dir / "data" / "project.db"

    console.print()
    console.print("🔍 [bold cyan]Running infrastructure checks...[/bold cyan]")
    console.print()

    checks_passed = 0
    checks_failed = 0
    checks_warning = 0

    # Check 1: Database File Existence
    console.print("[bold]1. Checking database file existence...[/bold]")
    if not db_path.exists():
        console.print(f"  [red]✗[/red] Database file not found: {db_path}")
        console.print("  [cyan]💡 Run 's9 init' to initialize the project[/cyan]")
        checks_failed += 1
        console.print()
        console.print("[bold red]❌ Cannot proceed without database file[/bold red]")
        raise typer.Exit(1)
    else:
        console.print(f"  [green]✓[/green] Database file exists: {db_path}")
        checks_passed += 1
    console.print()

    # Check 2: Database Integrity
    console.print("[bold]2. Checking database integrity...[/bold]")
    try:
        result = subprocess.run(
            ["sqlite3", str(db_path), "PRAGMA integrity_check;"], capture_output=True, text=True, check=True
        )
        if result.stdout.strip() == "ok":
            console.print("  [green]✓[/green] Database integrity check passed")
            checks_passed += 1
        else:
            console.print(f"  [red]✗[/red] Database integrity check failed: {result.stdout.strip()}")
            console.print("  [cyan]💡 You may need to restore from backup[/cyan]")
            checks_failed += 1
    except subprocess.CalledProcessError as e:
        console.print(f"  [red]✗[/red] Failed to run integrity check: {e}")
        console.print("  [yellow]⚠[/yellow]  Make sure sqlite3 is installed")
        checks_failed += 1
    except FileNotFoundError:
        console.print("  [yellow]⚠[/yellow]  sqlite3 command not found - skipping integrity check")
        console.print("  [cyan]💡 Install sqlite3 to enable this check[/cyan]")
        checks_warning += 1
    console.print()

    # Check 3: Session File Validation
    console.print("[bold]3. Checking session files...[/bold]")
    db = Database(db_path)
    all_sessions = db.execute_query("SELECT id, name, session_file FROM agents WHERE session_file IS NOT NULL")

    missing_files = []
    for session in all_sessions:
        if session.get("session_file"):
            # Handle both absolute and relative paths
            session_file = session["session_file"]
            if session_file.startswith(".opencode/"):
                # Relative path from project root
                session_path = Path(session_file)
            else:
                # Relative path from .opencode dir
                session_path = opencode_dir / session_file

            if not session_path.exists():
                missing_files.append({"id": session["id"], "name": session["name"], "file": session_file})
                if verbose:
                    console.print(
                        f"  [yellow]⚠[/yellow] Agent #{session['id']} ({session['name']}): session file not found: {session_file}"
                    )

    if missing_files:
        console.print(f"  [yellow]⚠[/yellow]  Found {len(missing_files)} missing session files (non-critical)")
        console.print("  [dim]Note: Session files are not critical. Database maintains session records.[/dim]")
        checks_warning += 1
    else:
        console.print(f"  [green]✓[/green] All {len(all_sessions)} session files exist")
        checks_passed += 1
    console.print()

    # Check 4: Gitignore Pattern Validation
    console.print("[bold]4. Checking .gitignore patterns...[/bold]")

    # Find .gitignore in project root (parent of .opencode)
    gitignore_path = opencode_dir.parent / ".gitignore"

    if not gitignore_path.exists():
        console.print("  [yellow]⚠[/yellow]  No .gitignore file found")
        console.print("  [cyan]💡 Consider creating a .gitignore to avoid committing database files[/cyan]")
        checks_warning += 1
    else:
        gitignore_content = gitignore_path.read_text()

        # Recommended patterns from docs
        recommended_patterns = [".opencode/data/*.db", ".opencode/data/*.db-journal", ".opencode/data/*.db-wal"]

        missing_patterns = []
        for pattern in recommended_patterns:
            if pattern not in gitignore_content:
                missing_patterns.append(pattern)
                if verbose:
                    console.print(f"  [yellow]⚠[/yellow] Missing recommended pattern: {pattern}")

        if missing_patterns:
            console.print(f"  [yellow]⚠[/yellow]  Missing {len(missing_patterns)} recommended .gitignore patterns")
            console.print("  [cyan]💡 Add these patterns to avoid committing database files:[/cyan]")
            for pattern in missing_patterns:
                console.print(f"      {pattern}")
            checks_warning += 1
        else:
            console.print(f"  [green]✓[/green] All recommended .gitignore patterns present")
            checks_passed += 1
    console.print()

    # Check 5: Backup File Detection
    console.print("[bold]5. Checking for backup files...[/bold]")

    backup_dir = opencode_dir / "data"
    backup_patterns = ["*.db.backup", "*.tar.gz", "*.zip"]

    backups_found = []
    for pattern in backup_patterns:
        backups_found.extend(backup_dir.glob(pattern))

    if backups_found:
        console.print(f"  [green]✓[/green] Found {len(backups_found)} backup file(s)")
        if verbose:
            for backup in backups_found:
                console.print(f"      {backup.name}")
        checks_passed += 1
    else:
        console.print("  [yellow]⚠[/yellow]  No backup files found")
        console.print("  [cyan]💡 Consider creating regular backups of your database[/cyan]")
        checks_warning += 1
    console.print()

    # Check 6: SQLite Temp Files
    console.print("[bold]6. Checking for SQLite temporary files...[/bold]")

    journal_file = db_path.parent / f"{db_path.name}-journal"
    wal_file = db_path.parent / f"{db_path.name}-wal"
    shm_file = db_path.parent / f"{db_path.name}-shm"

    temp_files = []
    if journal_file.exists():
        temp_files.append(journal_file.name)
    if wal_file.exists():
        temp_files.append(wal_file.name)
    if shm_file.exists():
        temp_files.append(shm_file.name)

    if temp_files:
        console.print(f"  [yellow]⚠[/yellow]  Found SQLite temporary files: {', '.join(temp_files)}")
        console.print("  [dim]Note: This may indicate active transactions or improper shutdown[/dim]")
        if verbose:
            for temp_file in temp_files:
                console.print(f"      {temp_file}")
        checks_warning += 1
    else:
        console.print("  [green]✓[/green] No SQLite temporary files present")
        checks_passed += 1
    console.print()

    # Summary
    console.print("═" * 70)

    total_checks = checks_passed + checks_failed + checks_warning

    # Create summary table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("[green]✓ Passed[/green]", f"{checks_passed}/{total_checks}")
    table.add_row("[yellow]⚠ Warnings[/yellow]", f"{checks_warning}/{total_checks}")
    table.add_row("[red]✗ Failed[/red]", f"{checks_failed}/{total_checks}")

    console.print(table)
    console.print()

    if checks_failed == 0 and checks_warning == 0:
        console.print(Panel("[bold green]✅ All infrastructure checks passed![/bold green]", border_style="green"))
    elif checks_failed == 0:
        console.print(
            Panel(
                f"[bold yellow]⚠ All checks passed with {checks_warning} warning(s)[/bold yellow]\n"
                "[dim]Review warnings above for recommended improvements[/dim]",
                border_style="yellow",
            )
        )
    else:
        console.print(
            Panel(
                f"[bold red]❌ {checks_failed} check(s) failed[/bold red]\n"
                "[dim]Review errors above and take corrective action[/dim]",
                border_style="red",
            )
        )
        raise typer.Exit(1)

    console.print()
