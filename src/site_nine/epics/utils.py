"""Utility functions for epic rendering"""


def generate_progress_bar(percent: int, width: int = 30) -> str:
    """Generate a text-based progress bar.

    Args:
        percent: Completion percentage (0-100)
        width: Character width of the bar

    Returns:
        Formatted progress bar string like "[██████░░░░░░░░░░░░░░░░░░░░░░░░] 20%"
    """
    filled = int(width * percent / 100)
    empty = width - filled
    return f"[{'█' * filled}{'░' * empty}] {percent}%"
