"""
Data analysis and statistics for WOF place collections.
"""

from __future__ import annotations

from typing import List, Dict, Any
from collections import Counter

from wof_explorer.models.places import WOFPlace


class PlaceAnalyzer:
    """Analyzes WOF place collections for patterns and statistics."""

    def __init__(self, places: List[WOFPlace]):
        self.places = places

    def calculate_summary(self) -> Dict[str, Any]:
        return {
            "count": len(self.places),
            "placetypes": self._placetype_distribution(),
            "status": self._status_distribution(),
            "countries": self._country_distribution(),
            "spatial": self._spatial_statistics(),
        }

    def _placetype_distribution(self) -> Dict[str, int]:
        return dict(Counter(p.placetype for p in self.places))

    def _status_distribution(self) -> Dict[str, int]:
        return {
            "current": sum(1 for p in self.places if getattr(p, "is_current", 0) == 1),
            "deprecated": sum(
                1 for p in self.places if getattr(p, "is_deprecated", False)
            ),
            "ceased": sum(1 for p in self.places if getattr(p, "is_ceased", False)),
        }

    def _country_distribution(self) -> Dict[str, int]:
        countries = [
            p.country
            for p in self.places
            if getattr(p, "country", None) is not None and p.country is not None
        ]
        return dict(Counter(countries))

    def _spatial_statistics(self) -> Dict[str, Any]:
        if not self.places:
            return {"bounds": None, "avg_lat": None, "avg_lon": None}

        with_bbox = [p for p in self.places if p.get_bounds() is not None]
        if with_bbox:
            bounds_list = [b for p in with_bbox if (b := p.get_bounds()) is not None]
            if bounds_list:
                min_lon = min(b.min_lon for b in bounds_list)
                min_lat = min(b.min_lat for b in bounds_list)
                max_lon = max(b.max_lon for b in bounds_list)
                max_lat = max(b.max_lat for b in bounds_list)
                bounds = [min_lon, min_lat, max_lon, max_lat]
            else:
                bounds = None
        else:
            bounds = None

        avg_lat = sum(getattr(p, "latitude", 0.0) for p in self.places) / len(
            self.places
        )
        avg_lon = sum(getattr(p, "longitude", 0.0) for p in self.places) / len(
            self.places
        )
        return {"bounds": bounds, "avg_lat": avg_lat, "avg_lon": avg_lon}

    def analyze_coverage(
        self, requested: List[Any], found: List[Any]
    ) -> Dict[str, Any]:
        requested_set = set(requested)
        found_set = set(found)
        missing = sorted(list(requested_set - found_set))
        coverage = (
            (len(found_set) / len(requested_set) * 100.0) if requested_set else 0.0
        )
        return {
            "requested": len(requested_set),
            "found": len(found_set),
            "missing": missing,
            "coverage_percent": coverage,
        }
