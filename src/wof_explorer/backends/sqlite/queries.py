"""
SQL query builders for WOF SQLite backend.

Constructs SQLAlchemy queries for various search patterns.
Part of the SQLite backend refactoring following Infrastructure Subsystem Pattern.
"""

import logging
from typing import Optional, List, Dict, Any

from sqlalchemy import select, and_, or_, text, Table
from sqlalchemy.sql import Select

from wof_explorer.models.filters import WOFSearchFilters, WOFFilters
from wof_explorer.models.places import BBox

logger = logging.getLogger(__name__)


class SQLiteQueryBuilder:
    """Builds SQL queries for WOF data access."""

    def __init__(self, tables: Dict[str, Any]):
        """
        Initialize query builder with table references.

        Args:
            tables: Dictionary of SQLAlchemy table objects
        """
        self.tables = tables
        self.spr_table: Optional[Table] = tables.get("spr")
        self.names_table: Optional[Table] = tables.get("names")
        self.ancestors_table: Optional[Table] = tables.get("ancestors")
        self.geojson_table: Optional[Table] = tables.get("geojson")

        # Validate that required tables are present
        if self.spr_table is None:
            raise ValueError("Required 'spr' table not found in tables dictionary")

    def build_search_query(self, filters: WOFSearchFilters) -> Select:
        """
        Build search query with filters.

        Args:
            filters: Search filters to apply

        Returns:
            SQLAlchemy Select query
        """
        # Start with base query - spr_table is guaranteed to exist due to __init__ check
        if self.spr_table is None:
            raise RuntimeError("SPR table not initialized - call connect() first")
        query = select(self.spr_table)

        # Apply placetype filter
        if filters.placetype:
            if isinstance(filters.placetype, list):
                query = query.where(self.spr_table.c.placetype.in_(filters.placetype))
            else:
                query = query.where(self.spr_table.c.placetype == filters.placetype)

        # Apply name filter (search in both main name and alternative names)
        if filters.name:
            name_pattern = f"%{filters.name}%"
            name_conditions = [self.spr_table.c.name.ilike(name_pattern)]

            # Also search in alternative names if names table is available
            if self.names_table is not None:
                subquery = (
                    select(self.names_table.c.id)
                    .where(self.names_table.c.name.ilike(name_pattern))
                    .distinct()
                )
                name_conditions.append(self.spr_table.c.id.in_(subquery))

            query = query.where(or_(*name_conditions))

        # Apply country filter
        if filters.country:
            if isinstance(filters.country, list):
                query = query.where(self.spr_table.c.country.in_(filters.country))
            else:
                query = query.where(self.spr_table.c.country == filters.country)

        # Apply region filter
        if filters.region:
            if isinstance(filters.region, list):
                query = query.where(self.spr_table.c.region.in_(filters.region))
            else:
                query = query.where(self.spr_table.c.region == filters.region)

        # Apply parent filters
        if filters.parent_id:
            if isinstance(filters.parent_id, list):
                query = query.where(self.spr_table.c.parent_id.in_(filters.parent_id))
            else:
                query = query.where(self.spr_table.c.parent_id == filters.parent_id)

        if filters.parent_name:
            # Get parent IDs by name
            parent_names = (
                filters.parent_name
                if isinstance(filters.parent_name, list)
                else [filters.parent_name]
            )
            parent_subquery = select(self.spr_table.c.id).where(
                self.spr_table.c.name.in_(parent_names)
            )
            query = query.where(self.spr_table.c.parent_id.in_(parent_subquery))

        # Apply ancestor filters (search entire hierarchy)
        if filters.ancestor_id and self.ancestors_table is not None:
            ancestor_ids = (
                filters.ancestor_id
                if isinstance(filters.ancestor_id, list)
                else [filters.ancestor_id]
            )

            # Find places that have any of these ancestor_ids in their ancestry
            ancestor_subquery = (
                select(self.ancestors_table.c.id)
                .where(self.ancestors_table.c.ancestor_id.in_(ancestor_ids))
                .distinct()
            )
            query = query.where(self.spr_table.c.id.in_(ancestor_subquery))

        if filters.ancestor_name and self.ancestors_table is not None:
            # Get ancestor IDs by name
            ancestor_names = (
                filters.ancestor_name
                if isinstance(filters.ancestor_name, list)
                else [filters.ancestor_name]
            )
            ancestor_id_subquery = (
                select(self.spr_table.c.id)
                .where(self.spr_table.c.name.in_(ancestor_names))
                .distinct()
            )

            # Find all descendants of these ancestors using the ancestors table
            descendant_subquery = (
                select(self.ancestors_table.c.id)
                .where(self.ancestors_table.c.ancestor_id.in_(ancestor_id_subquery))
                .distinct()
            )
            query = query.where(self.spr_table.c.id.in_(descendant_subquery))

        # Apply status filters
        if filters.is_current is not None:
            query = query.where(
                self.spr_table.c.is_current == (1 if filters.is_current else 0)
            )

        if filters.is_deprecated is not None:
            query = query.where(
                self.spr_table.c.is_deprecated == (1 if filters.is_deprecated else 0)
            )

        if filters.is_ceased is not None:
            query = query.where(
                self.spr_table.c.is_ceased == (1 if filters.is_ceased else 0)
            )

        if filters.is_superseded is not None:
            query = query.where(
                self.spr_table.c.is_superseded == (1 if filters.is_superseded else 0)
            )

        if filters.is_superseding is not None:
            query = query.where(
                self.spr_table.c.is_superseding == (1 if filters.is_superseding else 0)
            )

        # Apply spatial filters
        if filters.bbox:
            query = self._apply_bbox_filter(query, filters.bbox)

        # Apply proximity filter using the individual fields
        if filters.near_lat is not None and filters.near_lon is not None:
            proximity = {
                "lat": filters.near_lat,
                "lon": filters.near_lon,
                "radius_km": filters.radius_km or 10,  # Default 10km radius
            }
            query = self._apply_proximity_filter(query, proximity)

        # Apply source filter (for multi-database)
        if filters.source and hasattr(self.spr_table.c, "source"):
            if isinstance(filters.source, list):
                query = query.where(self.spr_table.c.source.in_(filters.source))
            else:
                query = query.where(self.spr_table.c.source == filters.source)

        # Apply limit
        if filters.limit:
            query = query.limit(filters.limit)

        # Apply offset
        if filters.offset:
            query = query.offset(filters.offset)

        return query

    def build_hierarchy_query(
        self, place_id: int, direction: str = "children"
    ) -> Select:
        """
        Build ancestor/descendant queries.

        Args:
            place_id: ID of the place
            direction: 'children', 'descendants', or 'ancestors'

        Returns:
            SQLAlchemy Select query
        """
        if self.spr_table is None:
            raise RuntimeError("SPR table not initialized - call connect() first")

        if direction == "children":
            # Direct children only
            query = select(self.spr_table).where(self.spr_table.c.parent_id == place_id)
        elif direction == "descendants" and self.ancestors_table is not None:
            # All descendants using ancestors table
            # Find all places that have this place_id as an ancestor
            descendant_ids = (
                select(self.ancestors_table.c.id)
                .where(self.ancestors_table.c.ancestor_id == place_id)
                .distinct()
            )
            query = select(self.spr_table).where(
                self.spr_table.c.id.in_(descendant_ids)
            )
        else:
            # Empty result for unsupported direction or missing ancestors table
            query = select(self.spr_table).where(text("1=0"))

        return query

    def build_ancestors_query(self, place_id: int) -> Select:
        """
        Build query to get ancestors of a place.

        Args:
            place_id: ID of the place

        Returns:
            SQLAlchemy Select query for ancestors
        """
        if self.ancestors_table is None:
            # Return empty query if ancestors table not available
            if self.spr_table is None:
                raise RuntimeError("SPR table not initialized - call connect() first")
            return select(self.spr_table).where(text("1=0"))

        # First get the ancestor IDs from the ancestors table
        ancestor_row = select(self.ancestors_table).where(
            self.ancestors_table.c.id == place_id
        )

        # This needs to be executed first to get the IDs,
        # then we query the spr table for those IDs
        # This is handled in the operations layer
        return ancestor_row

    def build_batch_query(
        self, ids: List[int], include_geometry: bool = False
    ) -> Select:
        """
        Build batch retrieval query.

        Args:
            ids: List of place IDs
            include_geometry: Whether to include geometry

        Returns:
            SQLAlchemy Select query
        """
        if self.spr_table is None:
            raise RuntimeError("SPR table not initialized - call connect() first")

        if include_geometry and self.geojson_table is not None:
            # Join with geojson table
            query = (
                select(self.spr_table, self.geojson_table.c.body.label("geojson"))
                .select_from(
                    self.spr_table.join(
                        self.geojson_table,
                        self.spr_table.c.id == self.geojson_table.c.id,
                        isouter=True,
                    )
                )
                .where(self.spr_table.c.id.in_(ids))
            )
        else:
            # Just SPR data
            query = select(self.spr_table).where(self.spr_table.c.id.in_(ids))

        return query

    def apply_filters(
        self, query: Select, table: Optional[Table], filters: WOFFilters
    ) -> Select:
        """
        Apply WOF filters to a query.

        Args:
            query: Base query to modify
            table: Table to apply filters to
            filters: Filters to apply

        Returns:
            Modified query with filters applied
        """
        if not filters or table is None:
            return query

        # Apply placetype filter
        if filters.placetype:
            if isinstance(filters.placetype, list):
                query = query.where(table.c.placetype.in_(filters.placetype))
            else:
                query = query.where(table.c.placetype == filters.placetype)

        # Apply status filters
        if filters.is_current is not None:
            query = query.where(table.c.is_current == (1 if filters.is_current else 0))

        if filters.is_deprecated is not None:
            query = query.where(
                table.c.is_deprecated == (1 if filters.is_deprecated else 0)
            )

        if filters.is_ceased is not None:
            query = query.where(table.c.is_ceased == (1 if filters.is_ceased else 0))

        if filters.is_superseded is not None:
            query = query.where(
                table.c.is_superseded == (1 if filters.is_superseded else 0)
            )

        return query

    def build_spatial_query(
        self, bbox: Optional[BBox] = None, proximity: Optional[Dict[str, Any]] = None
    ) -> Select:
        """
        Build spatial queries (bbox, proximity).

        Args:
            bbox: Bounding box for spatial filter
            proximity: Proximity filter with lat, lon, radius

        Returns:
            SQLAlchemy Select query with spatial filters
        """
        if self.spr_table is None:
            raise RuntimeError("SPR table not initialized - call connect() first")
        query = select(self.spr_table)

        if bbox:
            query = self._apply_bbox_filter(query, bbox)

        if proximity:
            query = self._apply_proximity_filter(query, proximity)

        return query

    def build_text_search_query(
        self, search_text: str, fields: Optional[List[str]] = None
    ) -> Select:
        """
        Build full-text search queries.

        Args:
            search_text: Text to search for
            fields: Fields to search in (default: name fields)

        Returns:
            SQLAlchemy Select query
        """
        if self.spr_table is None:
            raise RuntimeError("SPR table not initialized - call connect() first")

        if not fields:
            fields = ["name"]

        search_pattern = f"%{search_text}%"
        conditions = []

        for field in fields:
            if hasattr(self.spr_table.c, field):
                conditions.append(
                    getattr(self.spr_table.c, field).ilike(search_pattern)
                )

        if conditions:
            query = select(self.spr_table).where(or_(*conditions))
        else:
            # No matching fields, return empty
            query = select(self.spr_table).where(text("1=0"))

        return query

    def _apply_bbox_filter(self, query: Select, bbox: BBox) -> Select:
        """Apply bounding box filter to query."""
        # SQLite doesn't have native spatial support,
        # so we use simple coordinate comparison
        # BBox is a tuple: (min_lon, min_lat, max_lon, max_lat)
        if self.spr_table is None:
            raise RuntimeError("SPR table not initialized - call connect() first")
        min_lon, min_lat, max_lon, max_lat = bbox
        return query.where(
            and_(
                self.spr_table.c.latitude >= min_lat,
                self.spr_table.c.latitude <= max_lat,
                self.spr_table.c.longitude >= min_lon,
                self.spr_table.c.longitude <= max_lon,
            )
        )

    def _apply_proximity_filter(
        self, query: Select, proximity: Dict[str, Any]
    ) -> Select:
        """Apply proximity filter to query."""
        if self.spr_table is None:
            raise RuntimeError("SPR table not initialized - call connect() first")

        lat = proximity.get("lat")
        lon = proximity.get("lon")
        radius_km = proximity.get("radius_km", 10)

        if lat is None or lon is None:
            return query

        # Approximate degrees per kilometer
        # This is a rough approximation that works reasonably well for small distances
        km_per_degree_lat = 111.0
        km_per_degree_lon = (
            111.0  # This varies by latitude, but we'll use a simple approximation
        )

        lat_range = radius_km / km_per_degree_lat
        lon_range = radius_km / km_per_degree_lon

        return query.where(
            and_(
                self.spr_table.c.latitude >= lat - lat_range,
                self.spr_table.c.latitude <= lat + lat_range,
                self.spr_table.c.longitude >= lon - lon_range,
                self.spr_table.c.longitude <= lon + lon_range,
            )
        )
