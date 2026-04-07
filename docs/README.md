# s9 Documentation

This directory contains user-facing documentation for the s9 project.

## Directory Structure

- **source/** - Zensical source files for the main documentation site

## Documentation Organization

### Main Documentation (`source/`)

The primary user-facing documentation built with [Zensical](https://zensical.org/). See `zensical.toml` for the site structure.

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
