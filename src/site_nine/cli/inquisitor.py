"""Inquisitor commands — health checks, diagnostics, and repair.

Re-exports doctor_command as inquisitor_command for the new CLI naming.
"""

from site_nine.cli.doctor import doctor_command

# Expose under the new name; __main__.py registers this as "inquisitor"
inquisitor_command = doctor_command
