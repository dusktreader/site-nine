# s9 Documentation

This directory contains user-facing documentation for the s9 project.

## Directory Structure

- **source/** - MkDocs source files for the main documentation site

## Documentation Organization

### Main Documentation (`source/`)
The primary user-facing documentation built with MkDocs. See `mkdocs.yaml` for the site structure.

**Note:** For persona/developer documentation, see `.opencode/` directory in the project root.

## Building the Documentation

```bash
# Install dependencies
uv sync

# Serve locally with live reload
make docs/serve

# Build static site
make docs/build
```

## Contributing

When updating user-facing documentation:
1. Edit files in `source/`
2. Test locally with `make docs/serve`
3. Commit changes following the project's commit guidelines

## Building the Documentation

```bash
# Install dependencies
uv sync

# Serve locally
make docs/serve

# Build static site
make docs/build
```

## Contributing

When adding new documentation:
1. User-facing docs go in `source/`
2. Planning and design docs go in `planning/`
3. Outdated but historically valuable docs go in `archive/`
