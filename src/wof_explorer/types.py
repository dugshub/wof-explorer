"""
Type definitions and enumerations for WOF Explorer.
Central location for all type aliases, enums, and constants.
"""

from enum import Enum
from typing import TypeAlias, Union, Literal, Tuple, List, Optional, Any

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
GeometryType = Literal[
    "Point",
    "Polygon",
    "MultiPolygon",
    "LineString",
    "MultiLineString",
    "GeometryCollection",
]
GeoJSONGeometry: TypeAlias = dict  # Will be refined with TypedDict

# Data Source Types
DatabasePath: TypeAlias = str
DatabaseAlias: TypeAlias = str
SourceIdentifier: TypeAlias = str


PlacetypeLike = Union[str, "PlaceType"]


class PlaceType(str, Enum):
    """WhosOnFirst place types in hierarchical order."""

    # Global/Continental
    PLANET = "planet"
    CONTINENT = "continent"
    EMPIRE = "empire"

    # Country level
    COUNTRY = "country"
    DISPUTED = "disputed"
    DEPENDENCY = "dependency"

    # Regional
    MACROREGION = "macroregion"
    REGION = "region"  # Province/State

    # County level
    MACROCOUNTY = "macrocounty"
    COUNTY = "county"  # County/District

    # Local
    LOCALADMIN = "localadmin"  # Local administrative area
    LOCALITY = "locality"  # City/Town
    BOROUGH = "borough"  # Borough/Ward

    # Neighborhood levels
    MACROHOOD = "macrohood"  # Large neighborhood grouping
    NEIGHBOURHOOD = "neighbourhood"  # Standard neighborhood
    MICROHOOD = "microhood"  # Small sub-neighborhood

    # Special types
    CAMPUS = "campus"  # University/corporate campus
    VENUE = "venue"
    BUILDING = "building"
    ADDRESS = "address"
    CUSTOM = "custom"

    # Natural features
    OCEAN = "ocean"
    MARINEAREA = "marinearea"

    @classmethod
    def get_hierarchy_level(cls, placetype: PlacetypeLike) -> int:
        """Get hierarchical level of placetype (lower = higher in hierarchy)."""
        hierarchy = {
            "planet": 0,
            "continent": 1,
            "empire": 2,
            "country": 3,
            "disputed": 3,
            "dependency": 3,
            "macroregion": 4,
            "region": 5,
            "macrocounty": 6,
            "county": 7,
            "localadmin": 8,
            "locality": 9,
            "borough": 10,
            "macrohood": 11,
            "neighbourhood": 12,
            "microhood": 13,
            "campus": 14,
            "venue": 15,
            "building": 16,
            "address": 17,
            "custom": 99,
            "ocean": 100,
            "marinearea": 101,
        }
        key = normalize_placetype(placetype)
        return hierarchy.get(key, 999)

    @classmethod
    def is_admin_level(cls, placetype: PlacetypeLike) -> bool:
        """Check if placetype is administrative level."""
        admin_types = {
            cls.COUNTRY.value,
            cls.REGION.value,
            cls.COUNTY.value,
            cls.LOCALADMIN.value,
            cls.LOCALITY.value,
            cls.BOROUGH.value,
        }
        return normalize_placetype(placetype) in admin_types

    @classmethod
    def is_neighborhood_type(cls, placetype: PlacetypeLike) -> bool:
        """Check if placetype is neighborhood level."""
        neighborhood_types = {
            cls.MACROHOOD.value,
            cls.NEIGHBOURHOOD.value,
            cls.MICROHOOD.value,
        }
        return normalize_placetype(placetype) in neighborhood_types

    @classmethod
    def is_venue_type(cls, placetype: PlacetypeLike) -> bool:
        """Check if placetype is venue/building level."""
        venue_types = {
            cls.VENUE.value,
            cls.BUILDING.value,
            cls.ADDRESS.value,
        }
        return normalize_placetype(placetype) in venue_types

    @classmethod
    def is_natural_feature(cls, placetype: PlacetypeLike) -> bool:
        """Check if placetype is natural feature."""
        natural_types = {
            cls.OCEAN.value,
            cls.MARINEAREA.value,
        }
        return normalize_placetype(placetype) in natural_types

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"PlaceType('{self.value}')"


class PlaceStatus(str, Enum):
    """Place lifecycle status."""

    CURRENT = "current"
    DEPRECATED = "deprecated"
    CEASED = "ceased"
    SUPERSEDED = "superseded"
    SUPERSEDING = "superseding"


class CountryDatabase(str, Enum):
    """Supported country databases with their ISO codes."""

    CANADA = "CA"
    UNITED_STATES = "US"

    @classmethod
    def from_filename(cls, filename: str) -> Optional["CountryDatabase"]:
        """Determine country from database filename."""
        filename_lower = filename.lower()
        if "canada" in filename_lower or "ca.db" in filename_lower:
            return cls.CANADA
        elif (
            "usa" in filename_lower
            or "us.db" in filename_lower
            or "united" in filename_lower
        ):
            return cls.UNITED_STATES
        return None

    @classmethod
    def get_country_codes(cls, country: "CountryDatabase") -> List[str]:
        """Get all country codes for a country database."""
        # Support both 2-letter and 3-letter codes
        if country == cls.CANADA:
            return ["CA", "CAN"]
        elif country == cls.UNITED_STATES:
            return ["US", "USA"]
        return []


class DataQuality(str, Enum):
    """Data quality tiers."""

    COMPLETE = "complete"  # All fields present
    GOOD = "good"  # Core fields + some optional
    BASIC = "basic"  # Core fields only
    MINIMAL = "minimal"  # Missing core fields


class GeometryPrecision(str, Enum):
    """Geometry precision levels."""

    EXACT = "exact"  # Full precision geometry
    SIMPLIFIED = "simplified"  # Reduced point count
    BBOX = "bbox"  # Bounding box only
    POINT = "point"  # Centroid only
    NONE = "none"  # No geometry


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
    KOREAN = "kor"
    DUTCH = "nld"
    POLISH = "pol"
    TURKISH = "tur"

    @classmethod
    def get_x_codes(cls) -> List[str]:
        """Get preferred/default language codes."""
        return ["eng_x_preferred", "eng_x_variant", "eng_x_colloquial"]

    @classmethod
    def is_preferred(cls, lang_code: str) -> bool:
        """Check if language code indicates preferred name."""
        return "_x_preferred" in lang_code


# Search Options
SortOrder = Literal["asc", "desc"]
SortField = Literal["name", "placetype", "population", "area", "lastmodified"]
OutputFormat = Literal["geojson", "csv", "wkt", "json", "summary"]

# Expansion Options
ExpansionType = Literal["ancestors", "descendants", "children", "siblings"]
ExpansionDepth = Union[int, Literal["all"]]

# Filter Operators
FilterOperator = Literal[
    "eq", "ne", "gt", "gte", "lt", "lte", "in", "nin", "like", "ilike"
]
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

# Coordinate bounds
MIN_LONGITUDE = -180.0
MAX_LONGITUDE = 180.0
MIN_LATITUDE = -90.0
MAX_LATITUDE = 90.0


# Type Guards
def is_valid_placetype(value: PlacetypeLike) -> bool:
    """Check if value is valid placetype."""
    try:
        coerce_placetype(value)
        return True
    except ValueError:
        return False


def is_valid_bbox(value: Any) -> bool:
    """Check if value is valid bounding box."""
    return (
        isinstance(value, (list, tuple))
        and len(value) == 4
        and all(isinstance(v, (int, float)) for v in value)
        and MIN_LONGITUDE <= value[0] <= MAX_LONGITUDE  # min_lon
        and MIN_LATITUDE <= value[1] <= MAX_LATITUDE  # min_lat
        and MIN_LONGITUDE <= value[2] <= MAX_LONGITUDE  # max_lon
        and MIN_LATITUDE <= value[3] <= MAX_LATITUDE  # max_lat
        and value[0] <= value[2]  # min_lon <= max_lon
        and value[1] <= value[3]  # min_lat <= max_lat
    )


def is_valid_coordinate(value: Any) -> bool:
    """Check if value is valid coordinate."""
    return (
        isinstance(value, (list, tuple))
        and len(value) == 2
        and all(isinstance(v, (int, float)) for v in value)
        and MIN_LONGITUDE <= value[0] <= MAX_LONGITUDE  # longitude
        and MIN_LATITUDE <= value[1] <= MAX_LATITUDE  # latitude
    )


def is_valid_place_id(value: Any) -> bool:
    """Check if value is valid place ID."""
    return isinstance(value, int) and value > 0


def normalize_placetype(value: PlacetypeLike) -> str:
    """Normalize placetype string to standard form."""
    # Handle common variations
    replacements = {
        "neighborhood": "neighbourhood",
        "macro-hood": "macrohood",
        "micro-hood": "microhood",
        "local-admin": "localadmin",
        "marine-area": "marinearea",
    }
    if isinstance(value, PlaceType):
        return value.value
    normalized = value.lower().strip()
    return replacements.get(normalized, normalized)


def coerce_placetype(value: PlacetypeLike) -> PlaceType:
    """Convert arbitrary placetype input to PlaceType enum."""
    if isinstance(value, PlaceType):
        return value

    normalized = normalize_placetype(value)
    return PlaceType(normalized)


# Export all public items
__all__ = [
    # Type aliases
    "Longitude",
    "Latitude",
    "Coordinate",
    "BBox",
    "PlaceID",
    "ParentID",
    "AncestorID",
    "GeometryType",
    "GeoJSONGeometry",
    "DatabasePath",
    "DatabaseAlias",
    "SourceIdentifier",
    "PlacetypeLike",
    # Enums
    "PlaceType",
    "PlaceStatus",
    "DataQuality",
    "GeometryPrecision",
    "NameLanguage",
    # Literals
    "SortOrder",
    "SortField",
    "OutputFormat",
    "ExpansionType",
    "ExpansionDepth",
    "FilterOperator",
    "LogicalOperator",
    "ResultFormat",
    "CursorState",
    # Constants
    "DEFAULT_BATCH_SIZE",
    "MAX_BATCH_SIZE",
    "DEFAULT_SEARCH_LIMIT",
    "MAX_SEARCH_LIMIT",
    "DEFAULT_EXPANSION_DEPTH",
    "MAX_EXPANSION_DEPTH",
    "MIN_LONGITUDE",
    "MAX_LONGITUDE",
    "MIN_LATITUDE",
    "MAX_LATITUDE",
    # Type guards
    "is_valid_placetype",
    "is_valid_bbox",
    "is_valid_coordinate",
    "is_valid_place_id",
    "normalize_placetype",
    "coerce_placetype",
]
