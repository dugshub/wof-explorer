"""
High-level helpers to assemble commonly-needed geographic selections.

Exports a single entry point `quick_explore(...)` that returns
collections for:
  - US counties
  - Target city localities (focus list)
  - Neighborhood coverage for those cities

All collections can be serialized via PlaceCollection methods
to GeoJSON/WKT/CSV for front-end consumption.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from wof_explorer.models.filters import WOFSearchFilters, WOFFilters
from wof_explorer.processing.collections import PlaceCollection
from wof_explorer.types import PlaceType


DEFAULT_FOCUS_CITIES: List[str] = [
    "Chicago",
    "New York",
    "San Francisco",
    "Seattle",
    "Toronto",
    "Los Angeles",
    "Washington",
    "Denver",
    "Detroit",
    "Miami",
    "Miami Beach",
]


async def _find_locality(
    connector, name: str, country: Optional[str] = None
) -> Optional[int]:
    """Return the best locality ID for a city name (if found)."""
    filters = WOFSearchFilters(
        name=name,
        placetype=PlaceType.LOCALITY,
        is_current=True,
        limit=10,
    )
    if country:
        filters.country = country  # type: ignore[assignment]

    cursor = await connector.search(filters)
    # Prefer exact name match first, then first result
    exact = [p for p in cursor.places if p.name and p.name.lower() == name.lower()]
    if exact:
        return exact[0].id
    return cursor.places[0].id if cursor.places else None


async def _collect_localities(connector, names: Iterable[str]) -> PlaceCollection:
    """Fetch full locality places (with geometry) for given names."""
    ids: List[int] = []
    for n in names:
        # Country hint: Toronto likely CA, others US; keep it simple
        country = "CA" if n.lower() == "toronto" else None
        place_id = await _find_locality(connector, n, country)
        if place_id:
            ids.append(place_id)

    if not ids:
        return PlaceCollection.from_places([], source="cities")

    places = await connector.get_places(ids, include_geometry=True)
    return PlaceCollection.from_places(list(places), source="cities")


async def _collect_neighborhoods_for_localities(
    connector, locality_ids: List[int]
) -> PlaceCollection:
    """Fetch neighborhood-like descendants for the given localities."""
    all_places = []

    # Neighborhood types we care about
    types_in_order = [
        PlaceType.MICROHOOD,
        PlaceType.NEIGHBOURHOOD,
        PlaceType.MACROHOOD,
        PlaceType.BOROUGH,
    ]

    for lid in locality_ids:
        for ptype in types_in_order:
            desc = await connector.get_descendants(
                lid, WOFFilters(placetype=ptype, is_current=True)
            )
            all_places.extend(desc)

    # De-duplicate by id while preserving order
    seen = set()
    deduped = []
    for p in all_places:
        if p.id not in seen:
            seen.add(p.id)
            deduped.append(p)

    # Load geometry for the set
    ids = [p.id for p in deduped]
    if not ids:
        return PlaceCollection.from_places([], source="neighborhoods")
    full = await connector.get_places(ids, include_geometry=True)
    return PlaceCollection.from_places(list(full), source="neighborhoods")


async def quick_explore(
    connector,
    focus_cities: Optional[List[str]] = None,
    include_us_counties: bool = True,
) -> Dict[str, PlaceCollection]:
    """Assemble the target selections needed for exploration demos.

    Returns a dict with keys:
      - 'us_counties': PlaceCollection (if include_us_counties)
      - 'cities': PlaceCollection
      - 'neighborhoods': PlaceCollection

    All collections have geometry included where available and are
    immediately serializable via `.to_geojson()`.
    """
    focus = focus_cities or DEFAULT_FOCUS_CITIES

    results: Dict[str, PlaceCollection] = {}

    # 1) US counties (admin coverage)
    if include_us_counties:
        county_filters = WOFSearchFilters(
            placetype=PlaceType.COUNTY,
            country="US",
            is_current=True,
        )
        county_cursor = await connector.search(county_filters)
        us_counties = await county_cursor.fetch_all(include_geometry=True)
        results["us_counties"] = us_counties

    # 2) Focus cities (localities)
    city_collection = await _collect_localities(connector, focus)
    results["cities"] = city_collection

    # 3) Neighborhood coverage for those cities
    locality_ids = [p.id for p in city_collection.places]
    neighborhoods = await _collect_neighborhoods_for_localities(connector, locality_ids)
    results["neighborhoods"] = neighborhoods

    return results


__all__ = [
    "quick_explore",
    "DEFAULT_FOCUS_CITIES",
]
