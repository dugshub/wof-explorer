"""
Cursor implementations for WOF connector.
Cursors provide lazy-loading access to search results and hierarchical data.
"""

from typing import List, Optional, Dict, Any, TYPE_CHECKING, ClassVar

from wof_explorer.models.places import WOFPlace, WOFPlaceWithGeometry
from wof_explorer.models.hierarchy import WOFAncestor
from wof_explorer.models.filters import WOFFilters
from wof_explorer.display.descriptor import DisplayDescriptor
from .collections import PlaceCollection

if TYPE_CHECKING:
    from wof_explorer.backends.sqlite.connector import (
        SQLiteWOFConnector as WOFConnector,
    )
    from wof_explorer.backends.sqlite.models import InternalSearchResult


class WOFSearchCursor:
    """
    Cursor for search results that enables lazy loading of full place details.

    Similar to database cursors, this provides lightweight access to search results
    with the ability to fetch full details on demand.
    """

    display: ClassVar[DisplayDescriptor] = DisplayDescriptor()

    def __init__(self, result: "InternalSearchResult", connector: "WOFConnector"):
        """
        Initialize search cursor.

        Args:
            result: Internal search result data
            connector: Reference to the connector for fetching additional data
        """
        from wof_explorer.backends.sqlite.models import InternalSearchResult

        # Store the internal result directly
        self._result: InternalSearchResult = result
        self._connector = connector

    # ============= Direct access to result data =============

    @property
    def places(self) -> List[WOFPlace]:
        """Get the list of places (lightweight SPR data)."""
        return self._result.places

    @property
    def total_count(self) -> int:
        """Get total number of results."""
        return self._result.total_count

    @property
    def query_filters(self) -> Dict[str, Any]:
        """Get the filters used for this search."""
        return self._result.query_filters

    @property
    def has_results(self) -> bool:
        """Check if search returned any results."""
        return self._result.has_results

    def __len__(self) -> int:
        """Return number of results."""
        return len(self.places)

    def __getitem__(self, index: int) -> WOFPlace:
        """Get a place by index."""
        return self.places[index]

    def __iter__(self):
        """Iterate over places."""
        return iter(self.places)

    # ============= Fetch operations =============

    async def fetch_all(self, include_geometry: bool = False) -> PlaceCollection:
        """
        Fetch full details for all places in the cursor.

        Args:
            include_geometry: Whether to include GeoJSON geometry

        Returns:
            PlaceCollection with full details
        """
        if not self.places:
            return PlaceCollection(places=[], metadata={"source": "cursor"})

        place_ids = [p.id for p in self.places]
        places = await self._connector.get_places(place_ids, include_geometry)

        return PlaceCollection.from_places(
            places,
            source="cursor",
            query_filters=self.query_filters,
            fetched_with_geometry=include_geometry,
        )

    async def fetch_one(
        self, index: int = 0, include_geometry: bool = False
    ) -> Optional[WOFPlace]:
        """
        Fetch full details for a single place by index.

        Args:
            index: Index of the place to fetch (default: 0)
            include_geometry: Whether to include GeoJSON geometry

        Returns:
            Place with full details or None if index out of range
        """
        if index >= len(self.places) or index < 0:
            return None

        place_id = self.places[index].id
        return await self._connector.get_place(place_id, include_geometry)

    async def fetch_page(
        self, page: int = 1, size: int = 10, include_geometry: bool = False
    ) -> PlaceCollection:
        """
        Fetch a page of results with full details.

        Args:
            page: Page number (1-indexed)
            size: Number of results per page
            include_geometry: Whether to include GeoJSON geometry

        Returns:
            PlaceCollection for the requested page
        """
        if page < 1:
            page = 1

        start = (page - 1) * size
        end = start + size

        # Get the places for this page
        page_places = self.places[start:end]
        if not page_places:
            return PlaceCollection(places=[], metadata={"page": page, "size": size})

        # Fetch full details for the page
        place_ids = [p.id for p in page_places]
        places = await self._connector.get_places(place_ids, include_geometry)

        return PlaceCollection.from_places(
            places,
            source="cursor",
            page=page,
            size=size,
            total_pages=(self.total_count // size)
            + (1 if self.total_count % size else 0),
            fetched_with_geometry=include_geometry,
        )

    async def fetch_geometries(self) -> List[WOFPlaceWithGeometry]:
        """
        Fetch all places with their geometries.

        Convenience method equivalent to fetch_all(include_geometry=True).

        Returns:
            List of places with geometry data
        """
        collection = await self.fetch_all(include_geometry=True)
        # When include_geometry=True, places should be WOFPlaceWithGeometry
        return collection.places  # type: ignore[return-value]

    async def fetch_by_ids(
        self, place_ids: List[int], include_geometry: bool = False
    ) -> List[WOFPlace]:
        """
        Fetch specific places from the cursor by their IDs.

        Args:
            place_ids: List of place IDs to fetch
            include_geometry: Whether to include GeoJSON geometry

        Returns:
            List of places with full details
        """
        # Filter to only IDs that are in our results
        result_ids = {p.id for p in self.places}
        filtered_ids = [pid for pid in place_ids if pid in result_ids]

        if not filtered_ids:
            return []

        return await self._connector.get_places(filtered_ids, include_geometry)

    # ============= Utility methods =============

    def get_page_info(self, page_size: int = 10) -> Dict[str, int]:
        """
        Get pagination information for the cursor.

        Args:
            page_size: Number of items per page

        Returns:
            Dictionary with pagination info
        """
        total = self.total_count
        total_pages = (total // page_size) + (1 if total % page_size else 0)

        return {
            "total_count": total,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    def filter_places(self, **kwargs) -> List[WOFPlace]:
        """
        Filter the cursor's places by attributes.

        Args:
            **kwargs: Attribute filters (e.g., placetype="locality")

        Returns:
            Filtered list of places
        """
        filtered = self.places

        for key, value in kwargs.items():
            filtered = [
                p for p in filtered if hasattr(p, key) and getattr(p, key) == value
            ]

        return filtered

    async def to_dict(self, include_geometry: bool = False) -> Dict[str, Any]:
        """
        Convert cursor to a dictionary representation.

        Args:
            include_geometry: Whether to fetch and include geometries

        Returns:
            Dictionary representation of the cursor
        """
        data = {
            "total_count": self.total_count,
            "query_filters": self.query_filters,
            "places": [],
        }

        if include_geometry:
            places = await self.fetch_all(include_geometry=True)
            data["places"] = [p.model_dump() for p in places]
        else:
            data["places"] = [p.model_dump() for p in self.places]

        return data

    async def to_geojson(
        self, fetch_geometry: bool = True, properties: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Convert cursor results to GeoJSON FeatureCollection.
        Perfect for pasting into geojson.io or mapping libraries.

        Args:
            fetch_geometry: Whether to fetch full geometries (if False, uses point locations)
            properties: List of place attributes to include in feature properties
                       (defaults to ['id', 'name', 'placetype', 'is_current'])

        Returns:
            GeoJSON FeatureCollection that can be pasted directly into geojson.io
        """
        if properties is None:
            properties = ["id", "name", "placetype", "is_current"]

        features = []

        if fetch_geometry:
            # Fetch full geometries
            places = await self.fetch_all(include_geometry=True)

            for place in places:
                # Use actual geometry if available, otherwise create point
                if hasattr(place, "geometry") and place.geometry:
                    geometry = place.geometry
                else:
                    geometry = {
                        "type": "Point",
                        "coordinates": [place.longitude, place.latitude],
                    }

                feature = {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": {
                        prop: getattr(place, prop, None) for prop in properties
                    },
                }
                features.append(feature)
        else:
            # Just use point locations from lightweight data
            for place in self.places:
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [place.longitude, place.latitude],
                    },
                    "properties": {
                        prop: getattr(place, prop, None) for prop in properties
                    },
                }
                features.append(feature)

        return {
            "type": "FeatureCollection",
            "features": features,
        }

    async def to_geojson_string(self, **kwargs) -> str:
        """
        Convert to GeoJSON string ready for pasting.

        Args:
            **kwargs: Arguments passed to to_geojson()

        Returns:
            JSON string of GeoJSON FeatureCollection
        """
        import json

        geojson = await self.to_geojson(**kwargs)
        return json.dumps(geojson, indent=2)

    def to_csv_rows(self) -> List[Dict[str, Any]]:
        """
        Convert cursor results to CSV-friendly rows.

        Returns:
            List of dictionaries suitable for CSV export
        """
        rows = []
        for place in self.places:
            row = {
                "id": place.id,
                "name": place.name,
                "placetype": place.placetype,
                "latitude": place.latitude,
                "longitude": place.longitude,
                "parent_id": place.parent_id,
                "is_current": place.is_current,
                "country": place.country,
                "bbox_min_lat": (
                    place.bbox[1] if place.bbox and len(place.bbox) >= 4 else None
                ),
                "bbox_max_lat": (
                    place.bbox[3] if place.bbox and len(place.bbox) >= 4 else None
                ),
                "bbox_min_lon": (
                    place.bbox[0] if place.bbox and len(place.bbox) >= 4 else None
                ),
                "bbox_max_lon": (
                    place.bbox[2] if place.bbox and len(place.bbox) >= 4 else None
                ),
            }
            rows.append(row)
        return rows

    async def to_wkt_list(self, fetch_geometry: bool = True) -> List[Dict[str, Any]]:
        """
        Convert to Well-Known Text format for GIS tools.

        Args:
            fetch_geometry: Whether to fetch full geometries

        Returns:
            List of places with WKT geometries
        """
        from shapely.geometry import shape, Point, box

        results = []

        if fetch_geometry:
            places = await self.fetch_all(include_geometry=True)
            for place in places:
                if hasattr(place, "geometry") and place.geometry:
                    # Convert GeoJSON to WKT
                    geom = shape(place.geometry)
                    wkt = geom.wkt
                else:
                    # Use point coordinates if available
                    if place.longitude is not None and place.latitude is not None:
                        wkt = Point(place.longitude, place.latitude).wkt
                    else:
                        wkt = "POINT EMPTY"

                results.append(
                    {
                        "id": place.id,
                        "name": place.name,
                        "placetype": place.placetype,
                        "wkt": wkt,
                    }
                )
        else:
            # Use bounding boxes or points
            for place in self.places:
                if place.bbox:
                    # Create box from bbox
                    wkt = box(
                        place.bbox[0],  # min_lon
                        place.bbox[1],  # min_lat
                        place.bbox[2],  # max_lon
                        place.bbox[3],  # max_lat
                    ).wkt
                else:
                    # Use point coordinates if available
                    if place.longitude is not None and place.latitude is not None:
                        wkt = Point(place.longitude, place.latitude).wkt
                    else:
                        wkt = "POINT EMPTY"

                results.append(
                    {
                        "id": place.id,
                        "name": place.name,
                        "placetype": place.placetype,
                        "wkt": wkt,
                    }
                )

        return results


class WOFHierarchyCursor:
    """
    Cursor for hierarchical navigation results.

    Provides methods for traversing place hierarchies efficiently.
    Future implementation for hierarchy-specific operations.
    """

    display: ClassVar[DisplayDescriptor] = DisplayDescriptor()

    def __init__(self, root_place: WOFPlace, connector: "WOFConnector"):
        """
        Initialize hierarchy cursor.

        Args:
            root_place: The root place for hierarchy operations
            connector: Reference to the connector
        """
        self._root = root_place
        self._connector = connector
        self._ancestors_cache: Optional[List[WOFAncestor]] = None
        self._descendants_cache: Optional[List[WOFPlace]] = None

    @property
    def root(self) -> WOFPlace:
        """Get the root place."""
        return self._root

    async def fetch_ancestors(self, include_geometry: bool = False) -> List[WOFPlace]:
        """
        Fetch all ancestors of the root place.

        Args:
            include_geometry: Whether to include geometries

        Returns:
            List of ancestor places
        """
        if self._ancestors_cache is None:
            self._ancestors_cache = await self._connector.get_ancestors(self._root.id)

        if include_geometry:
            # Fetch full details with geometry
            ancestor_ids = [a.id for a in self._ancestors_cache]
            return await self._connector.get_places(ancestor_ids, include_geometry=True)

        # Convert ancestors to places without geometry
        ancestor_ids = [a.id for a in self._ancestors_cache]
        return await self._connector.get_places(ancestor_ids, include_geometry=False)

    async def fetch_descendants(
        self, filters: Optional[WOFFilters] = None, include_geometry: bool = False
    ) -> List[WOFPlace]:
        """
        Fetch descendants of the root place.

        Args:
            filters: Optional filters for descendants
            include_geometry: Whether to include geometries

        Returns:
            List of descendant places
        """
        descendants = await self._connector.get_descendants(self._root.id, filters)

        if include_geometry:
            # Fetch full details with geometry
            desc_ids = [d.id for d in descendants]
            return await self._connector.get_places(desc_ids, include_geometry=True)

        return descendants

    async def fetch_children(
        self, placetype: Optional[str] = None, include_geometry: bool = False
    ) -> List[WOFPlace]:
        """
        Fetch immediate children of the root place.

        Args:
            placetype: Optional filter by place type
            include_geometry: Whether to include geometries

        Returns:
            List of child places
        """
        from wof_explorer.types import coerce_placetype

        coerced_placetype = coerce_placetype(placetype) if placetype else None
        filters = WOFFilters(placetype=coerced_placetype, max_depth=1)
        return await self.fetch_descendants(filters, include_geometry)

    async def fetch_siblings(self, include_geometry: bool = False) -> List[WOFPlace]:
        """
        Fetch siblings of the root place (same parent, same type).

        Args:
            include_geometry: Whether to include geometries

        Returns:
            List of sibling places
        """
        # Get the parent
        ancestors = await self.fetch_ancestors()
        if not ancestors:
            return []

        # Find immediate parent (first ancestor of different type)
        parent = None
        for ancestor in ancestors:
            if ancestor.placetype != self._root.placetype:
                parent = ancestor
                break

        if not parent:
            return []

        # Get siblings (children of parent with same type as root)
        filters = WOFFilters(placetype=self._root.placetype)
        siblings = await self._connector.get_descendants(parent.id, filters)

        # Exclude self
        siblings = [s for s in siblings if s.id != self._root.id]

        if include_geometry:
            sibling_ids = [s.id for s in siblings]
            return await self._connector.get_places(sibling_ids, include_geometry=True)

        return siblings

    async def build_tree(self, max_depth: Optional[int] = None) -> Dict[str, Any]:
        """
        Build a complete hierarchy tree.

        Args:
            max_depth: Maximum depth for descendants

        Returns:
            Dictionary representation of the hierarchy
        """
        ancestors = await self.fetch_ancestors()

        filters = WOFFilters(max_depth=max_depth) if max_depth else None
        descendants = await self.fetch_descendants(filters)

        return {
            "root": self._root.model_dump(),
            "ancestors": [a.model_dump() for a in ancestors],
            "descendants": [d.model_dump() for d in descendants],
            "stats": {
                "ancestor_count": len(ancestors),
                "descendant_count": len(descendants),
                "total_places": len(ancestors) + len(descendants) + 1,
            },
        }


class WOFBatchCursor:
    """
    Cursor for batch operations on multiple places.

    Provides efficient batch fetching and processing.
    """

    display: ClassVar[DisplayDescriptor] = DisplayDescriptor()

    def __init__(self, place_ids: List[int], connector: "WOFConnector"):
        """
        Initialize batch cursor.

        Args:
            place_ids: List of place IDs
            connector: Reference to the connector
        """
        self._place_ids = place_ids
        self._connector = connector
        self._places_cache: Optional[List[WOFPlace]] = None

    @property
    def place_ids(self) -> List[int]:
        """Get the list of place IDs."""
        return self._place_ids

    @property
    def count(self) -> int:
        """Get the number of places."""
        return len(self._place_ids)

    async def fetch_all(self, include_geometry: bool = False) -> List[WOFPlace]:
        """
        Fetch all places in the batch.

        Args:
            include_geometry: Whether to include geometries

        Returns:
            List of places with full details
        """
        if self._places_cache is None or include_geometry:
            self._places_cache = await self._connector.get_places(
                self._place_ids, include_geometry
            )
        return self._places_cache

    async def fetch_hierarchies(self) -> List[Dict[str, Any]]:
        """
        Fetch hierarchy information for all places in batch.

        Returns:
            List of hierarchy data for each place
        """
        hierarchies = []

        for place_id in self._place_ids:
            ancestors = await self._connector.get_ancestors(place_id)
            hierarchies.append(
                {"place_id": place_id, "ancestors": [a.model_dump() for a in ancestors]}
            )

        return hierarchies

    async def process_in_chunks(
        self, chunk_size: int = 100, include_geometry: bool = False
    ):
        """
        Process places in chunks for memory efficiency.

        Args:
            chunk_size: Size of each chunk
            include_geometry: Whether to include geometries

        Yields:
            Chunks of places
        """
        for i in range(0, len(self._place_ids), chunk_size):
            chunk_ids = self._place_ids[i : i + chunk_size]
            chunk_places = await self._connector.get_places(chunk_ids, include_geometry)
            yield chunk_places
