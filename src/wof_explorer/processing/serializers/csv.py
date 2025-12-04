"""
CSV serializer for WOF places.
Exports tabular data with configurable columns.
"""

from __future__ import annotations

import csv as _csv
from io import StringIO
from typing import List, Dict, Any

from wof_explorer.models.places import WOFPlace
from wof_explorer.processing.serializers.base import SerializerBase, SerializerRegistry


class CSVSerializer(SerializerBase):
    """Serializes WOF places to CSV format."""

    def __init__(self):
        self.default_columns = [
            "id",
            "name",
            "placetype",
            "is_current",
            "country",
            "repo",
            "latitude",
            "longitude",
            "min_lat",
            "min_lon",
            "max_lat",
            "max_lon",
            "lastmodified",
        ]

    def serialize_to_dict(
        self, places: List[WOFPlace], **options
    ) -> List[Dict[str, Any]]:
        columns = options.get("columns", self.default_columns)
        rows: List[Dict[str, Any]] = []
        for place in places:
            rows.append(self._place_to_row(place, columns))
        return rows

    def _place_to_row(self, place: WOFPlace, columns: List[str]) -> Dict[str, Any]:
        row: Dict[str, Any] = {}
        for col in columns:
            if col in {"min_lat", "min_lon", "max_lat", "max_lon"}:
                bbox = place.get_bounds()
                if bbox:
                    row["min_lat"] = bbox.min_lat
                    row["min_lon"] = bbox.min_lon
                    row["max_lat"] = bbox.max_lat
                    row["max_lon"] = bbox.max_lon
                else:
                    row.setdefault("min_lat", None)
                    row.setdefault("min_lon", None)
                    row.setdefault("max_lat", None)
                    row.setdefault("max_lon", None)
            elif hasattr(place, col):
                row[col] = getattr(place, col)
            elif col == "lat":
                row[col] = getattr(place, "latitude", None)
            elif col == "lon":
                row[col] = getattr(place, "longitude", None)
            else:
                row[col] = None
        return row

    def serialize(self, places: List[WOFPlace], **options) -> str:
        rows = self.serialize_to_dict(places, **options)
        if not rows:
            return ""
        output = StringIO()
        writer = _csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()

    def write(self, places: List[WOFPlace], file, **options) -> None:
        rows = self.serialize_to_dict(places, **options)
        if not rows:
            return
        writer = _csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


# Self-register on import
SerializerRegistry.register("csv", CSVSerializer())
