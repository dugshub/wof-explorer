"""
Unit tests for WOF geometry models.

Tests verify geometry construction, parsing, and serialization.
"""

import pytest
import math
from typing import List, Dict, Any
from wof_explorer.models.geometry import (
    WOFGeometry,
    WOFBounds,
    WOFCentroid,
    GeometryCollection,
    SpatialReference,
)
from wof_explorer.types import Coordinate, BBox


# Sample test geometries (Barbados coordinates)
BARBADOS_CENTROID: Coordinate = (-59.6166, 13.0969)
SAMPLE_POINT_COORDS: List[float] = [-59.6166, 13.0969]
SAMPLE_POINT_GEOJSON = {"type": "Point", "coordinates": SAMPLE_POINT_COORDS}

SAMPLE_POLYGON_COORDS = [
    [
        [-59.7, 13.0],
        [-59.4, 13.0],
        [-59.4, 13.4],
        [-59.7, 13.4],
        [-59.7, 13.0],  # Closed ring
    ]
]
SAMPLE_POLYGON_GEOJSON = {"type": "Polygon", "coordinates": SAMPLE_POLYGON_COORDS}

SAMPLE_MULTIPOLYGON_COORDS = [
    [
        [
            [-59.7, 13.0],
            [-59.6, 13.0],
            [-59.6, 13.2],
            [-59.7, 13.2],
            [-59.7, 13.0],
        ]
    ],
    [
        [
            [-59.5, 13.2],
            [-59.4, 13.2],
            [-59.4, 13.4],
            [-59.5, 13.4],
            [-59.5, 13.2],
        ]
    ],
]
SAMPLE_MULTIPOLYGON_GEOJSON = {
    "type": "MultiPolygon",
    "coordinates": SAMPLE_MULTIPOLYGON_COORDS,
}

SAMPLE_LINESTRING_COORDS = [
    [-59.7, 13.0],
    [-59.6, 13.1],
    [-59.5, 13.2],
    [-59.4, 13.3],
]
SAMPLE_LINESTRING_GEOJSON = {
    "type": "LineString",
    "coordinates": SAMPLE_LINESTRING_COORDS,
}

SAMPLE_MULTILINESTRING_COORDS = [
    [
        [-59.7, 13.0],
        [-59.6, 13.1],
    ],
    [
        [-59.5, 13.2],
        [-59.4, 13.3],
    ],
]
SAMPLE_MULTILINESTRING_GEOJSON = {
    "type": "MultiLineString",
    "coordinates": SAMPLE_MULTILINESTRING_COORDS,
}


class TestWOFGeometry:
    """Tests for WOFGeometry construction and validation."""

    @pytest.mark.unit
    def test_point_geometry_construction(self):
        """Point geometry should construct with valid coordinates."""
        geometry = WOFGeometry(type="Point", coordinates=SAMPLE_POINT_COORDS)

        assert geometry.type == "Point"
        assert geometry.coordinates == SAMPLE_POINT_COORDS
        assert geometry.precision == "exact"

    @pytest.mark.unit
    def test_polygon_geometry_construction(self):
        """Polygon geometry should construct with valid coordinate rings."""
        geometry = WOFGeometry(type="Polygon", coordinates=SAMPLE_POLYGON_COORDS)

        assert geometry.type == "Polygon"
        assert geometry.coordinates == SAMPLE_POLYGON_COORDS
        assert len(geometry.coordinates) == 1  # One ring
        assert len(geometry.coordinates[0]) == 5  # Closed ring

    @pytest.mark.unit
    def test_multipolygon_geometry_construction(self):
        """MultiPolygon geometry should construct with multiple polygons."""
        geometry = WOFGeometry(
            type="MultiPolygon", coordinates=SAMPLE_MULTIPOLYGON_COORDS
        )

        assert geometry.type == "MultiPolygon"
        assert len(geometry.coordinates) == 2  # Two polygons

    @pytest.mark.unit
    def test_linestring_geometry_construction(self):
        """LineString geometry should construct with coordinate array."""
        geometry = WOFGeometry(type="LineString", coordinates=SAMPLE_LINESTRING_COORDS)

        assert geometry.type == "LineString"
        assert geometry.coordinates == SAMPLE_LINESTRING_COORDS
        assert len(geometry.coordinates) == 4

    @pytest.mark.unit
    def test_multilinestring_geometry_construction(self):
        """MultiLineString geometry should construct with multiple lines."""
        geometry = WOFGeometry(
            type="MultiLineString", coordinates=SAMPLE_MULTILINESTRING_COORDS
        )

        assert geometry.type == "MultiLineString"
        assert len(geometry.coordinates) == 2

    @pytest.mark.unit
    def test_geometry_with_custom_precision(self):
        """Geometry should accept custom precision value."""
        geometry = WOFGeometry(
            type="Point", coordinates=SAMPLE_POINT_COORDS, precision="simplified"
        )

        assert geometry.precision == "simplified"

    @pytest.mark.unit
    def test_invalid_point_coordinates_raises_error(self):
        """Point with invalid coordinates should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            WOFGeometry(type="Point", coordinates=[-59.6])  # Missing latitude

        assert "Point must have [lon, lat]" in str(exc_info.value)

    @pytest.mark.unit
    def test_invalid_polygon_coordinates_raises_error(self):
        """Polygon with invalid coordinates should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            WOFGeometry(type="Polygon", coordinates=[-59.6, 13.0])  # Not a list of rings

        assert "Polygon must have list of rings" in str(exc_info.value)

    @pytest.mark.unit
    def test_invalid_multipolygon_coordinates_raises_error(self):
        """MultiPolygon with invalid coordinates should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            WOFGeometry(
                type="MultiPolygon", coordinates=[-59.6, 13.0]
            )  # Not a list at all

        assert "MultiPolygon must have list of polygons" in str(exc_info.value)


class TestGeometryParsing:
    """Tests for parsing geometry from various formats."""

    @pytest.mark.unit
    def test_parse_from_geojson_dict(self):
        """Geometry should parse from GeoJSON-like dictionary."""
        geometry = WOFGeometry(**SAMPLE_POINT_GEOJSON)

        assert geometry.type == "Point"
        assert geometry.coordinates == SAMPLE_POINT_COORDS

    @pytest.mark.unit
    def test_parse_polygon_from_geojson(self):
        """Polygon should parse from GeoJSON format."""
        geometry = WOFGeometry(**SAMPLE_POLYGON_GEOJSON)

        assert geometry.type == "Polygon"
        assert geometry.coordinates == SAMPLE_POLYGON_COORDS

    @pytest.mark.unit
    def test_parse_multipolygon_from_geojson(self):
        """MultiPolygon should parse from GeoJSON format."""
        geometry = WOFGeometry(**SAMPLE_MULTIPOLYGON_GEOJSON)

        assert geometry.type == "MultiPolygon"
        assert len(geometry.coordinates) == 2


class TestGeometrySerialization:
    """Tests for geometry serialization to GeoJSON and WKT."""

    @pytest.mark.unit
    def test_point_to_geojson(self):
        """Point geometry should serialize to GeoJSON."""
        geometry = WOFGeometry(type="Point", coordinates=SAMPLE_POINT_COORDS)
        geojson = geometry.to_geojson()

        assert geojson["type"] == "Point"
        assert geojson["coordinates"] == SAMPLE_POINT_COORDS

    @pytest.mark.unit
    def test_polygon_to_geojson(self):
        """Polygon geometry should serialize to GeoJSON."""
        geometry = WOFGeometry(type="Polygon", coordinates=SAMPLE_POLYGON_COORDS)
        geojson = geometry.to_geojson()

        assert geojson["type"] == "Polygon"
        assert geojson["coordinates"] == SAMPLE_POLYGON_COORDS

    @pytest.mark.unit
    def test_point_to_wkt(self):
        """Point geometry should serialize to WKT format."""
        geometry = WOFGeometry(type="Point", coordinates=SAMPLE_POINT_COORDS)
        wkt = geometry.to_wkt()

        assert wkt == "POINT(-59.6166 13.0969)"

    @pytest.mark.unit
    def test_polygon_to_wkt(self):
        """Polygon geometry should serialize to WKT format."""
        geometry = WOFGeometry(type="Polygon", coordinates=SAMPLE_POLYGON_COORDS)
        wkt = geometry.to_wkt()

        assert wkt.startswith("POLYGON(")
        assert "-59.7 13.0" in wkt
        assert "-59.4 13.4" in wkt

    @pytest.mark.unit
    def test_multipolygon_to_wkt(self):
        """MultiPolygon geometry should serialize to WKT format."""
        geometry = WOFGeometry(
            type="MultiPolygon", coordinates=SAMPLE_MULTIPOLYGON_COORDS
        )
        wkt = geometry.to_wkt()

        assert wkt.startswith("MULTIPOLYGON(")
        assert wkt.count("((") == 2  # Two polygons

    @pytest.mark.unit
    def test_linestring_to_wkt(self):
        """LineString geometry should serialize to WKT format."""
        geometry = WOFGeometry(type="LineString", coordinates=SAMPLE_LINESTRING_COORDS)
        wkt = geometry.to_wkt()

        assert wkt.startswith("LINESTRING(")
        assert "-59.7 13.0" in wkt

    @pytest.mark.unit
    def test_multilinestring_to_wkt(self):
        """MultiLineString geometry should serialize to WKT format."""
        geometry = WOFGeometry(
            type="MultiLineString", coordinates=SAMPLE_MULTILINESTRING_COORDS
        )
        wkt = geometry.to_wkt()

        assert wkt.startswith("MULTILINESTRING(")

    @pytest.mark.unit
    def test_unknown_geometry_type_to_wkt(self):
        """Unknown geometry type should return EMPTY WKT."""
        geometry = WOFGeometry(type="UnknownType", coordinates=[])
        wkt = geometry.to_wkt()

        assert wkt == "UNKNOWNTYPE EMPTY"


class TestGeometryTypeChecks:
    """Tests for geometry type checking methods."""

    @pytest.mark.unit
    def test_get_type_returns_geometry_type(self):
        """get_type() should return the geometry type."""
        geometry = WOFGeometry(type="Point", coordinates=SAMPLE_POINT_COORDS)

        assert geometry.get_type() == "Point"

    @pytest.mark.unit
    def test_is_point_for_point_geometry(self):
        """is_point() should return True for Point geometry."""
        geometry = WOFGeometry(type="Point", coordinates=SAMPLE_POINT_COORDS)

        assert geometry.is_point() is True

    @pytest.mark.unit
    def test_is_point_for_polygon_geometry(self):
        """is_point() should return False for non-Point geometry."""
        geometry = WOFGeometry(type="Polygon", coordinates=SAMPLE_POLYGON_COORDS)

        assert geometry.is_point() is False

    @pytest.mark.unit
    def test_is_polygon_for_polygon_geometry(self):
        """is_polygon() should return True for Polygon."""
        geometry = WOFGeometry(type="Polygon", coordinates=SAMPLE_POLYGON_COORDS)

        assert geometry.is_polygon() is True

    @pytest.mark.unit
    def test_is_polygon_for_multipolygon_geometry(self):
        """is_polygon() should return True for MultiPolygon."""
        geometry = WOFGeometry(
            type="MultiPolygon", coordinates=SAMPLE_MULTIPOLYGON_COORDS
        )

        assert geometry.is_polygon() is True

    @pytest.mark.unit
    def test_is_line_for_linestring_geometry(self):
        """is_line() should return True for LineString."""
        geometry = WOFGeometry(type="LineString", coordinates=SAMPLE_LINESTRING_COORDS)

        assert geometry.is_line() is True

    @pytest.mark.unit
    def test_is_line_for_multilinestring_geometry(self):
        """is_line() should return True for MultiLineString."""
        geometry = WOFGeometry(
            type="MultiLineString", coordinates=SAMPLE_MULTILINESTRING_COORDS
        )

        assert geometry.is_line() is True


class TestGeometrySimplification:
    """Tests for geometry simplification."""

    @pytest.mark.unit
    def test_simplify_returns_geometry_with_simplified_precision(self):
        """simplify() should return geometry with simplified precision."""
        geometry = WOFGeometry(type="Polygon", coordinates=SAMPLE_POLYGON_COORDS)
        simplified = geometry.simplify(tolerance=0.001)

        assert isinstance(simplified, WOFGeometry)
        assert simplified.precision == "simplified"
        assert simplified.type == geometry.type

    @pytest.mark.unit
    def test_simplify_with_custom_tolerance(self):
        """simplify() should accept custom tolerance parameter."""
        geometry = WOFGeometry(type="Polygon", coordinates=SAMPLE_POLYGON_COORDS)
        simplified = geometry.simplify(tolerance=0.01)

        assert simplified.precision == "simplified"


class TestWOFBounds:
    """Tests for WOFBounds bounding box."""

    @pytest.mark.unit
    def test_bounds_construction(self):
        """Bounds should construct with valid coordinates."""
        bounds = WOFBounds(min_lon=-59.7, min_lat=13.0, max_lon=-59.4, max_lat=13.4)

        assert bounds.min_lon == -59.7
        assert bounds.min_lat == 13.0
        assert bounds.max_lon == -59.4
        assert bounds.max_lat == 13.4

    @pytest.mark.unit
    def test_bounds_to_tuple(self):
        """Bounds should convert to tuple format."""
        bounds = WOFBounds(min_lon=-59.7, min_lat=13.0, max_lon=-59.4, max_lat=13.4)
        bbox: BBox = bounds.to_tuple()

        assert bbox == (-59.7, 13.0, -59.4, 13.4)

    @pytest.mark.unit
    def test_bounds_to_list(self):
        """Bounds should convert to list format."""
        bounds = WOFBounds(min_lon=-59.7, min_lat=13.0, max_lon=-59.4, max_lat=13.4)
        bbox_list = bounds.to_list()

        assert bbox_list == [-59.7, 13.0, -59.4, 13.4]

    @pytest.mark.unit
    def test_invalid_longitude_raises_error(self):
        """Bounds with invalid longitude should raise ValueError."""
        with pytest.raises(ValueError):
            WOFBounds(min_lon=-200.0, min_lat=13.0, max_lon=-59.4, max_lat=13.4)

    @pytest.mark.unit
    def test_invalid_latitude_raises_error(self):
        """Bounds with invalid latitude should raise ValueError."""
        with pytest.raises(ValueError):
            WOFBounds(min_lon=-59.7, min_lat=-100.0, max_lon=-59.4, max_lat=13.4)

    @pytest.mark.unit
    def test_max_less_than_min_raises_error(self):
        """Bounds with max < min should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            WOFBounds(min_lon=-59.4, min_lat=13.0, max_lon=-59.7, max_lat=13.4)

        assert "max_lon must be >= min_lon" in str(exc_info.value)

    @pytest.mark.unit
    def test_max_lat_less_than_min_lat_raises_error(self):
        """Bounds with max_lat < min_lat should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            WOFBounds(min_lon=-59.7, min_lat=13.4, max_lon=-59.4, max_lat=13.0)

        assert "max_lat must be >= min_lat" in str(exc_info.value)

    @pytest.mark.unit
    def test_bounds_contains_point_inside(self):
        """contains_point() should return True for point inside bounds."""
        bounds = WOFBounds(min_lon=-59.7, min_lat=13.0, max_lon=-59.4, max_lat=13.4)

        assert bounds.contains_point(-59.5, 13.2) is True

    @pytest.mark.unit
    def test_bounds_contains_point_outside(self):
        """contains_point() should return False for point outside bounds."""
        bounds = WOFBounds(min_lon=-59.7, min_lat=13.0, max_lon=-59.4, max_lat=13.4)

        assert bounds.contains_point(-60.0, 13.2) is False
        assert bounds.contains_point(-59.5, 14.0) is False

    @pytest.mark.unit
    def test_bounds_contains_point_on_edge(self):
        """contains_point() should return True for point on edge."""
        bounds = WOFBounds(min_lon=-59.7, min_lat=13.0, max_lon=-59.4, max_lat=13.4)

        assert bounds.contains_point(-59.7, 13.0) is True
        assert bounds.contains_point(-59.4, 13.4) is True

    @pytest.mark.unit
    def test_bounds_contains_bounds_fully_inside(self):
        """contains_bounds() should return True for bounds fully inside."""
        outer = WOFBounds(min_lon=-60.0, min_lat=12.0, max_lon=-59.0, max_lat=14.0)
        inner = WOFBounds(min_lon=-59.7, min_lat=13.0, max_lon=-59.4, max_lat=13.4)

        assert outer.contains_bounds(inner) is True

    @pytest.mark.unit
    def test_bounds_contains_bounds_partially_outside(self):
        """contains_bounds() should return False for partially overlapping bounds."""
        bounds1 = WOFBounds(min_lon=-59.7, min_lat=13.0, max_lon=-59.4, max_lat=13.4)
        bounds2 = WOFBounds(min_lon=-59.5, min_lat=13.2, max_lon=-59.3, max_lat=13.6)

        assert bounds1.contains_bounds(bounds2) is False

    @pytest.mark.unit
    def test_bounds_intersects_overlapping(self):
        """intersects() should return True for overlapping bounds."""
        bounds1 = WOFBounds(min_lon=-59.7, min_lat=13.0, max_lon=-59.4, max_lat=13.4)
        bounds2 = WOFBounds(min_lon=-59.5, min_lat=13.2, max_lon=-59.3, max_lat=13.6)

        assert bounds1.intersects(bounds2) is True

    @pytest.mark.unit
    def test_bounds_intersects_non_overlapping(self):
        """intersects() should return False for non-overlapping bounds."""
        bounds1 = WOFBounds(min_lon=-59.7, min_lat=13.0, max_lon=-59.4, max_lat=13.4)
        bounds2 = WOFBounds(min_lon=-59.0, min_lat=13.5, max_lon=-58.5, max_lat=14.0)

        assert bounds1.intersects(bounds2) is False

    @pytest.mark.unit
    def test_bounds_union(self):
        """union() should create bounds containing both inputs."""
        bounds1 = WOFBounds(min_lon=-59.7, min_lat=13.0, max_lon=-59.4, max_lat=13.4)
        bounds2 = WOFBounds(min_lon=-59.5, min_lat=13.2, max_lon=-59.3, max_lat=13.6)
        union = bounds1.union(bounds2)

        assert union.min_lon == -59.7
        assert union.min_lat == 13.0
        assert union.max_lon == -59.3
        assert union.max_lat == 13.6

    @pytest.mark.unit
    def test_bounds_intersection_overlapping(self):
        """intersection() should return overlapping area."""
        bounds1 = WOFBounds(min_lon=-59.7, min_lat=13.0, max_lon=-59.4, max_lat=13.4)
        bounds2 = WOFBounds(min_lon=-59.5, min_lat=13.2, max_lon=-59.3, max_lat=13.6)
        intersection = bounds1.intersection(bounds2)

        assert intersection is not None
        assert intersection.min_lon == -59.5
        assert intersection.min_lat == 13.2
        assert intersection.max_lon == -59.4
        assert intersection.max_lat == 13.4

    @pytest.mark.unit
    def test_bounds_intersection_non_overlapping(self):
        """intersection() should return None for non-overlapping bounds."""
        bounds1 = WOFBounds(min_lon=-59.7, min_lat=13.0, max_lon=-59.4, max_lat=13.4)
        bounds2 = WOFBounds(min_lon=-59.0, min_lat=13.5, max_lon=-58.5, max_lat=14.0)
        intersection = bounds1.intersection(bounds2)

        assert intersection is None

    @pytest.mark.unit
    def test_get_center(self):
        """get_center() should return center point of bounds."""
        bounds = WOFBounds(min_lon=-60.0, min_lat=12.0, max_lon=-59.0, max_lat=14.0)
        center = bounds.get_center()

        assert center[0] == -59.5  # Longitude
        assert center[1] == 13.0  # Latitude

    @pytest.mark.unit
    def test_get_area_degrees(self):
        """get_area_degrees() should calculate area in square degrees."""
        bounds = WOFBounds(min_lon=-60.0, min_lat=12.0, max_lon=-59.0, max_lat=14.0)
        area = bounds.get_area_degrees()

        assert area == 2.0  # 1 degree width * 2 degrees height

    @pytest.mark.unit
    def test_get_width(self):
        """get_width() should return width in degrees."""
        bounds = WOFBounds(min_lon=-60.0, min_lat=12.0, max_lon=-59.0, max_lat=14.0)

        assert bounds.get_width() == 1.0

    @pytest.mark.unit
    def test_get_height(self):
        """get_height() should return height in degrees."""
        bounds = WOFBounds(min_lon=-60.0, min_lat=12.0, max_lon=-59.0, max_lat=14.0)

        assert bounds.get_height() == 2.0

    @pytest.mark.unit
    def test_expand_bounds(self):
        """expand() should increase bounds by specified degrees."""
        bounds = WOFBounds(min_lon=-59.7, min_lat=13.0, max_lon=-59.4, max_lat=13.4)
        expanded = bounds.expand(0.1)

        # Use approximate comparison for floating point
        assert abs(expanded.min_lon - (-59.8)) < 1e-10
        assert abs(expanded.min_lat - 12.9) < 1e-10
        assert abs(expanded.max_lon - (-59.3)) < 1e-10
        assert abs(expanded.max_lat - 13.5) < 1e-10

    @pytest.mark.unit
    def test_expand_bounds_respects_limits(self):
        """expand() should not exceed valid coordinate limits."""
        bounds = WOFBounds(min_lon=-179.0, min_lat=-89.0, max_lon=179.0, max_lat=89.0)
        expanded = bounds.expand(5.0)

        assert expanded.min_lon == -180.0
        assert expanded.min_lat == -90.0
        assert expanded.max_lon == 180.0
        assert expanded.max_lat == 90.0

    @pytest.mark.unit
    def test_to_polygon_coords(self):
        """to_polygon_coords() should return closed polygon ring."""
        bounds = WOFBounds(min_lon=-59.7, min_lat=13.0, max_lon=-59.4, max_lat=13.4)
        coords = bounds.to_polygon_coords()

        assert len(coords) == 1  # One ring
        assert len(coords[0]) == 5  # 5 points (closed)
        assert coords[0][0] == coords[0][4]  # First and last are same


class TestWOFCentroid:
    """Tests for WOFCentroid point."""

    @pytest.mark.unit
    def test_centroid_construction(self):
        """Centroid should construct with valid coordinates."""
        centroid = WOFCentroid(lon=-59.6166, lat=13.0969, source="calculated")

        assert centroid.lon == -59.6166
        assert centroid.lat == 13.0969
        assert centroid.source == "calculated"

    @pytest.mark.unit
    def test_centroid_default_source(self):
        """Centroid should default to 'calculated' source."""
        centroid = WOFCentroid(lon=-59.6166, lat=13.0969)

        assert centroid.source == "calculated"

    @pytest.mark.unit
    def test_centroid_to_tuple(self):
        """Centroid should convert to coordinate tuple."""
        centroid = WOFCentroid(lon=-59.6166, lat=13.0969)
        coord: Coordinate = centroid.to_tuple()

        assert coord == (-59.6166, 13.0969)

    @pytest.mark.unit
    def test_centroid_to_list(self):
        """Centroid should convert to coordinate list."""
        centroid = WOFCentroid(lon=-59.6166, lat=13.0969)
        coord_list = centroid.to_list()

        assert coord_list == [-59.6166, 13.0969]

    @pytest.mark.unit
    def test_centroid_to_point_geometry(self):
        """Centroid should convert to Point geometry."""
        centroid = WOFCentroid(lon=-59.6166, lat=13.0969)
        geometry = centroid.to_point_geometry()

        assert isinstance(geometry, WOFGeometry)
        assert geometry.type == "Point"
        assert geometry.coordinates == [-59.6166, 13.0969]
        assert geometry.precision == "point"

    @pytest.mark.unit
    def test_invalid_longitude_raises_error(self):
        """Centroid with invalid longitude should raise ValueError."""
        with pytest.raises(ValueError):
            WOFCentroid(lon=-200.0, lat=13.0969)

    @pytest.mark.unit
    def test_invalid_latitude_raises_error(self):
        """Centroid with invalid latitude should raise ValueError."""
        with pytest.raises(ValueError):
            WOFCentroid(lon=-59.6166, lat=100.0)

    @pytest.mark.unit
    def test_distance_to_same_point(self):
        """distance_to() should return 0 for same point."""
        centroid1 = WOFCentroid(lon=-59.6166, lat=13.0969)
        centroid2 = WOFCentroid(lon=-59.6166, lat=13.0969)

        distance = centroid1.distance_to(centroid2)
        assert distance == 0.0

    @pytest.mark.unit
    def test_distance_to_different_point(self):
        """distance_to() should calculate distance in degrees."""
        centroid1 = WOFCentroid(lon=-59.6166, lat=13.0969)
        centroid2 = WOFCentroid(lon=-59.5166, lat=13.1969)

        distance = centroid1.distance_to(centroid2)
        assert distance > 0
        # Should be approximately sqrt(0.1^2 + 0.1^2) = 0.141
        assert 0.14 < distance < 0.15

    @pytest.mark.unit
    def test_haversine_distance_to_same_point(self):
        """haversine_distance_to() should return 0 for same point."""
        centroid1 = WOFCentroid(lon=-59.6166, lat=13.0969)
        centroid2 = WOFCentroid(lon=-59.6166, lat=13.0969)

        distance = centroid1.haversine_distance_to(centroid2)
        assert distance == 0.0

    @pytest.mark.unit
    def test_haversine_distance_to_different_point(self):
        """haversine_distance_to() should calculate distance in kilometers."""
        centroid1 = WOFCentroid(lon=-59.6166, lat=13.0969)
        centroid2 = WOFCentroid(lon=-59.5166, lat=13.1969)

        distance = centroid1.haversine_distance_to(centroid2)
        assert distance > 0
        # Should be approximately 15-16 km
        assert 14 < distance < 17

    @pytest.mark.unit
    def test_is_label_point_for_label_source(self):
        """is_label_point() should return True for label source."""
        centroid = WOFCentroid(lon=-59.6166, lat=13.0969, source="label")

        assert centroid.is_label_point() is True

    @pytest.mark.unit
    def test_is_label_point_for_calculated_source(self):
        """is_label_point() should return False for calculated source."""
        centroid = WOFCentroid(lon=-59.6166, lat=13.0969, source="calculated")

        assert centroid.is_label_point() is False

    @pytest.mark.unit
    def test_is_calculated_for_calculated_source(self):
        """is_calculated() should return True for calculated source."""
        centroid = WOFCentroid(lon=-59.6166, lat=13.0969, source="calculated")

        assert centroid.is_calculated() is True

    @pytest.mark.unit
    def test_is_calculated_for_geometric_source(self):
        """is_calculated() should return False for non-calculated source."""
        centroid = WOFCentroid(lon=-59.6166, lat=13.0969, source="geometric")

        assert centroid.is_calculated() is False


class TestGeometryCollection:
    """Tests for GeometryCollection."""

    @pytest.mark.unit
    def test_collection_construction(self):
        """GeometryCollection should construct with list of geometries."""
        geom1 = WOFGeometry(type="Point", coordinates=SAMPLE_POINT_COORDS)
        geom2 = WOFGeometry(type="Polygon", coordinates=SAMPLE_POLYGON_COORDS)
        collection = GeometryCollection(geometries=[geom1, geom2])

        assert len(collection.geometries) == 2

    @pytest.mark.unit
    def test_collection_with_bbox(self):
        """GeometryCollection should accept optional bounding box."""
        geom = WOFGeometry(type="Point", coordinates=SAMPLE_POINT_COORDS)
        bbox = WOFBounds(min_lon=-60.0, min_lat=13.0, max_lon=-59.0, max_lat=14.0)
        collection = GeometryCollection(geometries=[geom], bbox=bbox)

        assert collection.bbox is not None
        assert collection.bbox.min_lon == -60.0

    @pytest.mark.unit
    def test_get_types(self):
        """get_types() should return list of geometry types."""
        geom1 = WOFGeometry(type="Point", coordinates=SAMPLE_POINT_COORDS)
        geom2 = WOFGeometry(type="Polygon", coordinates=SAMPLE_POLYGON_COORDS)
        geom3 = WOFGeometry(type="LineString", coordinates=SAMPLE_LINESTRING_COORDS)
        collection = GeometryCollection(geometries=[geom1, geom2, geom3])

        types = collection.get_types()
        assert types == ["Point", "Polygon", "LineString"]

    @pytest.mark.unit
    def test_filter_by_type(self):
        """filter_by_type() should return only matching geometries."""
        geom1 = WOFGeometry(type="Point", coordinates=SAMPLE_POINT_COORDS)
        geom2 = WOFGeometry(type="Polygon", coordinates=SAMPLE_POLYGON_COORDS)
        geom3 = WOFGeometry(type="Point", coordinates=[-59.5, 13.2])
        collection = GeometryCollection(geometries=[geom1, geom2, geom3])

        points = collection.filter_by_type("Point")
        assert len(points) == 2
        assert all(g.type == "Point" for g in points)

    @pytest.mark.unit
    def test_get_points(self):
        """get_points() should return all Point geometries."""
        geom1 = WOFGeometry(type="Point", coordinates=SAMPLE_POINT_COORDS)
        geom2 = WOFGeometry(type="Polygon", coordinates=SAMPLE_POLYGON_COORDS)
        geom3 = WOFGeometry(type="Point", coordinates=[-59.5, 13.2])
        collection = GeometryCollection(geometries=[geom1, geom2, geom3])

        points = collection.get_points()
        assert len(points) == 2

    @pytest.mark.unit
    def test_get_polygons(self):
        """get_polygons() should return all polygon-type geometries."""
        geom1 = WOFGeometry(type="Point", coordinates=SAMPLE_POINT_COORDS)
        geom2 = WOFGeometry(type="Polygon", coordinates=SAMPLE_POLYGON_COORDS)
        geom3 = WOFGeometry(
            type="MultiPolygon", coordinates=SAMPLE_MULTIPOLYGON_COORDS
        )
        collection = GeometryCollection(geometries=[geom1, geom2, geom3])

        polygons = collection.get_polygons()
        assert len(polygons) == 2
        assert all(g.is_polygon() for g in polygons)

    @pytest.mark.unit
    def test_get_lines(self):
        """get_lines() should return all line-type geometries."""
        geom1 = WOFGeometry(type="Point", coordinates=SAMPLE_POINT_COORDS)
        geom2 = WOFGeometry(type="LineString", coordinates=SAMPLE_LINESTRING_COORDS)
        geom3 = WOFGeometry(
            type="MultiLineString", coordinates=SAMPLE_MULTILINESTRING_COORDS
        )
        collection = GeometryCollection(geometries=[geom1, geom2, geom3])

        lines = collection.get_lines()
        assert len(lines) == 2
        assert all(g.is_line() for g in lines)

    @pytest.mark.unit
    def test_calculate_bbox_with_stored_bbox(self):
        """calculate_bbox() should return stored bbox if available."""
        geom = WOFGeometry(type="Point", coordinates=SAMPLE_POINT_COORDS)
        bbox = WOFBounds(min_lon=-60.0, min_lat=13.0, max_lon=-59.0, max_lat=14.0)
        collection = GeometryCollection(geometries=[geom], bbox=bbox)

        calculated = collection.calculate_bbox()
        assert calculated is not None
        assert calculated.min_lon == -60.0

    @pytest.mark.unit
    def test_calculate_bbox_empty_collection(self):
        """calculate_bbox() should return None for empty collection."""
        collection = GeometryCollection(geometries=[])

        assert collection.calculate_bbox() is None

    @pytest.mark.unit
    def test_to_geojson(self):
        """to_geojson() should return GeoJSON GeometryCollection."""
        geom1 = WOFGeometry(type="Point", coordinates=SAMPLE_POINT_COORDS)
        geom2 = WOFGeometry(type="Polygon", coordinates=SAMPLE_POLYGON_COORDS)
        collection = GeometryCollection(geometries=[geom1, geom2])

        geojson = collection.to_geojson()
        assert geojson["type"] == "GeometryCollection"
        assert len(geojson["geometries"]) == 2
        assert geojson["geometries"][0]["type"] == "Point"
        assert geojson["geometries"][1]["type"] == "Polygon"


class TestSpatialReference:
    """Tests for SpatialReference system information."""

    @pytest.mark.unit
    def test_default_spatial_reference(self):
        """SpatialReference should default to WGS84."""
        sref = SpatialReference()

        assert sref.srid == 4326
        assert sref.name == "WGS84"

    @pytest.mark.unit
    def test_custom_spatial_reference(self):
        """SpatialReference should accept custom SRID."""
        sref = SpatialReference(srid=3857, name="Web Mercator")

        assert sref.srid == 3857
        assert sref.name == "Web Mercator"

    @pytest.mark.unit
    def test_spatial_reference_with_proj4(self):
        """SpatialReference should accept proj4 string."""
        proj4_str = "+proj=longlat +datum=WGS84 +no_defs"
        sref = SpatialReference(proj4=proj4_str)

        assert sref.proj4 == proj4_str

    @pytest.mark.unit
    def test_is_wgs84_true(self):
        """is_wgs84() should return True for SRID 4326."""
        sref = SpatialReference(srid=4326)

        assert sref.is_wgs84() is True

    @pytest.mark.unit
    def test_is_wgs84_false(self):
        """is_wgs84() should return False for non-WGS84 SRID."""
        sref = SpatialReference(srid=3857, name="Web Mercator")

        assert sref.is_wgs84() is False

    @pytest.mark.unit
    def test_is_web_mercator_true(self):
        """is_web_mercator() should return True for SRID 3857."""
        sref = SpatialReference(srid=3857, name="Web Mercator")

        assert sref.is_web_mercator() is True

    @pytest.mark.unit
    def test_is_web_mercator_false(self):
        """is_web_mercator() should return False for non-Web Mercator SRID."""
        sref = SpatialReference(srid=4326)

        assert sref.is_web_mercator() is False


class TestBoundsDatelineCrossing:
    """Tests for bounding box handling of dateline crossing."""

    @pytest.mark.unit
    def test_dateline_crossing_allowed(self):
        """Bounds should allow dateline crossing (min_lon > max_lon)."""
        # Crossing dateline: from 170°E to -170°W
        bounds = WOFBounds(min_lon=170.0, min_lat=10.0, max_lon=-170.0, max_lat=20.0)

        assert bounds.min_lon == 170.0
        assert bounds.max_lon == -170.0

    @pytest.mark.unit
    def test_dateline_crossing_contains_point(self):
        """contains_point() should work with dateline crossing."""
        bounds = WOFBounds(min_lon=170.0, min_lat=10.0, max_lon=-170.0, max_lat=20.0)

        # Points on both sides of dateline should be inside
        assert bounds.contains_point(175.0, 15.0) is True
        assert bounds.contains_point(-175.0, 15.0) is True
        # Point in middle of Pacific should be outside
        assert bounds.contains_point(0.0, 15.0) is False

    @pytest.mark.unit
    def test_dateline_crossing_get_center(self):
        """get_center() should handle dateline crossing correctly."""
        bounds = WOFBounds(min_lon=170.0, min_lat=10.0, max_lon=-170.0, max_lat=20.0)
        center = bounds.get_center()

        # Center should be near 180/-180
        assert 179 <= abs(center[0]) <= 180
        assert center[1] == 15.0  # Latitude midpoint

    @pytest.mark.unit
    def test_dateline_crossing_get_width(self):
        """get_width() should handle dateline crossing correctly."""
        bounds = WOFBounds(min_lon=170.0, min_lat=10.0, max_lon=-170.0, max_lat=20.0)
        width = bounds.get_width()

        # Width should be 20 degrees (170 to 180 + 180 to -170)
        assert width == 20.0

    @pytest.mark.unit
    def test_dateline_crossing_intersects(self):
        """intersects() should return True for dateline crossing bounds."""
        bounds1 = WOFBounds(min_lon=170.0, min_lat=10.0, max_lon=-170.0, max_lat=20.0)
        bounds2 = WOFBounds(min_lon=175.0, min_lat=12.0, max_lon=-175.0, max_lat=18.0)

        # Simplified implementation returns True for dateline crossing
        assert bounds1.intersects(bounds2) is True
