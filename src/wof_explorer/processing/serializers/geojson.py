"""
GeoJSON serializer for WOF places.
Builds Feature and FeatureCollection objects.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
import json

from wof_explorer.models.places import WOFPlace, WOFPlaceWithGeometry
from wof_explorer.processing.serializers.base import SerializerBase, SerializerRegistry


class GeoJSONSerializer(SerializerBase):
    """Serializes WOF places to GeoJSON format."""

    def __init__(self):
        self.default_properties = [
            "id",
            "name",
            "placetype",
            "is_current",
            "country",
            "repo",
            "lastmodified",
        ]

    def serialize_to_dict(self, places: List[WOFPlace], **options) -> Dict[str, Any]:
        features = []
        for place in places:
            feature = self._place_to_feature(place, **options)
            if feature is not None:
                features.append(feature)

        result: Dict[str, Any] = {
            "type": "FeatureCollection",
            "features": features,
        }

        # Optionally add bbox to FeatureCollection (this is valid per GeoJSON spec)
        if options.get("include_collection_bbox", False):
            bbox = self._calculate_bounds(places)
            if bbox:
                result["bbox"] = bbox

        return result

    def serialize(self, places: List[WOFPlace], **options) -> str:
        data = self.serialize_to_dict(places, **options)
        indent = options.get("indent", 2 if options.get("pretty", True) else None)

        # Custom JSON encoder to handle datetime objects
        from datetime import datetime

        def json_serial(obj):
            """JSON serializer for objects not serializable by default."""
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        return json.dumps(data, indent=indent, default=json_serial)

    def _place_to_feature(self, place: WOFPlace, **options) -> Optional[Dict[str, Any]]:
        require_geometry = options.get("require_geometry", True)

        geometry = None
        if isinstance(place, WOFPlaceWithGeometry):
            geometry = self._extract_geometry(place)

        if require_geometry and geometry is None:
            return None

        properties = self._extract_properties(place, **options)
        return {
            "type": "Feature",
            "id": place.id,
            "properties": properties,
            "geometry": geometry,
        }

    def _extract_properties(self, place: WOFPlace, **options) -> Dict[str, Any]:
        include_props = (
            options.get("properties", self.default_properties)
            or self.default_properties
        )
        exclude_props = set(options.get("exclude_properties", []))

        properties: Dict[str, Any] = {}
        for prop in include_props:
            if prop in exclude_props:
                continue
            if hasattr(place, prop):
                value = getattr(place, prop)
                if value is not None:
                    properties[prop] = value

        # Always include center point and bbox if available
        properties.setdefault("latitude", getattr(place, "latitude", None))
        properties.setdefault("longitude", getattr(place, "longitude", None))
        bbox = place.get_bounds()
        if bbox:
            properties.setdefault(
                "bbox", [bbox.min_lon, bbox.min_lat, bbox.max_lon, bbox.max_lat]
            )

        return properties

    def _extract_geometry(
        self, place: WOFPlaceWithGeometry
    ) -> Optional[Dict[str, Any]]:
        geom = place.geometry
        if geom is None:
            return None
        # If geometry field is a Feature, unwrap
        if isinstance(geom, dict) and geom.get("type") == "Feature":
            return geom.get("geometry")
        return geom if isinstance(geom, dict) else None

    def _calculate_bounds(self, places: List[WOFPlace]) -> Optional[List[float]]:
        if not places:
            return None

        # Filter places that have valid bboxes
        places_with_bbox = [p for p in places if p.get_bounds() is not None]
        if not places_with_bbox:
            return None

        bounds_list = [b for p in places_with_bbox if (b := p.get_bounds()) is not None]
        if not bounds_list:
            return None

        min_lon = min(b.min_lon for b in bounds_list)
        min_lat = min(b.min_lat for b in bounds_list)
        max_lon = max(b.max_lon for b in bounds_list)
        max_lat = max(b.max_lat for b in bounds_list)
        return [min_lon, min_lat, max_lon, max_lat]


# Self-register on import
SerializerRegistry.register("geojson", GeoJSONSerializer())
