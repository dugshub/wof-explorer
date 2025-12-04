"""
Browsing and navigation utilities for WOF place collections.
"""

from __future__ import annotations

from typing import List, Dict, Any

from wof_explorer.models.places import WOFPlace


class PlaceBrowser:
    """Provides different browsing views of place collections."""

    def __init__(self, places: List[WOFPlace]):
        self.places = places

    def browse(self, style: str = "hierarchical") -> Dict[str, Any]:
        browsers = {
            "hierarchical": self._browse_hierarchical,
            "alphabetical": self._browse_alphabetical,
            "geographic": self._browse_geographic,
            "quality": self._browse_quality,
        }
        if style not in browsers:
            raise ValueError(f"Unknown browse style: {style}")
        return browsers[style]()

    def _browse_hierarchical(self) -> Dict[str, Any]:
        hierarchy: Dict[str, List[Dict[str, Any]]] = {}
        for place in self.places:
            pt = place.placetype
            hierarchy.setdefault(pt, []).append(
                {"id": place.id, "name": place.name, "parent": place.parent_id}
            )
        return {
            "style": "hierarchical",
            "data": hierarchy,
            "stats": {"total": len(self.places), "types": len(hierarchy)},
        }

    def _browse_alphabetical(self) -> Dict[str, Any]:
        by_letter: Dict[str, List[Dict[str, Any]]] = {}
        for place in sorted(self.places, key=lambda p: (p.name or "")):
            letter = place.name[0].upper() if place.name else "#"
            by_letter.setdefault(letter, []).append(
                {"id": place.id, "name": place.name, "type": place.placetype}
            )
        return {
            "style": "alphabetical",
            "data": by_letter,
            "index": list(by_letter.keys()),
        }

    def _browse_geographic(self) -> Dict[str, Any]:
        by_country: Dict[str, Dict[str, Any]] = {}
        for place in self.places:
            country = place.country or "Unknown"
            by_country.setdefault(country, {"regions": {}, "places": []})
            # Region attribute may not exist; include under places if missing
            region = getattr(place, "region", None)
            if region:
                by_country[country]["regions"].setdefault(region, []).append(
                    {"id": place.id, "name": place.name, "type": place.placetype}
                )
            else:
                by_country[country]["places"].append(
                    {"id": place.id, "name": place.name, "type": place.placetype}
                )
        return {
            "style": "geographic",
            "data": by_country,
            "countries": list(by_country.keys()),
        }

    def _browse_quality(self) -> Dict[str, Any]:
        tiers: Dict[str, List[Dict[str, Any]]] = {
            "complete": [],
            "good": [],
            "basic": [],
            "minimal": [],
        }
        for place in self.places:
            score = self._calculate_quality_score(place)
            tier = (
                "complete"
                if score >= 0.9
                else "good" if score >= 0.7 else "basic" if score >= 0.5 else "minimal"
            )
            tiers[tier].append({"id": place.id, "name": place.name, "score": score})
        return {
            "style": "quality",
            "data": tiers,
            "distribution": {k: len(v) for k, v in tiers.items()},
        }

    def _calculate_quality_score(self, place: WOFPlace) -> float:
        # Adjusted for available fields in WOFPlace model
        checks = [
            (getattr(place, "name", None), 0.25),
            (getattr(place, "bbox", None), 0.25),
            (
                (
                    getattr(place, "latitude", None) is not None
                    and getattr(place, "longitude", None) is not None
                ),
                0.2,
            ),
            (hasattr(place, "geometry") and getattr(place, "geometry", None), 0.3),
        ]
        score = 0.0
        for ok, weight in checks:
            if ok:
                score += weight
        return min(score, 1.0)
