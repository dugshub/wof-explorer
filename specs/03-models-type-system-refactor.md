# Models & Type System Refactor Specification

## Work Stream 3: Domain Models and Type Definitions Reorganization

### Current State Analysis

The models and type system are partially organized:
- `models/places.py` (197 lines) contains all place-related models including hierarchy
- `models/filters.py` (199 lines) contains filter specifications
- Result containers are embedded in `processing/cursors.py`
- No clear separation between data models and domain logic

### Target Architecture

```
models/
├── __init__.py           # Public model exports
├── places.py             # Core place models (150 lines)
├── hierarchy.py          # Hierarchy models (100 lines)
├── filters.py            # [EXISTING] Filter specifications
├── results.py            # Result containers (150 lines)
└── geometry.py           # Geometry-specific models (100 lines)

types.py                  # Type definitions and enums (150 lines)
```

### Detailed Migration Plan

#### Phase 1: Create Type System Foundation
**File**: `types.py`

```python
"""
Type definitions and enumerations for WOF Explorer.
Central location for all type aliases, enums, and constants.
"""

from enum import Enum
from typing import TypeAlias, Union, Literal, Tuple, List, Optional

# Coordinate Types
Longitude: TypeAlias = float
Latitude: TypeAlias = float
Coordinate: TypeAlias = Tuple[Longitude, Latitude]
BBox: TypeAlias = Tuple[Longitude, Latitude, Longitude, Latitude]

# ID Types
PlaceID: TypeAlias = int
ParentID: TypeAlias = Optional[int]
AncestorID: TypeAlias = int

# Geometry Types
GeometryType = Literal["Point", "Polygon", "MultiPolygon", "LineString", "MultiLineString"]
GeoJSONGeometry: TypeAlias = dict  # Will be refined with TypedDict

# Data Source Types
DatabasePath: TypeAlias = str
DatabaseAlias: TypeAlias = str
SourceIdentifier: TypeAlias = str

class PlaceType(str, Enum):
    """WhosOnFirst place types in hierarchical order."""

    PLANET = "planet"
    CONTINENT = "continent"
    EMPIRE = "empire"
    COUNTRY = "country"
    DISPUTED = "disputed"
    DEPENDENCY = "dependency"
    MACROREGION = "macroregion"
    REGION = "region"
    MACROCOUNTY = "macrocounty"
    COUNTY = "county"
    LOCALADMIN = "localadmin"
    LOCALITY = "locality"
    BOROUGH = "borough"
    MACROHOOD = "macrohood"
    NEIGHBOURHOOD = "neighbourhood"
    MICROHOOD = "microhood"
    CAMPUS = "campus"
    VENUE = "venue"
    BUILDING = "building"
    ADDRESS = "address"
    CUSTOM = "custom"
    OCEAN = "ocean"
    MARINEAREA = "marinearea"

    @classmethod
    def get_hierarchy_level(cls, placetype: str) -> int:
        """Get hierarchical level of placetype."""
        order = list(cls)
        try:
            return order.index(cls(placetype))
        except (ValueError, KeyError):
            return 999  # Unknown types go to bottom

    @classmethod
    def is_admin_level(cls, placetype: str) -> bool:
        """Check if placetype is administrative level."""
        admin_types = {
            cls.COUNTRY, cls.REGION, cls.COUNTY,
            cls.LOCALADMIN, cls.LOCALITY
        }
        try:
            return cls(placetype) in admin_types
        except ValueError:
            return False

class PlaceStatus(str, Enum):
    """Place lifecycle status."""

    CURRENT = "current"
    DEPRECATED = "deprecated"
    CEASED = "ceased"
    SUPERSEDED = "superseded"
    SUPERSEDING = "superseding"

class DataQuality(str, Enum):
    """Data quality tiers."""

    COMPLETE = "complete"    # All fields present
    GOOD = "good"            # Core fields + some optional
    BASIC = "basic"          # Core fields only
    MINIMAL = "minimal"      # Missing core fields

class GeometryPrecision(str, Enum):
    """Geometry precision levels."""

    EXACT = "exact"          # Full precision geometry
    SIMPLIFIED = "simplified" # Reduced point count
    BBOX = "bbox"            # Bounding box only
    POINT = "point"          # Centroid only
    NONE = "none"            # No geometry

class NameLanguage(str, Enum):
    """Common language codes for alternative names."""

    ENGLISH = "eng"
    FRENCH = "fra"
    SPANISH = "spa"
    GERMAN = "deu"
    ITALIAN = "ita"
    PORTUGUESE = "por"
    RUSSIAN = "rus"
    CHINESE = "zho"
    JAPANESE = "jpn"
    ARABIC = "ara"
    HINDI = "hin"

    @classmethod
    def get_x_codes(cls) -> List[str]:
        """Get preferred/default language codes."""
        return ["eng_x_preferred", "eng_x_variant", "eng_x_colloquial"]

# Search Options
SortOrder = Literal["asc", "desc"]
SortField = Literal["name", "placetype", "population", "area", "lastmodified"]
OutputFormat = Literal["geojson", "csv", "wkt", "json", "summary"]

# Expansion Options
ExpansionType = Literal["ancestors", "descendants", "children", "siblings"]
ExpansionDepth = Union[int, Literal["all"]]

# Filter Operators
FilterOperator = Literal["eq", "ne", "gt", "gte", "lt", "lte", "in", "nin", "like", "ilike"]
LogicalOperator = Literal["and", "or", "not"]

# Result Types
ResultFormat = Literal["full", "summary", "id_only", "name_only"]
CursorState = Literal["ready", "fetching", "exhausted", "error"]

# Constants
DEFAULT_BATCH_SIZE = 100
MAX_BATCH_SIZE = 10000
DEFAULT_SEARCH_LIMIT = 1000
MAX_SEARCH_LIMIT = 100000
DEFAULT_EXPANSION_DEPTH = 1
MAX_EXPANSION_DEPTH = 10

# Type Guards
def is_valid_placetype(value: str) -> bool:
    """Check if value is valid placetype."""
    try:
        PlaceType(value)
        return True
    except ValueError:
        return False

def is_valid_bbox(value: Any) -> bool:
    """Check if value is valid bounding box."""
    return (
        isinstance(value, (list, tuple)) and
        len(value) == 4 and
        all(isinstance(v, (int, float)) for v in value) and
        value[0] <= value[2] and  # min_lon <= max_lon
        value[1] <= value[3]       # min_lat <= max_lat
    )

def is_valid_coordinate(value: Any) -> bool:
    """Check if value is valid coordinate."""
    return (
        isinstance(value, (list, tuple)) and
        len(value) == 2 and
        all(isinstance(v, (int, float)) for v in value) and
        -180 <= value[0] <= 180 and  # longitude
        -90 <= value[1] <= 90         # latitude
    )
```

**Migration considerations**:
- Keep all enums and type aliases consolidated in `types.py`
- Add type aliases for common types
- Add validation functions
- Add constants

#### Phase 2: Extract Hierarchy Models
**File**: `models/hierarchy.py`

```python
"""
Hierarchy models for WOF place relationships.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from ..types import PlaceID, PlaceType

class WOFAncestor(BaseModel):
    """Represents an ancestor in the geographic hierarchy."""
    # Move from places.py lines 75-95

    id: PlaceID
    name: str
    placetype: PlaceType
    country: Optional[str] = None
    region: Optional[str] = None
    level: int = Field(0, description="Hierarchy level (0=immediate parent)")

    class Config:
        frozen = True

    def is_country(self) -> bool:
        """Check if ancestor is country level."""
        return self.placetype == PlaceType.COUNTRY

    def is_region(self) -> bool:
        """Check if ancestor is region level."""
        return self.placetype == PlaceType.REGION

    def is_admin(self) -> bool:
        """Check if ancestor is administrative level."""
        return PlaceType.is_admin_level(self.placetype)

class WOFHierarchy(BaseModel):
    """Complete hierarchy information for a place."""
    # Move from places.py lines 96-130

    place_id: PlaceID
    ancestors: List[WOFAncestor] = []
    descendants_count: Dict[PlaceType, int] = {}
    parent: Optional[WOFAncestor] = None
    children: List['WOFPlaceRef'] = []
    siblings: List['WOFPlaceRef'] = []

    def get_country(self) -> Optional[WOFAncestor]:
        """Get country ancestor."""
        for ancestor in self.ancestors:
            if ancestor.is_country():
                return ancestor
        return None

    def get_region(self) -> Optional[WOFAncestor]:
        """Get region ancestor."""
        for ancestor in self.ancestors:
            if ancestor.is_region():
                return ancestor
        return None

    def get_admin_chain(self) -> List[WOFAncestor]:
        """Get administrative hierarchy chain."""
        return [a for a in self.ancestors if a.is_admin()]

    def get_ancestor_by_type(self, placetype: PlaceType) -> Optional[WOFAncestor]:
        """Get ancestor of specific type."""
        for ancestor in self.ancestors:
            if ancestor.placetype == placetype:
                return ancestor
        return None

    def get_depth(self) -> int:
        """Get depth in hierarchy."""
        return len(self.ancestors)

    def is_leaf(self) -> bool:
        """Check if place has no descendants."""
        return sum(self.descendants_count.values()) == 0

    def is_root(self) -> bool:
        """Check if place has no ancestors."""
        return len(self.ancestors) == 0

class WOFPlaceRef(BaseModel):
    """Lightweight reference to a place."""

    id: PlaceID
    name: str
    placetype: PlaceType

    class Config:
        frozen = True

class HierarchyPath(BaseModel):
    """Represents a path through the hierarchy."""

    path: List[WOFPlaceRef]

    def to_string(self, separator: str = " > ") -> str:
        """Convert path to string representation."""
        return separator.join(p.name for p in self.path)

    def get_types(self) -> List[PlaceType]:
        """Get placetypes in path."""
        return [p.placetype for p in self.path]

    def contains_type(self, placetype: PlaceType) -> bool:
        """Check if path contains placetype."""
        return placetype in self.get_types()
```

**Migration from `places.py`**:
- Move lines 75-95 (WOFAncestor) → hierarchy.py
- Move lines 96-130 (WOFHierarchy) → hierarchy.py
- Add new helper classes

#### Phase 3: Extract Result Containers
**File**: `models/results.py`

```python
"""
Result container models for WOF queries.
"""

from typing import List, Optional, Dict, Any, Generic, TypeVar
from pydantic import BaseModel, Field
from ..types import PlaceID, ResultFormat, CursorState

T = TypeVar('T')

class WOFSearchResult(BaseModel):
    """Container for search results with metadata."""
    # Move from places.py lines 131-145

    total_count: int
    returned_count: int
    offset: int = 0
    limit: Optional[int] = None
    has_more: bool = False
    query_time_ms: Optional[float] = None
    filters_applied: Dict[str, Any] = {}

    def get_page_info(self) -> Dict[str, Any]:
        """Get pagination information."""
        return {
            'page': (self.offset // (self.limit or 100)) + 1 if self.limit else 1,
            'per_page': self.limit,
            'total_pages': (self.total_count // (self.limit or 100)) + 1 if self.limit else 1,
            'has_next': self.has_more,
            'has_prev': self.offset > 0
        }

class BatchResult(BaseModel, Generic[T]):
    """Result container for batch operations."""

    items: List[T]
    succeeded: List[PlaceID]
    failed: List[PlaceID]
    errors: Dict[PlaceID, str] = {}

    def success_rate(self) -> float:
        """Calculate success rate."""
        total = len(self.succeeded) + len(self.failed)
        return len(self.succeeded) / total if total > 0 else 0.0

    def get_failed_items(self) -> List[Tuple[PlaceID, str]]:
        """Get failed items with error messages."""
        return [(id, self.errors.get(id, "Unknown error"))
                for id in self.failed]

class CursorResult(BaseModel, Generic[T]):
    """Result from cursor-based fetching."""
    # Extract from cursors.py

    items: List[T]
    cursor_state: CursorState
    cursor_position: Optional[str] = None
    has_next: bool = False
    fetch_count: int = 0
    total_fetched: int = 0

    def is_exhausted(self) -> bool:
        """Check if cursor is exhausted."""
        return self.cursor_state == "exhausted" or not self.has_next

    def is_error(self) -> bool:
        """Check if cursor encountered error."""
        return self.cursor_state == "error"

class AggregateResult(BaseModel):
    """Result from aggregation queries."""

    aggregations: Dict[str, Any]
    group_by: Optional[List[str]] = None
    metrics: Dict[str, float] = {}

    def get_top_n(self, field: str, n: int = 10) -> List[Tuple[Any, int]]:
        """Get top N values for field."""
        if field not in self.aggregations:
            return []

        data = self.aggregations[field]
        if isinstance(data, dict):
            sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)
            return sorted_items[:n]
        return []

class SpatialResult(BaseModel):
    """Result from spatial queries."""

    places: List[Any]  # Will be WOFPlace
    bbox: Optional[List[float]] = None
    centroid: Optional[List[float]] = None
    total_area_m2: Optional[float] = None
    density: Optional[Dict[str, Any]] = None

    def get_bounds(self) -> Optional[List[float]]:
        """Get bounding box of results."""
        return self.bbox

    def get_center(self) -> Optional[List[float]]:
        """Get center point of results."""
        return self.centroid

class ValidationResult(BaseModel):
    """Result from data validation."""

    valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    field_errors: Dict[str, List[str]] = {}

    def add_error(self, message: str, field: Optional[str] = None):
        """Add validation error."""
        self.valid = False
        self.errors.append(message)
        if field:
            if field not in self.field_errors:
                self.field_errors[field] = []
            self.field_errors[field].append(message)

    def add_warning(self, message: str):
        """Add validation warning."""
        self.warnings.append(message)

    def merge(self, other: 'ValidationResult'):
        """Merge another validation result."""
        self.valid = self.valid and other.valid
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        for field, errors in other.field_errors.items():
            if field not in self.field_errors:
                self.field_errors[field] = []
            self.field_errors[field].extend(errors)

class ExportResult(BaseModel):
    """Result from export operations."""

    format: str
    size_bytes: int
    record_count: int
    file_path: Optional[str] = None
    content: Optional[str] = None
    metadata: Dict[str, Any] = {}

    def get_size_mb(self) -> float:
        """Get size in megabytes."""
        return self.size_bytes / (1024 * 1024)

    def is_file_export(self) -> bool:
        """Check if exported to file."""
        return self.file_path is not None

    def is_content_export(self) -> bool:
        """Check if exported to string."""
        return self.content is not None
```

**Migration from various files**:
- Move WOFSearchResult from places.py
- Extract cursor results from cursors.py
- Add new result containers for different operations

#### Phase 4: Extract Geometry Models
**File**: `models/geometry.py`

```python
"""
Geometry-specific models for WOF places.
"""

from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field, validator
from ..types import BBox, Coordinate, GeometryType, GeometryPrecision

class WOFGeometry(BaseModel):
    """Geometry information for a place."""

    type: GeometryType
    coordinates: Union[List, List[List], List[List[List]]]
    precision: GeometryPrecision = GeometryPrecision.EXACT

    @validator('coordinates')
    def validate_coordinates(cls, v, values):
        """Validate coordinates match geometry type."""
        geom_type = values.get('type')
        if geom_type == 'Point':
            if not isinstance(v, list) or len(v) != 2:
                raise ValueError("Point must have [lon, lat] coordinates")
        elif geom_type == 'Polygon':
            if not isinstance(v, list) or not all(isinstance(ring, list) for ring in v):
                raise ValueError("Polygon must have list of rings")
        elif geom_type == 'MultiPolygon':
            if not isinstance(v, list) or not all(isinstance(poly, list) for poly in v):
                raise ValueError("MultiPolygon must have list of polygons")
        return v

    def to_geojson(self) -> Dict[str, Any]:
        """Convert to GeoJSON geometry."""
        return {
            "type": self.type,
            "coordinates": self.coordinates
        }

    def to_wkt(self) -> str:
        """Convert to Well-Known Text."""
        # Implementation for WKT conversion
        if self.type == "Point":
            return f"POINT({self.coordinates[0]} {self.coordinates[1]})"
        # Add other geometry types
        return f"{self.type.upper()} EMPTY"

    def simplify(self, tolerance: float = 0.001) -> 'WOFGeometry':
        """Simplify geometry to reduce complexity."""
        # Implementation for geometry simplification
        return WOFGeometry(
            type=self.type,
            coordinates=self.coordinates,  # Simplified
            precision=GeometryPrecision.SIMPLIFIED
        )

class WOFBounds(BaseModel):
    """Bounding box for a place."""

    min_lon: float = Field(..., ge=-180, le=180)
    min_lat: float = Field(..., ge=-90, le=90)
    max_lon: float = Field(..., ge=-180, le=180)
    max_lat: float = Field(..., ge=-90, le=90)

    @validator('max_lon')
    def validate_lon_order(cls, v, values):
        """Ensure max_lon >= min_lon."""
        if 'min_lon' in values and v < values['min_lon']:
            raise ValueError("max_lon must be >= min_lon")
        return v

    @validator('max_lat')
    def validate_lat_order(cls, v, values):
        """Ensure max_lat >= min_lat."""
        if 'min_lat' in values and v < values['min_lat']:
            raise ValueError("max_lat must be >= min_lat")
        return v

    def to_tuple(self) -> BBox:
        """Convert to tuple format."""
        return (self.min_lon, self.min_lat, self.max_lon, self.max_lat)

    def to_list(self) -> List[float]:
        """Convert to list format."""
        return [self.min_lon, self.min_lat, self.max_lon, self.max_lat]

    def contains_point(self, lon: float, lat: float) -> bool:
        """Check if point is within bounds."""
        return (
            self.min_lon <= lon <= self.max_lon and
            self.min_lat <= lat <= self.max_lat
        )

    def intersects(self, other: 'WOFBounds') -> bool:
        """Check if bounds intersect."""
        return not (
            self.max_lon < other.min_lon or
            self.min_lon > other.max_lon or
            self.max_lat < other.min_lat or
            self.min_lat > other.max_lat
        )

    def union(self, other: 'WOFBounds') -> 'WOFBounds':
        """Create union of two bounds."""
        return WOFBounds(
            min_lon=min(self.min_lon, other.min_lon),
            min_lat=min(self.min_lat, other.min_lat),
            max_lon=max(self.max_lon, other.max_lon),
            max_lat=max(self.max_lat, other.max_lat)
        )

    def get_center(self) -> Coordinate:
        """Get center point of bounds."""
        return (
            (self.min_lon + self.max_lon) / 2,
            (self.min_lat + self.max_lat) / 2
        )

    def get_area_degrees(self) -> float:
        """Get area in square degrees."""
        return (self.max_lon - self.min_lon) * (self.max_lat - self.min_lat)

class WOFCentroid(BaseModel):
    """Centroid point for a place."""

    lon: float = Field(..., ge=-180, le=180)
    lat: float = Field(..., ge=-90, le=90)
    source: str = "calculated"  # calculated, label, geometric

    def to_tuple(self) -> Coordinate:
        """Convert to coordinate tuple."""
        return (self.lon, self.lat)

    def to_point_geometry(self) -> WOFGeometry:
        """Convert to Point geometry."""
        return WOFGeometry(
            type="Point",
            coordinates=[self.lon, self.lat],
            precision=GeometryPrecision.POINT
        )

    def distance_to(self, other: 'WOFCentroid') -> float:
        """Calculate distance to another centroid (degrees)."""
        import math
        return math.sqrt(
            (self.lon - other.lon) ** 2 +
            (self.lat - other.lat) ** 2
        )
```

#### Phase 5: Refactor Core Place Models
**File**: `models/places.py` (refactored)

```python
"""
Core place models for WOF Explorer.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from ..types import PlaceID, ParentID, PlaceType, PlaceStatus
from .geometry import WOFGeometry, WOFBounds, WOFCentroid

class WOFPlace(BaseModel):
    """Core WhosOnFirst place model."""
    # Refactored from original places.py lines 10-74

    # Identity
    id: PlaceID
    name: str
    placetype: PlaceType

    # Hierarchy
    parent_id: ParentID = None

    # Status
    is_current: bool = True
    deprecated: Optional[datetime] = None
    cessation: Optional[datetime] = None
    superseded_by: Optional[List[PlaceID]] = None
    supersedes: Optional[List[PlaceID]] = None

    # Location
    country: Optional[str] = None
    region: Optional[str] = None
    county: Optional[str] = None
    locality: Optional[str] = None
    neighbourhood: Optional[str] = None

    # Spatial (basic)
    bbox: Optional[List[float]] = None
    centroid: Optional[List[float]] = None

    # Metadata
    population: Optional[int] = None
    area_m2: Optional[float] = None
    source: Optional[str] = None
    lastmodified: Optional[datetime] = None
    repo: Optional[str] = None

    class Config:
        frozen = False
        extra = "allow"  # Allow extra fields from database

    def get_status(self) -> PlaceStatus:
        """Get place status."""
        if self.cessation:
            return PlaceStatus.CEASED
        elif self.deprecated:
            return PlaceStatus.DEPRECATED
        elif self.superseded_by:
            return PlaceStatus.SUPERSEDED
        elif self.supersedes:
            return PlaceStatus.SUPERSEDING
        else:
            return PlaceStatus.CURRENT

    def get_bounds(self) -> Optional[WOFBounds]:
        """Get bounds object."""
        if self.bbox and len(self.bbox) == 4:
            return WOFBounds(
                min_lon=self.bbox[0],
                min_lat=self.bbox[1],
                max_lon=self.bbox[2],
                max_lat=self.bbox[3]
            )
        return None

    def get_centroid(self) -> Optional[WOFCentroid]:
        """Get centroid object."""
        if self.centroid and len(self.centroid) == 2:
            return WOFCentroid(
                lon=self.centroid[0],
                lat=self.centroid[1]
            )
        return None

    def get_hierarchy_fields(self) -> Dict[str, Optional[str]]:
        """Get hierarchy location fields."""
        return {
            'country': self.country,
            'region': self.region,
            'county': self.county,
            'locality': self.locality,
            'neighbourhood': self.neighbourhood
        }

    def is_administrative(self) -> bool:
        """Check if place is administrative level."""
        return PlaceType.is_admin_level(self.placetype)

    def to_reference(self) -> 'WOFPlaceRef':
        """Convert to lightweight reference."""
        from .hierarchy import WOFPlaceRef
        return WOFPlaceRef(
            id=self.id,
            name=self.name,
            placetype=self.placetype
        )

class WOFPlaceWithGeometry(WOFPlace):
    """Place model with full geometry data."""
    # Simplified from original

    geometry: Optional[Dict[str, Any]] = None

    def get_geometry(self) -> Optional[WOFGeometry]:
        """Get geometry object."""
        if self.geometry:
            return WOFGeometry(
                type=self.geometry.get('type'),
                coordinates=self.geometry.get('coordinates')
            )
        return None

    def has_geometry(self) -> bool:
        """Check if place has geometry."""
        return self.geometry is not None

    def get_geometry_type(self) -> Optional[str]:
        """Get geometry type."""
        if self.geometry:
            return self.geometry.get('type')
        return None

class WOFName(BaseModel):
    """Alternative name for a place."""
    # New model for name handling

    place_id: PlaceID
    language: str
    name: str
    preferred: bool = False
    colloquial: bool = False
    historic: bool = False

    class Config:
        frozen = True

    def is_english(self) -> bool:
        """Check if name is English."""
        return self.language.startswith('eng')

    def is_preferred(self) -> bool:
        """Check if name is preferred."""
        return self.preferred or '_x_preferred' in self.language
```

**Migration from `places.py`**:
- Simplify WOFPlace to core fields
- Move geometry to separate concern
- Move hierarchy to hierarchy.py
- Add helper methods for conversions

### Testing Requirements

1. **Unit Tests** for each model:
   - `test_types.py`: Type validation and guards
   - `test_hierarchy.py`: Hierarchy operations
   - `test_results.py`: Result containers
   - `test_geometry.py`: Geometry operations
   - `test_places.py`: Core place models

2. **Integration Tests**:
   - Model serialization/deserialization
   - Type conversions
   - Validation rules

3. **Migration Tests**:
   - Ensure backward compatibility
   - Test all model methods still work
   - Verify no data loss

### Success Criteria

1. **Code Organization**:
   - Clear separation between models
   - Each file under 200 lines
   - Single responsibility per model

2. **Type Safety**:
   - Strong typing throughout
   - Type guards for validation
   - Clear type aliases

3. **Maintainability**:
   - Models are immutable where appropriate
   - Clear validation rules
   - Good documentation

4. **Compatibility**:
   - All existing code works
   - No breaking changes to API
   - Smooth migration path

### Implementation Order

1. Ensure `types.py` is the authoritative source for enums and type aliases
2. Extract hierarchy models
3. Create result containers
4. Create geometry models
5. Refactor place models
6. Update all imports
7. Run tests and fix issues

### Risk Mitigation

- Keep original files during migration
- Update imports gradually
- Test each model independently
- Ensure backward compatibility
- Document all changes

### Estimated Effort

- Type System: 2 hours
- Hierarchy Models: 2 hours
- Result Containers: 3 hours
- Geometry Models: 2 hours
- Place Model Refactor: 2 hours
- Import Updates: 1 hour
- Testing: 2 hours
- **Total: 14 hours**

### Post-Refactor Benefits

1. **Clear Domain Model**: Each model has single responsibility
2. **Type Safety**: Strong typing with validation
3. **Extensibility**: Easy to add new model types
4. **Testing**: Models can be tested in isolation
5. **Documentation**: Self-documenting through types
6. **Performance**: Lighter models with optional fields
7. **Maintainability**: Smaller, focused files
