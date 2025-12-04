"""
Geometry-specific models for WOF places.
"""

from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field, model_validator
from wof_explorer.types import BBox, Coordinate


class WOFGeometry(BaseModel):
    """Geometry information for a place."""

    type: str  # GeometryType
    coordinates: Union[List, List[List], List[List[List]]]
    precision: str = "exact"  # GeometryPrecision

    @model_validator(mode="after")
    def validate_coordinates(self):
        """Validate coordinates match geometry type."""
        v = self.coordinates
        geom_type = self.type
        if geom_type == "Point":
            if not isinstance(v, list) or len(v) != 2:
                raise ValueError("Point must have [lon, lat] coordinates")
        elif geom_type == "Polygon":
            if not isinstance(v, list) or not all(isinstance(ring, list) for ring in v):
                raise ValueError("Polygon must have list of rings")
        elif geom_type == "MultiPolygon":
            if not isinstance(v, list) or not all(isinstance(poly, list) for poly in v):
                raise ValueError("MultiPolygon must have list of polygons")
        return self

    def to_geojson(self) -> Dict[str, Any]:
        """Convert to GeoJSON geometry."""
        return {"type": self.type, "coordinates": self.coordinates}

    def to_wkt(self) -> str:
        """Convert to Well-Known Text."""
        if self.type == "Point":
            return f"POINT({self.coordinates[0]} {self.coordinates[1]})"
        elif self.type == "Polygon":
            return self._polygon_to_wkt(self.coordinates)
        elif self.type == "MultiPolygon":
            return self._multipolygon_to_wkt(self.coordinates)
        elif self.type == "LineString":
            return self._linestring_to_wkt(self.coordinates)
        elif self.type == "MultiLineString":
            return self._multilinestring_to_wkt(self.coordinates)
        else:
            return f"{self.type.upper()} EMPTY"

    def _polygon_to_wkt(self, coords: List) -> str:
        """Convert polygon coordinates to WKT."""
        rings = []
        for ring in coords:
            points = [f"{x} {y}" for x, y in ring]
            rings.append(f"({','.join(points)})")
        return f"POLYGON({','.join(rings)})"

    def _multipolygon_to_wkt(self, coords: List) -> str:
        """Convert multipolygon coordinates to WKT."""
        polygons = []
        for polygon in coords:
            rings = []
            for ring in polygon:
                points = [f"{x} {y}" for x, y in ring]
                rings.append(f"({','.join(points)})")
            polygons.append(f"({','.join(rings)})")
        return f"MULTIPOLYGON({','.join(polygons)})"

    def _linestring_to_wkt(self, coords: List) -> str:
        """Convert linestring coordinates to WKT."""
        points = [f"{x} {y}" for x, y in coords]
        return f"LINESTRING({','.join(points)})"

    def _multilinestring_to_wkt(self, coords: List) -> str:
        """Convert multilinestring coordinates to WKT."""
        lines = []
        for line in coords:
            points = [f"{x} {y}" for x, y in line]
            lines.append(f"({','.join(points)})")
        return f"MULTILINESTRING({','.join(lines)})"

    def simplify(self, tolerance: float = 0.001) -> "WOFGeometry":
        """Simplify geometry to reduce complexity (placeholder)."""
        # In a real implementation, this would use a simplification algorithm
        # like Douglas-Peucker
        return WOFGeometry(
            type=self.type,
            coordinates=self.coordinates,  # Would be simplified
            precision="simplified",
        )

    def get_type(self) -> str:
        """Get geometry type."""
        return self.type

    def is_point(self) -> bool:
        """Check if geometry is a point."""
        return self.type == "Point"

    def is_polygon(self) -> bool:
        """Check if geometry is a polygon."""
        return self.type in ["Polygon", "MultiPolygon"]

    def is_line(self) -> bool:
        """Check if geometry is a line."""
        return self.type in ["LineString", "MultiLineString"]


class WOFBounds(BaseModel):
    """Bounding box for a place."""

    min_lon: float = Field(..., ge=-180, le=180)
    min_lat: float = Field(..., ge=-90, le=90)
    max_lon: float = Field(..., ge=-180, le=180)
    max_lat: float = Field(..., ge=-90, le=90)

    @model_validator(mode="after")
    def validate_bbox_order(self):
        """Ensure max values >= min values."""
        if self.max_lon < self.min_lon:
            # Allow wrapping around dateline
            if not (self.min_lon > 0 and self.max_lon < 0):
                raise ValueError("max_lon must be >= min_lon")
        if self.max_lat < self.min_lat:
            raise ValueError("max_lat must be >= min_lat")
        return self

    def to_tuple(self) -> BBox:
        """Convert to tuple format."""
        return (self.min_lon, self.min_lat, self.max_lon, self.max_lat)

    def to_list(self) -> List[float]:
        """Convert to list format."""
        return [self.min_lon, self.min_lat, self.max_lon, self.max_lat]

    def contains_point(self, lon: float, lat: float) -> bool:
        """Check if point is within bounds."""
        # Handle dateline crossing
        if self.min_lon > self.max_lon:
            # Wraps around dateline
            return self.min_lat <= lat <= self.max_lat and (
                lon >= self.min_lon or lon <= self.max_lon
            )
        else:
            return (
                self.min_lon <= lon <= self.max_lon
                and self.min_lat <= lat <= self.max_lat
            )

    def contains_bounds(self, other: "WOFBounds") -> bool:
        """Check if this bounds completely contains another."""
        return self.contains_point(
            other.min_lon, other.min_lat
        ) and self.contains_point(other.max_lon, other.max_lat)

    def intersects(self, other: "WOFBounds") -> bool:
        """Check if bounds intersect."""
        # Handle dateline crossing
        if self.min_lon > self.max_lon or other.min_lon > other.max_lon:
            # Complex dateline logic - simplified version
            return True  # Would need proper implementation

        return not (
            self.max_lon < other.min_lon
            or self.min_lon > other.max_lon
            or self.max_lat < other.min_lat
            or self.min_lat > other.max_lat
        )

    def union(self, other: "WOFBounds") -> "WOFBounds":
        """Create union of two bounds."""
        return WOFBounds(
            min_lon=min(self.min_lon, other.min_lon),
            min_lat=min(self.min_lat, other.min_lat),
            max_lon=max(self.max_lon, other.max_lon),
            max_lat=max(self.max_lat, other.max_lat),
        )

    def intersection(self, other: "WOFBounds") -> Optional["WOFBounds"]:
        """Create intersection of two bounds."""
        if not self.intersects(other):
            return None

        return WOFBounds(
            min_lon=max(self.min_lon, other.min_lon),
            min_lat=max(self.min_lat, other.min_lat),
            max_lon=min(self.max_lon, other.max_lon),
            max_lat=min(self.max_lat, other.max_lat),
        )

    def get_center(self) -> Coordinate:
        """Get center point of bounds."""
        # Handle dateline crossing
        if self.min_lon > self.max_lon:
            # Wraps around dateline
            lon = ((self.min_lon + self.max_lon + 360) / 2) % 360
            if lon > 180:
                lon -= 360
        else:
            lon = (self.min_lon + self.max_lon) / 2

        lat = (self.min_lat + self.max_lat) / 2
        return (lon, lat)

    def get_area_degrees(self) -> float:
        """Get area in square degrees."""
        width = self.max_lon - self.min_lon
        if width < 0:  # Crosses dateline
            width += 360
        height = self.max_lat - self.min_lat
        return width * height

    def get_width(self) -> float:
        """Get width in degrees."""
        width = self.max_lon - self.min_lon
        if width < 0:  # Crosses dateline
            width += 360
        return width

    def get_height(self) -> float:
        """Get height in degrees."""
        return self.max_lat - self.min_lat

    def expand(self, degrees: float) -> "WOFBounds":
        """Expand bounds by specified degrees."""
        return WOFBounds(
            min_lon=max(-180, self.min_lon - degrees),
            min_lat=max(-90, self.min_lat - degrees),
            max_lon=min(180, self.max_lon + degrees),
            max_lat=min(90, self.max_lat + degrees),
        )

    def to_polygon_coords(self) -> List[List[Coordinate]]:
        """Convert bounds to polygon coordinates."""
        return [
            [
                (self.min_lon, self.min_lat),
                (self.max_lon, self.min_lat),
                (self.max_lon, self.max_lat),
                (self.min_lon, self.max_lat),
                (self.min_lon, self.min_lat),  # Close the ring
            ]
        ]


class WOFCentroid(BaseModel):
    """Centroid point for a place."""

    lon: float = Field(..., ge=-180, le=180)
    lat: float = Field(..., ge=-90, le=90)
    source: str = Field(
        "calculated", description="Source of centroid: calculated, label, or geometric"
    )

    def to_tuple(self) -> Coordinate:
        """Convert to coordinate tuple."""
        return (self.lon, self.lat)

    def to_list(self) -> List[float]:
        """Convert to coordinate list."""
        return [self.lon, self.lat]

    def to_point_geometry(self) -> WOFGeometry:
        """Convert to Point geometry."""
        return WOFGeometry(
            type="Point", coordinates=[self.lon, self.lat], precision="point"
        )

    def distance_to(self, other: "WOFCentroid") -> float:
        """Calculate distance to another centroid (degrees)."""
        import math

        return math.sqrt((self.lon - other.lon) ** 2 + (self.lat - other.lat) ** 2)

    def haversine_distance_to(self, other: "WOFCentroid") -> float:
        """Calculate haversine distance to another centroid (km)."""
        import math

        R = 6371  # Earth's radius in kilometers

        lat1, lon1 = math.radians(self.lat), math.radians(self.lon)
        lat2, lon2 = math.radians(other.lat), math.radians(other.lon)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        return R * c

    def is_label_point(self) -> bool:
        """Check if centroid is a label point."""
        return self.source == "label"

    def is_calculated(self) -> bool:
        """Check if centroid is calculated."""
        return self.source == "calculated"


class GeometryCollection(BaseModel):
    """Collection of geometries."""

    geometries: List[WOFGeometry]
    bbox: Optional[WOFBounds] = None

    def get_types(self) -> List[str]:
        """Get list of geometry types."""
        return [g.type for g in self.geometries]

    def filter_by_type(self, geom_type: str) -> List[WOFGeometry]:
        """Filter geometries by type."""
        return [g for g in self.geometries if g.type == geom_type]

    def get_points(self) -> List[WOFGeometry]:
        """Get all point geometries."""
        return self.filter_by_type("Point")

    def get_polygons(self) -> List[WOFGeometry]:
        """Get all polygon geometries."""
        return [g for g in self.geometries if g.is_polygon()]

    def get_lines(self) -> List[WOFGeometry]:
        """Get all line geometries."""
        return [g for g in self.geometries if g.is_line()]

    def calculate_bbox(self) -> Optional[WOFBounds]:
        """Calculate bounding box for all geometries."""
        if not self.geometries:
            return None

        # This would need proper implementation to extract bounds from each geometry
        # For now, return stored bbox
        return self.bbox

    def to_geojson(self) -> Dict[str, Any]:
        """Convert to GeoJSON GeometryCollection."""
        return {
            "type": "GeometryCollection",
            "geometries": [g.to_geojson() for g in self.geometries],
        }


class SpatialReference(BaseModel):
    """Spatial reference system information."""

    srid: int = Field(4326, description="Spatial Reference ID (default WGS84)")
    proj4: Optional[str] = None
    name: str = "WGS84"

    def is_wgs84(self) -> bool:
        """Check if using WGS84."""
        return self.srid == 4326

    def is_web_mercator(self) -> bool:
        """Check if using Web Mercator."""
        return self.srid == 3857


# Export all public items
__all__ = [
    "WOFGeometry",
    "WOFBounds",
    "WOFCentroid",
    "GeometryCollection",
    "SpatialReference",
]
