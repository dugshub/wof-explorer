# WOF Connector Examples & Best Practices

## Table of Contents
1. [Basic Usage](#basic-usage)
2. [Search Patterns](#search-patterns)
3. [Hierarchical Navigation](#hierarchical-navigation)
4. [Data Export](#data-export)
5. [Analysis & Summaries](#analysis--summaries)
6. [Performance Optimization](#performance-optimization)
7. [Error Handling](#error-handling)
8. [Async Patterns](#async-patterns)

## Basic Usage

### Simple Connection and Search

```python
import asyncio
from src import WOFConnector
from src.filters import WOFSearchFilters

async def find_city():
    # Always use context manager or try/finally for cleanup
    connector = WOFConnector("path/to/database.db")

    try:
        await connector.connect()

        # Simple search
        cursor = await connector.search(
            WOFSearchFilters(
                name="Toronto",
                placetype="locality"
            )
        )

        if cursor.has_results:
            city = await cursor.fetch_one()
            print(f"Found: {city.name} (ID: {city.id})")

    finally:
        await connector.disconnect()

asyncio.run(find_city())
```

### Using Context Manager (Recommended)

```python
import asyncio
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_connector(db_path: str):
    """Context manager for safe connection handling"""
    connector = WOFConnector(db_path)
    await connector.connect()
    try:
        yield connector
    finally:
        await connector.disconnect()

async def main():
    async with get_connector("database.db") as connector:
        # Use connector here
        cursor = await connector.search(WOFSearchFilters(placetype="country"))
        countries = await cursor.fetch_all()

asyncio.run(main())
```

## Search Patterns

### Multi-Value Searches (OR Logic)

```python
# Find neighborhoods in multiple cities
cursor = await connector.search(
    WOFSearchFilters(
        placetype=["neighbourhood", "borough", "macrohood"],
        ancestor_name=["Chicago", "New York", "Los Angeles"],
        is_current=True
    )
)

places = await cursor.fetch_all()
print(f"Found {len(places.places)} neighborhoods")
```

### Hierarchical Searches

```python
# Find all places in California
cursor = await connector.search(
    WOFSearchFilters(
        ancestor_name="California",  # Searches entire ancestry
        placetype=["county", "locality"],
        is_current=True
    )
)

# Find only direct children of California
cursor = await connector.search(
    WOFSearchFilters(
        parent_name="California",  # Only immediate children
        placetype="county"
    )
)
```

### Spatial Searches

```python
from app.atoms.connectors.wof.models import BBox, Point

# Bounding box search (e.g., downtown area)
cursor = await connector.search(
    WOFSearchFilters(
        bbox=BBox(
            min_lat=43.640,
            max_lat=43.660,
            min_lon=-79.390,
            max_lon=-79.370
        ),
        placetype="venue"
    )
)

# Proximity search (5km radius)
cursor = await connector.search(
    WOFSearchFilters(
        near=Point(lat=43.651070, lon=-79.347015),
        radius_km=5,
        placetype=["neighbourhood", "locality"]
    )
)

# Only places with polygon boundaries
cursor = await connector.search(
    WOFSearchFilters(
        placetype="neighbourhood",
        exclude_point_geoms=True  # Excludes point-only places
    )
)
```

### Filter → Fetch Geometries → Write (Recommended)

Use lightweight filtering first, fetch only what you need with geometry, and finally write to GeoJSON.

```python
from pathlib import Path
from wof_explorer.factory import get_wof_connector
from wof_explorer.models.filters import WOFSearchFilters

connector = get_wof_connector()
await connector.connect()

cursor = await connector.search(WOFSearchFilters(
    placetype="locality",
    country="US",
    is_current=True,
    limit=200,
))

collection = await cursor.fetch_geometries()
Path("output").mkdir(parents=True, exist_ok=True)
Path("output/us_localities_subset.geojson").write_text(
    collection.to_geojson_string(indent=2, use_polygons=True, require_geometry=False),
    encoding="utf-8",
)

await connector.disconnect()
```

### Quick Explore (Counties, Cities, Neighborhoods)

```python
from wof_explorer.factory import get_wof_connector
from wof_explorer.processing.quick_explore import quick_explore, DEFAULT_FOCUS_CITIES

connector = get_wof_connector()
await connector.connect()

selections = await quick_explore(connector, focus_cities=DEFAULT_FOCUS_CITIES)
print({k: len(v) for k, v in selections.items()})

geojson = selections["neighborhoods"].to_geojson_string(indent=2)
await connector.disconnect()
```

### Click Under Point (Point-In-Polygon)

```python
from wof_explorer.processing.spatial import query_under_point
from wof_explorer.types import PlaceType

under = await query_under_point(
    connector,
    lat=41.881832, lon=-87.623177,
    placetypes=[PlaceType.MICROHOOD, PlaceType.NEIGHBOURHOOD, PlaceType.LOCALITY, PlaceType.COUNTY],
    country="US",
    radius_km=5.0,
)

under_geojson = under.to_geojson_string(indent=2)
```

### Name Searches

```python
# Exact name match
cursor = await connector.search(
    WOFSearchFilters(
        name="Downtown",
        name_exact=True
    )
)

# Partial name match (contains)
cursor = await connector.search(
    WOFSearchFilters(
        name_contains="Park",
        placetype="neighbourhood"
    )
)

# Search in specific language
cursor = await connector.search(
    WOFSearchFilters(
        name="París",
        name_language="spa",  # Spanish
        placetype="locality"
    )
)
```

## Hierarchical Navigation

### Building a Place Tree

```python
async def build_place_tree(place_id: int, connector: WOFConnector):
    """Build complete hierarchy for a place"""

    place = await connector.get_place(place_id)
    if not place:
        return None

    # Get ancestors (from root to parent)
    ancestors = await connector.get_ancestors(place_id)

    # Get descendants
    descendants = await connector.get_descendants(place_id)

    return {
        "place": place,
        "ancestors": ancestors,
        "descendants": descendants,
        "hierarchy_depth": len(ancestors),
        "descendant_count": len(descendants)
    }

# Usage
tree = await build_place_tree(85940195, connector)  # Chicago
print(f"Chicago has {tree['descendant_count']} descendant places")
```

### Finding All Cities in a State

```python
async def get_cities_in_state(state_name: str, connector: WOFConnector):
    """Get all cities within a state"""

    # First find the state
    cursor = await connector.search(
        WOFSearchFilters(
            name=state_name,
            placetype="region",
            country="US"
        )
    )

    if not cursor.has_results:
        return []

    state = await cursor.fetch_one()

    # Get all localities within the state
    cursor = await connector.search(
        WOFSearchFilters(
            ancestor_id=state.id,
            placetype="locality",
            is_current=True
        )
    )

    cities = await cursor.fetch_all()
    return cities.places

# Usage
cities = await get_cities_in_state("Illinois", connector)
print(f"Found {len(cities)} cities in Illinois")
```

## Data Export

### Export to GeoJSON

```python
# Export neighborhoods with full geometry
cursor = await connector.search(
    WOFSearchFilters(
        placetype="neighbourhood",
        ancestor_name="San Francisco",
        exclude_point_geoms=True
    )
)

places = await cursor.fetch_all(include_geometry=True)

# Save with polygon boundaries
places.save_geojson(
    "sf_neighborhoods.geojson",
    use_polygons=True,
    properties=["name", "placetype", "population"]
)

# Or get GeoJSON dict for further processing
geojson = places.to_geojson(use_polygons=True)
print(f"Exported {len(geojson['features'])} features")
```

### Export to CSV

```python
# Export places to CSV for analysis
cursor = await connector.search(
    WOFSearchFilters(
        placetype="county",
        ancestor_name="California"
    )
)

places = await cursor.fetch_all()
places.save_csv("california_counties.csv")

# Or work with DataFrame
import pandas as pd
rows = places.to_csv_rows()
df = pd.DataFrame(rows)
print(df.head())
```

### Export to WKT for GIS

```python
# Export with WKT geometry for PostGIS/QGIS
places = await cursor.fetch_all(include_geometry=True)
wkt_data = places.to_wkt_list()

# Use with GeoPandas
import geopandas as gpd
gdf = gpd.GeoDataFrame(wkt_data)
gdf.to_file("places.shp")
```

## Analysis & Summaries

### Intelligent Summary with Grouping

```python
# Search across multiple cities
cursor = await connector.search(
    WOFSearchFilters(
        placetype="neighbourhood",
        ancestor_name=["Chicago", "New York", "Los Angeles", "Houston"],
        exclude_point_geoms=True
    )
)

places = await cursor.fetch_all()

# Get basic summary (fast)
summary = places.get_summary(enrich_ancestors=False)
print(f"Total neighborhoods: {summary['total_count']}")
print(f"Coverage: {summary['coverage']}")

# Enhanced summary with city grouping (slower but more detailed)
await places.enrich_with_ancestors(connector)
summary = places.get_summary()

# Analyze distribution
for city, data in summary['by_ancestor'].items():
    pct = (data['count'] / summary['total_count']) * 100
    print(f"{city}: {data['count']} ({pct:.1f}%)")
```

### Coverage Analysis

```python
# Check data completeness
cursor = await connector.search(
    WOFSearchFilters(
        placetype=["neighbourhood", "locality", "county"],
        ancestor_name=["California", "Nevada", "Oregon"],
        is_current=True
    )
)

places = await cursor.fetch_all()
summary = places.get_summary(enrich_ancestors=False)

# Check what was found vs requested
coverage = summary['coverage']
print(f"Requested states: {coverage['ancestors_query']}")
print(f"Requested types: {coverage['placetypes_requested']}")
print(f"Found types: {coverage['placetypes_found']}")
if 'placetypes_missing' in coverage:
    print(f"Missing types: {coverage['placetypes_missing']}")
```

### Custom Analysis

```python
async def analyze_place_distribution(connector: WOFConnector):
    """Analyze distribution of place types"""

    # Get database summary
    explorer = connector.explorer
    summary = await explorer.database_summary()

    print("Database Overview:")
    print(f"Total places: {summary['total_places']:,}")
    print(f"Countries: {summary['total_countries']}")

    print("\nTop place types:")
    for ptype, count in summary['placetype_counts'].items()[:10]:
        print(f"  {ptype}: {count:,}")

    # Find cities with best coverage
    cities = await explorer.top_cities_by_coverage(limit=10)
    print("\nCities with most neighborhoods:")
    for city in cities:
        print(f"  {city['name']}: {city['neighbourhood_count']} neighborhoods")
```

## Performance Optimization

### Batch Processing Large Datasets

```python
async def process_large_dataset(connector: WOFConnector):
    """Process large dataset efficiently"""

    # Don't fetch all at once for huge datasets
    cursor = await connector.search(
        WOFSearchFilters(
            placetype="venue",
            country="US"
        )
    )

    print(f"Processing {cursor.total_count} venues...")

    # Process in batches
    batch_size = 1000
    processed = 0

    async for place in cursor:  # Async iteration
        # Process each place
        await process_venue(place)

        processed += 1
        if processed % batch_size == 0:
            print(f"Processed {processed}/{cursor.total_count}")
```

### Parallel Processing

```python
import asyncio

async def fetch_place_details(place_id: int, connector: WOFConnector):
    """Fetch details for a single place"""
    place = await connector.get_place(place_id, include_geometry=True)
    ancestors = await connector.get_ancestors(place_id)
    return {"place": place, "ancestors": ancestors}

async def fetch_many_places(place_ids: List[int], connector: WOFConnector):
    """Fetch details for multiple places in parallel"""

    # Create tasks for parallel execution
    tasks = [
        fetch_place_details(place_id, connector)
        for place_id in place_ids
    ]

    # Execute in parallel
    results = await asyncio.gather(*tasks)
    return results

# Usage
place_ids = [85940195, 85633793, 85688697]
details = await fetch_many_places(place_ids, connector)
```

### Geometry Optimization

```python
# Only fetch geometry when needed
cursor = await connector.search(filters)

# First pass: analyze without geometry (fast)
places = await cursor.fetch_all(include_geometry=False)
interesting_ids = [
    p.id for p in places.places
    if p.population and p.population > 100000
]

# Second pass: fetch geometry only for interesting places
detailed = await connector.get_places(interesting_ids, include_geometry=True)
```

## Error Handling

### Robust Connection Handling

```python
import logging
from typing import Optional

logger = logging.getLogger(__name__)

async def safe_search(
    connector: WOFConnector,
    filters: WOFSearchFilters,
    max_retries: int = 3
) -> Optional[PlaceCollection]:
    """Search with retry logic"""

    for attempt in range(max_retries):
        try:
            cursor = await connector.search(filters)
            return await cursor.fetch_all()

        except ConnectionError as e:
            logger.warning(f"Connection error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                await connector.disconnect()
                await connector.connect()
            else:
                logger.error("Max retries exceeded")
                raise

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise

    return None
```

### Validation and Fallbacks

```python
async def get_place_safely(
    place_id: int,
    connector: WOFConnector
) -> Optional[Dict[str, Any]]:
    """Get place with validation and fallbacks"""

    # Validate input
    if not isinstance(place_id, int) or place_id <= 0:
        logger.error(f"Invalid place_id: {place_id}")
        return None

    try:
        # Try to get with geometry
        place = await connector.get_place(place_id, include_geometry=True)

        if not place:
            logger.warning(f"Place {place_id} not found")
            return None

        # Validate critical fields
        if not place.name or not place.placetype:
            logger.warning(f"Place {place_id} missing critical data")

        return place.dict()

    except Exception as e:
        logger.error(f"Error fetching place {place_id}: {e}")

        # Try without geometry as fallback
        try:
            place = await connector.get_place(place_id, include_geometry=False)
            return place.dict() if place else None
        except:
            return None
```

## Async Patterns

### Running in Jupyter Notebooks

```python
# In Jupyter, you're already in an async context
connector = WOFConnector("database.db")
await connector.connect()

cursor = await connector.search(WOFSearchFilters(placetype="country"))
countries = await cursor.fetch_all()
```

### Running in Scripts

```python
import asyncio

async def main():
    connector = WOFConnector("database.db")
    await connector.connect()

    try:
        # Your async code here
        cursor = await connector.search(filters)
        # ...
    finally:
        await connector.disconnect()

# Python 3.7+
asyncio.run(main())

# Or for more control
loop = asyncio.get_event_loop()
try:
    loop.run_until_complete(main())
finally:
    loop.close()
```

### Integration with FastAPI

```python
from fastapi import FastAPI, Depends
from typing import List

app = FastAPI()

# Create connector on startup
@app.on_event("startup")
async def startup():
    app.state.connector = WOFConnector("database.db")
    await app.state.connector.connect()

@app.on_event("shutdown")
async def shutdown():
    await app.state.connector.disconnect()

# Dependency to get connector
async def get_connector():
    return app.state.connector

@app.get("/places/search")
async def search_places(
    placetype: str,
    country: str = "US",
    limit: int = 100,
    connector: WOFConnector = Depends(get_connector)
):
    cursor = await connector.search(
        WOFSearchFilters(
            placetype=placetype,
            country=country,
            limit=limit
        )
    )
    places = await cursor.fetch_all()
    return places.to_geojson()
```

### Sync Wrapper (If Needed)

```python
import asyncio
from typing import Optional

class SyncWOFConnector:
    """Synchronous wrapper for WOFConnector"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._connector = None
        self._loop = None

    def connect(self):
        """Synchronous connect"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._connector = WOFConnector(self.db_path)
        self._loop.run_until_complete(self._connector.connect())

    def search(self, filters: WOFSearchFilters) -> PlaceCollection:
        """Synchronous search"""
        cursor = self._loop.run_until_complete(
            self._connector.search(filters)
        )
        return self._loop.run_until_complete(
            cursor.fetch_all()
        )

    def disconnect(self):
        """Synchronous disconnect"""
        if self._loop and self._connector:
            self._loop.run_until_complete(self._connector.disconnect())
            self._loop.close()

# Usage (blocking)
connector = SyncWOFConnector("database.db")
connector.connect()
places = connector.search(WOFSearchFilters(placetype="country"))
connector.disconnect()
```

## Best Practices Summary

1. **Always disconnect**: Use try/finally or context managers
2. **Filter at database level**: Don't filter in Python when you can filter in the query
3. **Fetch geometry selectively**: Geometry data is large; only fetch when needed
4. **Use batch operations**: Process large datasets in chunks
5. **Cache when appropriate**: Ancestors and names don't change often
6. **Handle errors gracefully**: Network and database operations can fail
7. **Use type hints**: The connector is fully typed for better IDE support
8. **Profile performance**: Use Explorer to understand your data
9. **Leverage async**: Process multiple operations concurrently
10. **Document assumptions**: WhosOnFirst data has quirks; document your expectations
