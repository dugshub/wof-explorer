# Changelog

All notable changes to WOF Explorer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2024-09-20

### Changed
- **BREAKING**: Restructured as standalone pip-installable package
- **BREAKING**: Moved from flat structure to src-layout (`src/wof_explorer/`)
- **BREAKING**: Simplified public API to core classes only
- **BREAKING**: Reduced dependencies to essential trio (aiosqlite, sqlalchemy, pydantic)

### Added
- Explicit public API with `__all__` exports
- Package version attribute (`__version__ = "0.3.0"`)
- Comprehensive package metadata for PyPI compatibility
- CLI entry point for `wof-explore` command
- Professional examples directory with 4 usage patterns
- Complete package documentation (README, CHANGELOG, LICENSE)
- Development and notebook optional dependencies

### Removed
- FastAPI, uvicorn, and other non-core dependencies
- Internal models from public API exports
- Factory complexity from main interface

### Fixed
- Package build and installation process
- Import paths for src-layout structure
- Setuptools configuration for proper package discovery

## [0.2.0] - Previous Versions

### Features from Earlier Development
- Infrastructure Subsystem Pattern with swappable backends
- SQLite backend with comprehensive WOF data support
- Cursor-based navigation patterns for memory efficiency
- Hierarchical geographic queries (ancestors/descendants)
- Spatial queries with bounding box support
- Multiple export formats (GeoJSON, CSV, WKT)
- Two-phase exploration pattern (navigate → fetch)
- PlaceCollection for batch operations and analysis
- WOF database discovery and exploration tools

### Architecture Patterns
- Three-layer data model (Database → Internal → Public)
- Repository pattern for data access
- Clean separation of concerns
- Async/await throughout for performance

## Migration Guide

### From 0.2.x to 0.3.0

**Import Changes**:
```python
# Old (0.2.x)
from wof_explorer.factory import WOFConnector
from wof_explorer.models.filters import WOFSearchFilters

# New (0.3.0)
from wof_explorer import WOFConnector, WOFSearchFilters
```

**Removed Exports**:
- Internal models (WOFAncestor, WOFName, WOFHierarchy) no longer exported
- Factory functions (get_wof_connector, reset_connector) no longer public
- Base classes (WOFConnectorBase) no longer exported
- Explorer class no longer directly exported (access via connector.explorer)

**Installation**:
```bash
# Old - required cloning repository
git clone ...

# New - pip installable
pip install git+https://github.com/pattern-stack/geography-patterns.git#subdirectory=wof-explorer
```

## Upcoming Features

### [0.4.0] - Planned
- PostGIS backend support
- Enhanced spatial query capabilities
- Performance optimizations for large datasets
- Extended export format support

### [0.5.0] - Future
- Real-time data sync capabilities
- Advanced aggregation features
- Plugin architecture for custom backends
- Web UI for interactive exploration

## Compatibility

- **Python**: 3.9+
- **WhosOnFirst**: SQLite database format
- **Platforms**: Cross-platform (Windows, macOS, Linux)
- **Dependencies**: Minimal (3 core packages)