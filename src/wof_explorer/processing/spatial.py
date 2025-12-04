"""
Lightweight spatial helpers for WOF geometries.

Provides point-in-polygon tests for GeoJSON geometries and
convenience functions to find places under a clicked point.

This module avoids heavy GIS deps (shapely/geopandas) by
implementing a robust ray-casting algorithm for Polygon and
MultiPolygon geometries. It also falls back to bounding-box checks
when geometry is not present.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from wof_explorer.models.places import WOFPlace
from wof_explorer.processing.collections import PlaceCollection
from wof_explorer.types import PlaceType


Coord = Tuple[float, float]  # (lon, lat)


def _point_in_ring(point: Coord, ring: Sequence[Coord]) -> bool:
    """Return True if point is inside the ring using ray casting.

    Includes boundary as inside (touching edges/vertices returns True).
    """
    x, y = point
    inside = False

    if not ring:
        return False

    # Iterate edges: (xi, yi) -> (xj, yj)
    n = len(ring)
    for i in range(n):
        x_i, y_i = ring[i]
        x_j, y_j = ring[(i + 1) % n]

        # Check if point is on a vertex
        if x == x_i and y == y_i:
            return True

        # Check if point is on a horizontal segment
        if y_i == y_j == y and min(x_i, x_j) <= x <= max(x_i, x_j):
            return True

        # Check if segment crosses the horizontal ray to the right of point
        intersects = (y_i > y) != (y_j > y)
        if intersects:
            # Compute intersection of segment with horizontal line at y
            try:
                x_intersect = x_i + (y - y_i) * (x_j - x_i) / (y_j - y_i)
            except ZeroDivisionError:
                # Should not happen due to (y_i > y) != (y_j > y)
                x_intersect = x_i

            # On-edge check (treat as inside)
            if x_intersect == x:
                return True

            if x_intersect > x:
                inside = not inside

    return inside


def _point_in_polygon(point: Coord, polygon: Sequence[Sequence[Coord]]) -> bool:
    """Return True if point lies within a polygon with optional holes.

    The first ring is treated as the exterior ring, subsequent rings
    are treated as holes.
    """
    if not polygon:
        return False

    shell = polygon[0]
    if not _point_in_ring(point, shell):
        return False

    # If in any hole, it's outside
    for hole in polygon[1:]:
        if _point_in_ring(point, hole):
            return False
    return True


def _point_in_multipolygon(
    point: Coord, multipolygon: Sequence[Sequence[Sequence[Coord]]]
) -> bool:
    """Return True if point lies within any polygon in a multipolygon."""
    for poly in multipolygon:
        if _point_in_polygon(point, poly):
            return True
    return False


def point_in_geojson_geometry(lon: float, lat: float, geometry: Dict[str, Any]) -> bool:
    """Return True if (lon, lat) lies within the GeoJSON geometry.

    Supports Point, Polygon, MultiPolygon. For LineString/MultiLineString
    and unknown types, returns False.
    """
    if not geometry:
        return False

    # Unwrap Feature
    if geometry.get("type") == "Feature":
        geometry = geometry.get("geometry", {}) or {}

    gtype = geometry.get("type")
    coords = geometry.get("coordinates")

    if not gtype or coords is None:
        return False

    # Normalize to tuples for safety
    p = (lon, lat)

    if gtype == "Point":
        try:
            return float(coords[0]) == lon and float(coords[1]) == lat
        except Exception:
            return False
    elif gtype == "Polygon":
        # coords: List[ring], ring: List[[x,y]]
        rings: List[List[Coord]] = [
            [(float(x), float(y)) for x, y in ring] for ring in coords or []
        ]
        return _point_in_polygon(p, rings)
    elif gtype == "MultiPolygon":
        # coords: List[polygon], polygon: List[ring]
        polys: List[List[List[Coord]]] = [
            [[(float(x), float(y)) for x, y in ring] for ring in polygon or []]
            for polygon in coords or []
        ]
        return _point_in_multipolygon(p, polys)

    # Not supported for containment
    return False


def places_containing_point(
    places: Iterable[WOFPlace],
    lat: float,
    lon: float,
) -> List[WOFPlace]:
    """Filter places to those whose geometry (or bbox) contains the point.

    - If a place has a GeoJSON geometry, use exact polygon containment
      where supported (Polygon/MultiPolygon).
    - Otherwise, fall back to bounding box containment if available.
    """
    results: List[WOFPlace] = []
    for place in places:
        # Prefer exact geometry when present
        geom = getattr(place, "geometry", None)
        if geom:
            if point_in_geojson_geometry(lon, lat, geom):
                results.append(place)
                continue

        # Fallback: bounding box
        bbox_list = getattr(place, "bbox", None)
        if bbox_list and len(bbox_list) == 4:
            min_lon, min_lat, max_lon, max_lat = bbox_list
            if (min_lon <= lon <= max_lon) and (min_lat <= lat <= max_lat):
                results.append(place)

    return results


async def query_under_point(
    connector,
    lat: float,
    lon: float,
    placetypes: Optional[List[PlaceType]] = None,
    country: Optional[str] = None,
    radius_km: float = 10.0,
) -> PlaceCollection:
    """Query the dataset for places that contain the given point.

    Strategy:
    1) Do a coarse proximity search around (lat, lon) to get candidates.
    2) Fetch candidates with geometry.
    3) Filter by exact polygon containment where possible (fallback to bbox).

    Args:
        connector: A connected WOF connector
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        placetypes: Optional list of PlaceType to restrict results
        country: Optional ISO country code filter (e.g., "US", "CA")
        radius_km: Proximity radius used for coarse candidate selection

    Returns:
        PlaceCollection with matching places (with geometry included).
    """
    from wof_explorer.models.filters import WOFSearchFilters

    # Build coarse candidate search
    filters = WOFSearchFilters(
        is_current=True,
        near_lat=lat,
        near_lon=lon,
        radius_km=radius_km,
    )
    if placetypes:
        filters.placetype = placetypes  # type: ignore[assignment]
    if country:
        filters.country = country  # type: ignore[assignment]

    cursor = await connector.search(filters)
    # Load full details with geometry
    candidates = await cursor.fetch_all(include_geometry=True)

    # Filter by polygon containment
    matches = places_containing_point(candidates.places, lat=lat, lon=lon)

    # Sort small → large by placetype level
    def _level(p: WOFPlace) -> int:
        try:
            return PlaceType.get_hierarchy_level(p.placetype)
        except Exception:
            return 999

    # Higher level value = smaller area (e.g., microhood > county), show smaller first
    matches.sort(key=_level, reverse=True)
    return PlaceCollection.from_places(matches, source="under_point", lat=lat, lon=lon)


__all__ = [
    "point_in_geojson_geometry",
    "places_containing_point",
    "query_under_point",
]
