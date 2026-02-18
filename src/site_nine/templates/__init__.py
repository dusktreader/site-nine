"""
Template organization for site-nine.

This package contains two categories of templates:

- **scaffold/**: Files used during project initialization (`s9 init`)
  - **static/**: Copied as-is into the new `.opencode/` directory
    (commands, skills, generic guides, etc.)
  - **templates/**: Jinja2 templates rendered with project context
    (role docs, project-specific guides, etc.)

- **internal/**: Templates used at runtime by the application
  These templates are used internally by s9 commands during normal
  operation to generate files dynamically.
  Examples: mission files, task files, reports, etc.
"""
