"""Health check, diagnostics, and repair commands

Backward-compatibility alias — all logic lives in site_nine.cli.inquisitor.
"""

from site_nine.cli.inquisitor import inquisitor_command

# Expose under the legacy name; __main__.py registers this as "doctor"
doctor_command = inquisitor_command
