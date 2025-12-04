# Distribution Guide

This document explains how to distribute and install the WOF Explorer package.

## Package Status

✅ **Ready for Distribution**

- Package builds successfully
- All tests pass
- Examples validated
- Documentation complete
- Twine validation passes

## Installation Methods

### 1. Git Installation (Recommended)

```bash
pip install git+https://github.com/pattern-stack/geography-patterns.git#subdirectory=wof-explorer
```

### 2. Local Development

```bash
git clone https://github.com/pattern-stack/geography-patterns.git
cd geography-patterns/wof-explorer
pip install -e .
```

### 3. Built Wheel (Manual)

```bash
# After building locally
pip install dist/wof_explorer-0.3.0-py3-none-any.whl
```

## Building from Source

### Prerequisites

- Python 3.9+
- `build` and `twine` packages

### Build Steps

```bash
cd wof-explorer

# Install build tools
pip install build twine

# Build the package
python -m build

# Validate quality
twine check dist/*
```

### Build Outputs

- **Wheel**: `wof_explorer-0.3.0-py3-none-any.whl` (~98KB)
- **Source**: `wof_explorer-0.3.0.tar.gz` (~83KB)

## Current Distribution Strategy

### Phase 1: Git Distribution ✅
- Direct installation from GitHub
- Subdirectory installation support
- Development and production ready

### Phase 2: PyPI Publishing (Future)
- Upload to Python Package Index
- Simple `pip install wof-explorer`
- Automated releases via CI/CD

## Quality Assurance

### Validation Checklist

- [x] Package builds without errors
- [x] Both wheel and sdist created
- [x] Twine validation passes
- [x] All imports work correctly
- [x] Examples run without errors
- [x] Tests pass
- [x] Documentation complete

### Known Issues

**Build Warnings** (non-blocking):
- License format deprecation warnings (setuptools)
- These are cosmetic and don't affect functionality

## Usage After Installation

```python
# Install
pip install git+https://github.com/pattern-stack/geography-patterns.git#subdirectory=wof-explorer

# Use
from wof_explorer import WOFConnector, WOFSearchFilters
```

## CLI Tool

The package includes a command-line tool:

```bash
# After installation
wof-explore --help
```

## Dependency Information

### Core Dependencies (3)
- `aiosqlite>=0.19.0` - Async SQLite support
- `sqlalchemy>=2.0.0` - ORM and database abstraction
- `pydantic>=2.0.0` - Data validation and serialization

### Optional Dependencies
```bash
# Development tools
pip install wof-explorer[dev]

# Jupyter notebook support
pip install wof-explorer[notebook]
```

## Version Management

Current version: **0.3.0**

Version is defined in:
- `src/wof_explorer/__init__.py` (`__version__`)
- `pyproject.toml` (`version`)

## Future Distribution Plans

1. **Automated Testing**: CI/CD pipeline for quality assurance
2. **PyPI Publishing**: Official Python Package Index releases
3. **Docker Images**: Containerized distributions
4. **Conda Packages**: conda-forge distribution channel

## Support

For installation issues:
1. Check the [README](README.md) for basic setup
2. Review [examples/](examples/) for usage patterns
3. Open an issue on GitHub for problems