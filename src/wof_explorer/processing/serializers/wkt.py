"""
WKT serializer for WOF places.
Converts GeoJSON-like geometry dicts to WKT strings.
"""

from __future__ import annotations

from typing import List, Dict, Any

from wof_explorer.models.places import WOFPlace, WOFPlaceWithGeometry
from wof_explorer.processing.serializers.base import SerializerBase, SerializerRegistry


class WKTSerializer(SerializerBase):
    """Serializes WOF places with geometry to WKT lines."""

    def serialize_to_dict(
        self, places: List[WOFPlace], **options
    ) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        for place in places:
            if isinstance(place, WOFPlaceWithGeometry) and place.geometry:
                geom = self._unwrap_feature(place.geometry)
                wkt = self._geometry_to_wkt(geom)
                records.append({"id": place.id, "name": place.name, "wkt": wkt})
        return records

    def serialize(self, places: List[WOFPlace], **options) -> str:
        records = self.serialize_to_dict(places, **options)
        return "\n".join(f"{r['id']}\t{r['name']}\t{r['wkt']}" for r in records)

    def _unwrap_feature(self, geometry: Dict[str, Any]) -> Dict[str, Any]:
        if geometry.get("type") == "Feature":
            return geometry.get("geometry", {}) or {}
        return geometry

    def _geometry_to_wkt(self, geometry: Dict[str, Any]) -> str:
        gtype = (geometry or {}).get("type")
        coords = (geometry or {}).get("coordinates", [])
        if not gtype:
            return "GEOMETRYCOLLECTION EMPTY"

        t = gtype.upper()
        if t == "POINT":
            try:
                return f"POINT({coords[0]} {coords[1]})"
            except Exception:
                return "POINT EMPTY"
        if t == "POLYGON":
            return self._polygon_to_wkt(coords)
        if t == "MULTIPOLYGON":
            return self._multipolygon_to_wkt(coords)
        if t == "MULTIPOINT":
            pts = ", ".join(f"({x} {y})" for x, y in coords)
            return f"MULTIPOINT({pts})"
        if t == "LINESTRING":
            pts = ", ".join(f"{x} {y}" for x, y in coords)
            return f"LINESTRING({pts})"
        if t == "MULTILINESTRING":
            lines = ", ".join(
                f"({', '.join(f'{x} {y}' for x, y in line)})" for line in coords
            )
            return f"MULTILINESTRING({lines})"
        return f"{t} EMPTY"

    def _polygon_to_wkt(self, coords: List) -> str:
        rings = []
        for ring in coords or []:
            points = ", ".join(f"{x} {y}" for x, y in ring)
            rings.append(f"({points})")
        inner = ", ".join(rings)
        return f"POLYGON({inner})" if inner else "POLYGON EMPTY"

    def _multipolygon_to_wkt(self, coords: List) -> str:
        polygons = []
        for polygon in coords or []:
            rings = []
            for ring in polygon or []:
                points = ", ".join(f"{x} {y}" for x, y in ring)
                rings.append(f"({points})")
            polygons.append(f"({', '.join(rings)})")
        inner = ", ".join(polygons)
        return f"MULTIPOLYGON({inner})" if inner else "MULTIPOLYGON EMPTY"


# Self-register on import
SerializerRegistry.register("wkt", WKTSerializer())
