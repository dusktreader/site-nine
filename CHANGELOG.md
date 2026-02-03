# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## v0.2.0 - 2026-02-02

Built out the site-nine project, a comprehensive Python-based framework for managing AI agent
workflows with specialized roles, task management, session tracking, and documentation generation.

Core Features:
- Multi-role agent system (administrator, architect, builder, designer, documentarian, inspector, operator, tester)
- SQLite-based task tracking with priority-based ID system
- Session management with handoff workflows between agents
- Jinja2 template system for .opencode configuration generation
- CLI commands for agent, task, config, and session management

Technical Implementation:
- Built with Typer for CLI, SQLAlchemy for database ORM
- Comprehensive test suite with pytest (13 test modules, 85% coverage threshold)
- CI/CD with GitHub Actions for tests, docs, and deployment
- MkDocs-based documentation with Material theme
- Migration scripts for schema updates and legacy data

Project Structure:
- src/s9/cli: Command-line interface modules
- src/s9/core: Configuration, database, paths, templates
- src/s9/tasks: Task management and ID generation
- src/s9/templates: Jinja2 templates for agent docs and workflows
- tests/: Comprehensive test coverage
- docs/: MkDocs documentation site

## v0.1.0 - 2026-01-30
- Generated project from template
