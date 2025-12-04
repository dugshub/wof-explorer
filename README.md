# WOF Explorer

[![Python 3.9-3.13](https://img.shields.io/badge/python-3.9--3.13-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Python library for exploring [WhosOnFirst](https://whosonfirst.org/) geographic data with cursor-based navigation and hierarchical queries.

## Features

- **Cursor-based navigation** for memory-efficient exploration of large datasets
- **Hierarchical traversal** (country → region → city → neighborhood)
- **Spatial queries** with bounding box support
- **Multiple export formats**: GeoJSON, CSV, WKT
- **Async-first API** with clean, intuitive interface

## Installation

```bash
pip install wof-explorer
```

For development:

```bash
git clone https://github.com/dugspi/wof-explorer.git
cd wof-explorer
pip install -e ".[dev]"
```

## CLI Tool

The package includes a command-line tool for downloading WhosOnFirst databases:

```bash
# Download US and Canada databases (downloads, extracts, and merges automatically)
wof-explore download us,ca

# Download multiple countries
wof-explore download us ca mx gb

# Specify output directory
wof-explore download us,ca -o ./data

# Keep individual database files after merge
wof-explore download us,ca --keep

# List available country codes
wof-explore countries

# Validate installation
wof-explore validate
```

The downloader fetches compressed databases from [geocode.earth](https://data.geocode.earth/wof/dist/sqlite/), extracts them, and merges multiple countries into a single `whosonfirst-combined.db` file.

## Quick Start

```python
import asyncio
from wof_explorer import WOFConnector, WOFSearchFilters, PlaceCollection

async def main():
    connector = WOFConnector('whosonfirst-data-admin-us-latest.db')
    await connector.connect()

    # Search for neighborhoods in Chicago
    cursor = await connector.search(
        WOFSearchFilters(
            placetype="neighbourhood",
            ancestor_name="Chicago",
            is_current=True
        )
    )

    # Fetch results with geometry
    places = await cursor.fetch_all(include_geometry=True)
    print(f"Found {len(places)} neighborhoods")

    # Export to GeoJSON
    collection = PlaceCollection(places=places)
    geojson = collection.to_geojson_string()

    await connector.disconnect()

asyncio.run(main())
```

## Database Setup

WOF Explorer works with WhosOnFirst SQLite databases. Download one to get started:

```bash
# US administrative data (~1.5GB)
curl -O https://data.whosonfirst.org/sqlite/whosonfirst-data-admin-us-latest.db

# Or choose a smaller region
curl -O https://data.whosonfirst.org/sqlite/whosonfirst-data-admin-ca-latest.db  # Canada
curl -O https://data.whosonfirst.org/sqlite/whosonfirst-data-admin-gb-latest.db  # Great Britain
```

See [data.whosonfirst.org/sqlite](https://data.whosonfirst.org/sqlite/) for all available databases.

## Core Concepts

### Two-Phase Exploration

WOF Explorer uses a two-phase pattern optimized for large datasets:

**Phase 1: Navigate (lightweight)**
```python
# Search returns a cursor with minimal data loaded
cursor = await connector.search(WOFSearchFilters(placetype="locality"))
print(f"Found {cursor.total_count} cities")

# Iterate without loading geometry
for place in cursor.places:
    print(f"{place.name} ({place.id})")
```

**Phase 2: Fetch (selective)**
```python
# Only fetch full details for what you need
places = await cursor.fetch_all(include_geometry=True)
```

### Hierarchical Navigation

```python
from wof_explorer import WOFConnector, WOFSearchFilters, WOFHierarchyCursor

async def explore_hierarchy():
    connector = WOFConnector('database.db')
    await connector.connect()

    # Find San Francisco
    cursor = await connector.search(WOFSearchFilters(name="San Francisco"))
    sf = cursor.places[0]

    # Navigate the hierarchy
    hierarchy = WOFHierarchyCursor(sf, connector)

    # Get ancestors (city → county → state → country)
    ancestors = await hierarchy.fetch_ancestors()

    # Get descendants (neighborhoods within SF)
    neighborhoods = await hierarchy.fetch_descendants(
        filters=WOFSearchFilters(placetype="neighbourhood")
    )

    await connector.disconnect()
```

### Spatial Queries

```python
from wof_explorer.models import BBox

# Search within a bounding box
bbox = BBox(min_lat=37.7, max_lat=37.8, min_lon=-122.5, max_lon=-122.4)
cursor = await connector.search(
    WOFSearchFilters(placetype="locality", bbox=bbox)
)
```

### Export Formats

```python
collection = PlaceCollection(places=places)

# GeoJSON (for mapping tools)
geojson = collection.to_geojson_string()

# CSV (for spreadsheets)
csv_data = collection.to_csv_string()

# WKT (for GIS software)
wkt_data = collection.to_wkt_string()
```

## API Reference

### Core Classes

| Class | Description |
|-------|-------------|
| `WOFConnector` | Database connection and query interface |
| `WOFSearchFilters` | Query builder for search operations |
| `PlaceCollection` | Container for batch operations and export |
| `WOFSearchCursor` | Iterate search results efficiently |
| `WOFHierarchyCursor` | Navigate geographic hierarchies |
| `WOFBatchCursor` | Process multiple places by ID |

### Search Filters

```python
WOFSearchFilters(
    name="Chicago",              # Exact name match
    name_contains="New",         # Partial name match
    placetype="locality",        # Place type filter
    placetype=["locality", "neighbourhood"],  # Multiple types (OR)
    ancestor_name="California",  # Within ancestor hierarchy
    country="US",                # Country code
    is_current=True,             # Only current records
    bbox=BBox(...),              # Bounding box
    limit=100                    # Result limit
)
```

## Examples

See the [examples/](examples/) directory:

- [basic_usage.py](examples/basic_usage.py) - Getting started
- [hierarchical_search.py](examples/hierarchical_search.py) - Navigate hierarchies
- [spatial_queries.py](examples/spatial_queries.py) - Bounding box searches
- [batch_processing.py](examples/batch_processing.py) - Handle large datasets

## Requirements

- Python 3.9+
- SQLite database with WhosOnFirst data

## License

MIT License - see [LICENSE](LICENSE) for details.

## Links

- [WhosOnFirst](https://whosonfirst.org/) - The underlying geographic data project
- [WhosOnFirst Data](https://data.whosonfirst.org/) - Download databases
- [GitHub Issues](https://github.com/dugspi/wof-explorer/issues) - Report bugs or request features
