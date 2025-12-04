# WOF Explorer Cursor API Documentation

## Overview

The WOF Explorer uses a **cursor-based navigation pattern** that enables efficient exploration of geographic hierarchies. This pattern separates data navigation (lightweight) from data fetching (selective), allowing you to explore large datasets without loading unnecessary data into memory.

## Core Concepts

### Two-Phase Exploration

1. **Phase 1: Navigate** - Move through data using lightweight metadata
2. **Phase 2: Fetch** - Selectively retrieve full details including geometry

### Three Types of Cursors

- **WOFSearchCursor** - Navigate search results
- **WOFHierarchyCursor** - Traverse place hierarchies
- **WOFBatchCursor** - Process multiple places efficiently

## WOFSearchCursor

The primary cursor for search results.

### Creation

```python
# Created automatically from search operations
cursor = await connector.search(WOFSearchFilters(
    placetype="locality",
    country="US"
))
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `places` | `List[WOFPlace]` | Lightweight place objects (no geometry) |
| `total_count` | `int` | Total number of results |
| `query_filters` | `Dict[str, Any]` | Filters used in the search |
| `has_results` | `bool` | Whether search returned results |

### Methods

#### `fetch_all(include_geometry: bool = False) -> PlaceCollection`

Fetch full details for all places in the cursor.

```python
# Without geometry (fast)
places = await cursor.fetch_all()

# With geometry (slower, more memory)
places_with_geom = await cursor.fetch_all(include_geometry=True)

#### `fetch_geometries() -> PlaceCollection`

Convenience alias for `fetch_all(include_geometry=True)`. Returns a PlaceCollection with geometry loaded where available.

```python
collection = await cursor.fetch_geometries()
print(collection)  # e.g., PlaceCollection(200 places: locality:200 | with Polygon/MultiPolygon)
```
```

#### `fetch_one(index: int = 0, include_geometry: bool = False) -> Optional[WOFPlace]`

Fetch a single place by index.

```python
# Get the first result with geometry
place = await cursor.fetch_one(0, include_geometry=True)
```

#### `fetch_page(page: int = 1, size: int = 10, include_geometry: bool = False) -> PlaceCollection`

Fetch a specific page of results.

```python
# Get page 2 with 20 items per page
page2 = await cursor.fetch_page(page=2, size=20)
```

#### `fetch_by_ids(place_ids: List[int], include_geometry: bool = False) -> List[WOFPlace]`

Fetch specific places from the cursor by their IDs.

```python
# Only fetch specific places
selected = await cursor.fetch_by_ids([123, 456, 789])
```

#### `filter_places(**kwargs) -> List[WOFPlace]`

Filter cursor places by attributes (lightweight operation).

```python
# Filter without fetching
current_places = cursor.filter_places(is_current=True)
california_places = cursor.filter_places(country="US", region="California")
```

#### `to_geojson(fetch_geometry: bool = True) -> Dict[str, Any]`

Convert to GeoJSON FeatureCollection.

```python
# Automatically fetches geometry if needed
geojson = await cursor.to_geojson()

# Or use point locations only
geojson_points = await cursor.to_geojson(fetch_geometry=False)
```

## WOFHierarchyCursor

Navigate place hierarchies efficiently.

### Creation

```python
# From a known place
place = cursor.places[0]
hierarchy = WOFHierarchyCursor(place, connector)
```

### Methods

#### `fetch_ancestors(include_geometry: bool = False) -> List[WOFPlace]`

Get all ancestors from immediate parent to root.

```python
ancestors = await hierarchy.fetch_ancestors()
# Returns: [parent, grandparent, ..., country, continent]
```

#### `fetch_descendants(filters: Optional[WOFFilters] = None, include_geometry: bool = False) -> List[WOFPlace]`

Get all descendants matching optional filters.

```python
# All descendants
all_desc = await hierarchy.fetch_descendants()

# Only neighborhoods
neighborhoods = await hierarchy.fetch_descendants(
    filters=WOFFilters(placetype="neighbourhood")
)
```

#### `fetch_children(placetype: Optional[str] = None, include_geometry: bool = False) -> List[WOFPlace]`

Get immediate children only.

```python
# Direct children
children = await hierarchy.fetch_children()

# Only locality children
cities = await hierarchy.fetch_children(placetype="locality")
```

#### `fetch_siblings(include_geometry: bool = False) -> List[WOFPlace]`

Get siblings (same parent, same type).

```python
siblings = await hierarchy.fetch_siblings()
```

#### `build_tree(max_depth: Optional[int] = None) -> Dict[str, Any]`

Build complete hierarchy tree.

```python
# Full tree
tree = await hierarchy.build_tree()

# Limited depth
tree = await hierarchy.build_tree(max_depth=3)
```

## WOFBatchCursor

Process multiple places efficiently.

### Creation

```python
# From known IDs
place_ids = [123, 456, 789]
batch = WOFBatchCursor(place_ids, connector)
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `place_ids` | `List[int]` | IDs being processed |
| `count` | `int` | Number of places |

### Methods

#### `fetch_all(include_geometry: bool = False) -> List[WOFPlace]`

Fetch all places in the batch.

```python
places = await batch.fetch_all(include_geometry=True)
```

#### `fetch_hierarchies() -> List[Dict[str, Any]]`

Get hierarchy information for all places.

```python
hierarchies = await batch.fetch_hierarchies()
for h in hierarchies:
    print(f"Place {h['place_id']} has {len(h['ancestors'])} ancestors")
```

#### `process_in_chunks(chunk_size: int = 100, include_geometry: bool = False)`

Process large batches in chunks (async generator).

```python
# Process 1000 places in chunks of 100
large_batch = WOFBatchCursor(place_ids_1000, connector)
async for chunk in large_batch.process_in_chunks(chunk_size=100):
    # Process each chunk
    for place in chunk:
        process_place(place)
```

## Common Patterns

### Pattern 0: Filter → Fetch Geometries → Write

```python
from pathlib import Path
from wof_explorer.models.filters import WOFSearchFilters

# 1) Filter with lightweight search
cursor = await connector.search(WOFSearchFilters(
    placetype="locality",
    country="US",
    is_current=True,
    limit=200,
))

# 2) Fetch geometries only for the filtered set
collection = await cursor.fetch_geometries()

# 3) Write to GeoJSON
Path("output").mkdir(parents=True, exist_ok=True)
Path("output/us_localities_subset.geojson").write_text(
    collection.to_geojson_string(indent=2, use_polygons=True, require_geometry=False),
    encoding="utf-8",
)
```

### Pattern 1: Search, Filter, Fetch

```python
# 1. Search (lightweight)
cursor = await connector.search(WOFSearchFilters(
    placetype="neighbourhood",
    country="US"
))

# 2. Filter (still lightweight)
filtered = [p for p in cursor.places if p.is_current and "Historic" in p.name]

# 3. Fetch (selective, with geometry)
final_places = await connector.get_places(
    [p.id for p in filtered],
    include_geometry=True
)
```

### Pattern 2: Navigate Hierarchy, Then Fetch

```python
# 1. Find starting point
city_cursor = await connector.search(WOFSearchFilters(name="Boston"))

# 2. Navigate (lightweight)
hierarchy = WOFHierarchyCursor(city_cursor.places[0], connector)
neighborhoods = await hierarchy.fetch_descendants(
    filters=WOFFilters(placetype="neighbourhood")
)

# 3. Fetch geometry for export
with_geometry = await connector.get_places(
    [n.id for n in neighborhoods],
    include_geometry=True
)

# 4. Export
collection = PlaceCollection(places=with_geometry)
geojson = collection.to_geojson_string()
```

### Pattern 3: Bulk Processing

```python
# Process large dataset in chunks
all_cities = await connector.search(WOFSearchFilters(
    placetype="locality",
    is_current=True
))

# Create batch from search results
city_ids = [c.id for c in all_cities.places]
batch = WOFBatchCursor(city_ids, connector)

# Process in memory-efficient chunks
async for chunk in batch.process_in_chunks(chunk_size=50):
    # Each chunk has full place data
    for city in chunk:
        await process_city(city)
```

## Performance Guidelines

### DO ✅

- Use cursors to navigate before fetching
- Filter results while they're still lightweight
- Fetch geometry only when needed for export
- Process large datasets in chunks
- Cache cursor results if you'll reuse them

### DON'T ❌

- Fetch geometry for filtering or counting
- Call `fetch_all(include_geometry=True)` on large result sets
- Fetch the same data multiple times
- Load entire hierarchies when you only need one level

## Memory Optimization

```python
# BAD: Loads everything into memory
cursor = await connector.search(WOFSearchFilters(placetype="neighbourhood"))
all_with_geom = await cursor.fetch_all(include_geometry=True)  # 🚨 Huge memory usage

# GOOD: Selective loading
cursor = await connector.search(WOFSearchFilters(placetype="neighbourhood"))
filtered = [p for p in cursor.places if meets_criteria(p)]
selected_with_geom = await connector.get_places(
    [p.id for p in filtered[:100]],  # Limit to 100
    include_geometry=True
)

# BETTER: Chunked processing
batch = WOFBatchCursor([p.id for p in filtered], connector)
async for chunk in batch.process_in_chunks(chunk_size=25):
    # Process 25 at a time
    await process_chunk(chunk)
```

## Export Examples

### To GeoJSON

```python
# Direct from cursor
geojson = await cursor.to_geojson()

# Or via PlaceCollection for more control
places = await cursor.fetch_all(include_geometry=True)
geojson = places.to_geojson_string(
    properties=["id", "name", "placetype", "population"],
    indent=2
)
```

### To CSV

```python
# Get CSV-friendly rows
rows = cursor.to_csv_rows()

# Or use PlaceCollection
places = await cursor.fetch_all()
csv_string = places.to_csv_string(
    columns=["id", "name", "latitude", "longitude", "placetype"]
)
```

### To WKT

```python
# Get Well-Known Text for GIS tools
wkt_list = await cursor.to_wkt_list(fetch_geometry=True)
for item in wkt_list:
    print(f"{item['name']}: {item['wkt']}")
```

## Error Handling

```python
try:
    cursor = await connector.search(filters)

    if not cursor.has_results:
        print("No results found")
        return

    # Safe to proceed
    places = await cursor.fetch_all()

except RuntimeError as e:
    print(f"Search failed: {e}")
```

## Threading and Async

All cursor operations are async and should be awaited:

```python
# Correct
places = await cursor.fetch_all()

# Incorrect - will return coroutine
places = cursor.fetch_all()  # ❌ Missing await
```

For parallel operations:

```python
import asyncio

# Fetch multiple hierarchies in parallel
async def get_all_hierarchies(place_ids):
    tasks = []
    for place_id in place_ids:
        hierarchy = WOFHierarchyCursor(place, connector)
        tasks.append(hierarchy.fetch_ancestors())

    # Run in parallel
    results = await asyncio.gather(*tasks)
    return results
```
