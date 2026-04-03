"""
Logging configuration for site-nine OpenCode tool scripts.

Tool scripts run as subprocesses invoked by OpenCode's TypeScript wrappers
(via ``Bun.$`...uv run python3 <script>``). Only stdout is captured for the
JSON result -- anything written to stderr bleeds directly into the terminal
and corrupts the OpenCode TUI rendering.

Loguru's default configuration writes to stderr. This module replaces that
default handler with a file handler (via typerdrive's ``LoggingManager``)
so that log output goes to ``~/.local/state/site-nine/logs/app.log``
instead of the terminal.

Usage::

    from tool_logging import logger
"""

from loguru import logger
from typerdrive import LoggingManager, set_typerdrive_config

set_typerdrive_config(app_name="site-nine")
LoggingManager()

__all__ = ["logger"]
