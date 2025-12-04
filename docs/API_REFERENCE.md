# WOF Connector API Reference

## Core Classes

### WOFConnector

The main connector class for WhosOnFirst database operations.

#### Constructor

```python
WOFConnector(db_path: str)
```

**Parameters:**
- `db_path` (str): Path to the WhosOnFirst SQLite database file

#### Methods

##### `async connect() -> None`
Initialize database connection and reflect tables.

##### `async disconnect() -> None`
Close database connections and cleanup resources.

##### `async search(filters: WOFSearchFilters) -> WOFSearchCursor`
Search for places using filters.

**Parameters:**
- `filters` (WOFSearchFilters): Search criteria

**Returns:**
- WOFSearchCursor: Cursor for iterating results

##### `async get_place(place_id: int, include_geometry: bool = False) -> Optional[WOFPlace]`
Get a single place by ID.

**Parameters:**
- `place_id` (int): WhosOnFirst place ID
- `include_geometry` (bool): Include GeoJSON geometry data

**Returns:**
- WOFPlace or None if not found

##### `async get_places(place_ids: List[int], include_geometry: bool = False) -> List[WOFPlace]`
Get multiple places by IDs.

**Parameters:**
- `place_ids` (List[int]): List of WhosOnFirst place IDs
- `include_geometry` (bool): Include GeoJSON geometry data

**Returns:**
- List[WOFPlace]: List of places (empty if none found)

##### `async get_ancestors(place_id: int, filters: Optional[WOFFilters] = None) -> List[WOFPlace]`
Get all ancestors of a place.

**Parameters:**
- `place_id` (int): WhosOnFirst place ID
- `filters` (Optional[WOFFilters]): Optional filters for ancestors

**Returns:**
- List[WOFPlace]: Ancestors from root to immediate parent

##### `async get_descendants(place_id: int, filters: Optional[WOFFilters] = None) -> List[WOFPlace]`
Get all descendants of a place.

**Parameters:**
- `place_id` (int): WhosOnFirst place ID
- `filters` (Optional[WOFFilters]): Optional filters for descendants

**Returns:**
- List[WOFPlace]: All descendant places

##### `async get_names(place_id: int, language: Optional[str] = None) -> List[WOFName]`
Get alternative names for a place.

**Parameters:**
- `place_id` (int): WhosOnFirst place ID
- `language` (Optional[str]): ISO language code (e.g., 'fra', 'spa')

**Returns:**
- List[WOFName]: Alternative names

#### Properties

##### `explorer -> WOFExplorer`
Access database exploration tools (lazy-loaded).

##### `connected -> bool`
Check if connector is connected to database.

---

### WOFSearchFilters

Filters for search operations. All fields are optional.

#### Fields

##### Basic Filters
- `name` (str | List[str]): Exact name match
- `name_contains` (str): Partial name match (case-insensitive)
- `name_language` (str): Language for name search (default: 'eng')
- `name_type` (str): Name type (default: 'preferred')

##### Type Filters
- `placetype` (str | List[str]): Place type(s) to search
- `exclude_placetype` (str | List[str]): Place types to exclude

##### Location Filters
- `country` (str | List[str]): Country code(s) (e.g., 'US', 'CA')
- `repo` (str | List[str]): Repository name(s)

##### Hierarchy Filters
- `parent_id` (int | List[int]): Immediate parent ID(s)
- `parent_name` (str | List[str]): Immediate parent name(s)
- `ancestor_id` (int | List[int]): Any ancestor ID(s)
- `ancestor_name` (str | List[str]): Any ancestor name(s)

##### Status Filters
- `is_current` (bool): Only current places (default: None)
- `is_deprecated` (bool): Include deprecated places
- `is_ceased` (bool): Include ceased places
- `is_superseded` (bool): Include superseded places

##### Spatial Filters
- `bbox` (BBox): Bounding box for spatial search
- `near` (Point): Center point for proximity search
- `radius_km` (float): Radius in kilometers for proximity search
- `exclude_point_geoms` (bool): Exclude places with only point geometries
- `geometry_type` (str | List[str]): Specific geometry types

##### Result Control
- `limit` (Optional[int]): Maximum results (None = unlimited, default)
- `name_exact` (bool): Use exact name matching (default: False)

---

### WOFSearchCursor

Cursor for iterating through search results efficiently.

#### Properties

##### `total_count -> int`
Total number of results found.

##### `has_results -> bool`
Check if search returned any results.

##### `places -> List[WOFPlace]`
Access to lightweight place data (no geometry).

##### `query_filters -> Dict[str, Any]`
The filters used for this search.

#### Methods

##### `async fetch_one(index: int = 0, include_geometry: bool = False) -> Optional[WOFPlace]`
Fetch a single place by index.

**Parameters:**
- `index` (int): Index in results (default: 0)
- `include_geometry` (bool): Include GeoJSON geometry

**Returns:**
- WOFPlace or None if index out of range

##### `async fetch_all(include_geometry: bool = False) -> PlaceCollection`
Fetch all places as a collection.

**Parameters:**
- `include_geometry` (bool): Include GeoJSON geometry

**Returns:**
- PlaceCollection: Collection with all places

##### `async fetch_page(page: int, size: int = 100, include_geometry: bool = False) -> List[WOFPlace]`
Fetch a page of results.

**Parameters:**
- `page` (int): Page number (1-based)
- `size` (int): Results per page
- `include_geometry` (bool): Include GeoJSON geometry

**Returns:**
- List[WOFPlace]: Places for the requested page

##### `async __aiter__() -> AsyncIterator[WOFPlace]`
Async iteration support.

```python
async for place in cursor:
    print(place.name)
```

---

## High-Level Processing Helpers

### Quick Explore

Module: `wof_explorer.processing.quick_explore`

```python
from wof_explorer.processing.quick_explore import quick_explore, DEFAULT_FOCUS_CITIES

selections = await quick_explore(connector, focus_cities=DEFAULT_FOCUS_CITIES)

# selections keys:
#   'us_counties'     -> PlaceCollection
#   'cities'          -> PlaceCollection
#   'neighborhoods'   -> PlaceCollection

geojson = selections["neighborhoods"].to_geojson_string(indent=2)
```

### Under-Point (Point-In-Polygon)

Module: `wof_explorer.processing.spatial`

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

geojson = under.to_geojson_string(indent=2)
```

---

### PlaceCollection

Container for a collection of places with serialization and analysis capabilities.

#### Properties

##### `places -> List[WOFPlace]`
The places in this collection.

##### `metadata -> Dict[str, Any]`
Collection metadata including query filters.

##### `is_empty -> bool`
Check if collection is empty.

##### `has_geometry -> bool`
Check if any places have geometry data.

#### Methods

##### `get_summary(enrich_ancestors: bool = True) -> Dict[str, Any]`
Get intelligent summary with auto-grouping.

**Parameters:**
- `enrich_ancestors` (bool): Fetch ancestor data for grouping

**Returns:**
- Dict with summary including groupings and coverage

##### `async enrich_with_ancestors(connector: WOFConnector) -> PlaceCollection`
Enrich collection with ancestor data for better grouping.

**Parameters:**
- `connector` (WOFConnector): Connected WOFConnector instance

**Returns:**
- Self for method chaining

##### `save_geojson(filepath: str, use_polygons: bool = True, properties: Optional[List[str]] = None) -> None`
Save collection as GeoJSON file.

**Parameters:**
- `filepath` (str): Output file path
- `use_polygons` (bool): Use polygon geometry when available
- `properties` (Optional[List[str]]): Properties to include

##### `save_csv(filepath: str) -> None`
Save collection as CSV file.

**Parameters:**
- `filepath` (str): Output file path

##### `to_geojson(use_polygons: bool = True, properties: Optional[List[str]] = None) -> Dict`
Convert to GeoJSON FeatureCollection.

**Parameters:**
- `use_polygons` (bool): Use polygon geometry when available
- `properties` (Optional[List[str]]): Properties to include

**Returns:**
- Dict: GeoJSON FeatureCollection

##### `to_csv_rows() -> List[Dict[str, Any]]`
Convert to CSV-friendly rows.

**Returns:**
- List[Dict]: Rows suitable for CSV export

##### `to_wkt_list() -> List[Dict[str, Any]]`
Convert to Well-Known Text format.

**Returns:**
- List[Dict]: Places with WKT geometries

##### `filter(predicate: Callable[[WOFPlace], bool]) -> PlaceCollection`
Filter places by predicate.

**Parameters:**
- `predicate` (Callable): Function that returns True to keep place

**Returns:**
- PlaceCollection: New filtered collection

##### `group_by(attribute: str) -> Dict[Any, List[WOFPlace]]`
Group places by attribute.

**Parameters:**
- `attribute` (str): Attribute name to group by

**Returns:**
- Dict mapping attribute values to places

##### `find(name: str, exact: bool = True) -> List[WOFPlace]`
Find places by name.

**Parameters:**
- `name` (str): Name to search for
- `exact` (bool): Use exact matching

**Returns:**
- List[WOFPlace]: Matching places

##### `sample(n: int = 10, by: Optional[str] = None) -> PlaceCollection`
Get a representative sample.

**Parameters:**
- `n` (int): Number of samples
- `by` (Optional[str]): Attribute to stratify by

**Returns:**
- PlaceCollection: Sampled collection

---

### WOFExplorer

Database exploration and discovery tools.

#### Methods

##### `async database_summary() -> Dict[str, Any]`
Get comprehensive database overview.

**Returns:**
- Dict with statistics about the database

##### `async discover_places(placetype: str, parent_name: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]`
Discover places of a specific type.

**Parameters:**
- `placetype` (str): Type of places to discover
- `parent_name` (Optional[str]): Parent place name
- `limit` (int): Maximum results

**Returns:**
- List of place summaries with counts

##### `async suggest_starting_points() -> Dict[str, List[Dict[str, Any]]]`
Get suggested places to start exploring.

**Returns:**
- Dict with categorized suggestions

##### `async top_cities_by_coverage(limit: int = 20) -> List[Dict[str, Any]]`
Find cities with the most data coverage.

**Parameters:**
- `limit` (int): Number of cities to return

**Returns:**
- List of cities with coverage statistics

---

## Data Models

### WOFPlace

Core place data model.

#### Fields
- `id` (int): WhosOnFirst place ID
- `name` (str): Place name
- `placetype` (str): Place type
- `parent_id` (Optional[int]): Immediate parent ID
- `latitude` (float): Latitude coordinate
- `longitude` (float): Longitude coordinate
- `bbox` (BBox): Bounding box
- `is_current` (int): -1, 0, or 1 per WOF spec
- `is_deprecated` (bool): Place was incorrect
- `is_ceased` (bool): Place definition changed
- `is_superseded` (bool): Replaced by another place
- `is_superseding` (bool): Replaces another place
- `country` (Optional[str]): Country code
- `repo` (Optional[str]): Repository name
- `lastmodified` (Optional[int]): Unix timestamp
- `superseded_by` (Optional[str]): ID of replacement
- `supersedes` (Optional[str]): ID of replaced place
- `src_geom` (Optional[str]): Geometry source

#### Properties
- `is_active -> bool`: Check if place is currently active
- `center_point -> Tuple[float, float]`: Get center point

### WOFPlaceWithGeometry

Extended place model with geometry data.

#### Additional Fields
- `geometry` (Optional[Dict]): GeoJSON geometry
- `geometry_source` (Optional[str]): Source of geometry

#### Additional Properties
- `has_geometry -> bool`: Check if geometry is available
- `geometry_type -> Optional[str]`: Get geometry type

### BBox

Bounding box for spatial operations.

#### Fields
- `min_lat` (float): Minimum latitude
- `max_lat` (float): Maximum latitude
- `min_lon` (float): Minimum longitude
- `max_lon` (float): Maximum longitude

#### Methods
- `contains(lat: float, lon: float) -> bool`: Check if point is inside
- `intersects(other: BBox) -> bool`: Check if boxes intersect

### Point

Geographic point for proximity searches.

#### Fields
- `lat` (float): Latitude
- `lon` (float): Longitude

### WOFName

Alternative name for a place.

#### Fields
- `id` (int): Place ID
- `name` (str): Alternative name
- `language` (str): ISO language code
- `name_type` (str): Type of name
- `is_preferred` (bool): Preferred name for language
- `is_colloquial` (bool): Colloquial name
- `is_historic` (bool): Historic name

---

## Exceptions

### ConnectionError
Raised when database connection fails.

### RuntimeError
Raised when operations are attempted before connecting.

---

## Type Hints

The connector is fully type-hinted for IDE support and type checking:

```python
from typing import List, Optional, Dict, Any
from src import (
    WOFConnector,
    WOFSearchFilters,
    WOFPlace,
    PlaceCollection
)

async def typed_example(
    connector: WOFConnector,
    filters: WOFSearchFilters
) -> Optional[PlaceCollection]:
    cursor = await connector.search(filters)
    if cursor.has_results:
        return await cursor.fetch_all()
    return None
```
