"""
Database operations for WOF SQLite backend.

Executes queries and transforms results.
Part of the SQLite backend refactoring following Infrastructure Subsystem Pattern.
"""

import json
import logging
from typing import Optional, List, Any, Union
from datetime import datetime

from sqlalchemy import select, and_
from sqlalchemy.engine import Row

from wof_explorer.models.places import WOFPlace, WOFPlaceWithGeometry, WOFAncestor
from wof_explorer.models.filters import WOFSearchFilters, WOFFilters
from wof_explorer.processing.cursors import WOFSearchCursor
from wof_explorer.types import PlaceType, coerce_placetype, normalize_placetype

from .session import SQLiteSessionManager
from .queries import SQLiteQueryBuilder
from .models import DBSearchResult, InternalSearchResult

logger = logging.getLogger(__name__)


class SQLiteOperations:
    """Executes database operations and transforms results."""

    def __init__(
        self,
        session_manager: SQLiteSessionManager,
        query_builder: SQLiteQueryBuilder,
        connector=None,
    ):
        """
        Initialize operations handler.

        Args:
            session_manager: Session manager for database connection
            query_builder: Query builder for SQL construction
            connector: Optional reference to parent connector for cursor operations
        """
        self.session = session_manager
        self.queries = query_builder
        self.connector = connector

    @staticmethod
    def _coerce_placetype(value: Any) -> PlaceType:
        """Convert raw database values to PlaceType with graceful fallback."""
        if value is None:
            return PlaceType.CUSTOM
        try:
            return coerce_placetype(value)
        except ValueError:
            normalized = normalize_placetype(str(value))
            try:
                return coerce_placetype(normalized)
            except ValueError:
                logger.warning("Unknown placetype '%s'; defaulting to custom", value)
                return PlaceType.CUSTOM

    async def execute_search(self, filters: WOFSearchFilters) -> WOFSearchCursor:
        """
        Execute search query and return cursor.

        Args:
            filters: Search filters to apply

        Returns:
            WOFSearchCursor for accessing results
        """
        import time

        start_time = time.time()

        # Get the engine
        engine = self.session.get_async_engine()
        if not engine:
            raise RuntimeError(
                "Not connected. Session manager must be connected first."
            )

        # Build the query
        query = self.queries.build_search_query(filters)

        # Execute query - Layer 1: DB Result
        async with engine.connect() as conn:
            result = await conn.execute(query)
            rows = result.fetchall()

        execution_time = (time.time() - start_time) * 1000  # ms

        # Create DB result
        db_result = DBSearchResult(
            rows=list(rows),
            total_count=len(rows),
            query_executed=str(query),
            execution_time_ms=execution_time,
            source_db=(
                str(self.session.db_path) if hasattr(self.session, "db_path") else None
            ),
        )

        # Transform to Layer 2: Internal Result
        places = [self.transform_row_to_place(row) for row in db_result.rows]

        internal_result = InternalSearchResult(
            places=places,
            total_count=db_result.total_count,
            returned_count=len(places),
            query_filters=filters.model_dump() if filters else {},
            metadata={
                "query_time_ms": execution_time,
                "source_db": db_result.source_db,
            },
        )

        # Return cursor with internal result (not public model)
        if not self.connector:
            raise RuntimeError(
                "Operations requires connector reference for cursor creation"
            )
        return WOFSearchCursor(internal_result, self.connector)

    async def execute_get_place(
        self, place_id: int, include_geometry: bool = False
    ) -> Optional[Union[WOFPlace, WOFPlaceWithGeometry]]:
        """
        Get single place by ID.

        Args:
            place_id: WhosOnFirst place ID
            include_geometry: Whether to include geometry data

        Returns:
            Place object or None if not found
        """
        # Build query
        query = self.queries.build_batch_query([place_id], include_geometry)

        # Get the engine
        engine = self.session.get_async_engine()
        if not engine:
            raise RuntimeError(
                "Not connected. Session manager must be connected first."
            )

        # Execute query
        async with engine.connect() as conn:
            result = await conn.execute(query)
            row = result.first()

        if row:
            # Transform and return
            if include_geometry and "geojson" in row._mapping:
                return self.transform_row_with_geometry(row)
            else:
                return self.transform_row_to_place(row)

        return None  # Place not found

    async def execute_hierarchy_query(
        self, place_id: int, direction: str, filters: Optional[WOFFilters] = None
    ) -> Union[List[WOFPlace], List[WOFAncestor]]:
        """
        Execute ancestor/descendant queries.

        Args:
            place_id: ID of the place
            direction: 'children', 'descendants', or 'ancestors'
            filters: Optional filters to apply

        Returns:
            List of places in hierarchy
        """
        # Special handling for ancestors
        if direction == "ancestors":
            return await self.execute_ancestors_query(place_id)

        # Build query for children/descendants
        query = self.queries.build_hierarchy_query(place_id, direction)

        # Apply additional filters if provided
        if filters:
            query = self.queries.apply_filters(query, self.queries.spr_table, filters)

        # Get the engine
        engine = self.session.get_async_engine()
        if not engine:
            raise RuntimeError(
                "Not connected. Session manager must be connected first."
            )

        # Execute query
        async with engine.connect() as conn:
            result = await conn.execute(query)
            rows = result.fetchall()

        # Transform rows to places
        places = [self.transform_row_to_place(row) for row in rows]
        return places

    async def execute_ancestors_query(self, place_id: int) -> List[WOFAncestor]:
        """
        Get ancestors of a place.

        Args:
            place_id: ID of the place

        Returns:
            List of ancestors ordered from immediate parent to root
        """
        # Get the engine
        engine = self.session.get_async_engine()
        if not engine:
            raise RuntimeError(
                "Not connected. Session manager must be connected first."
            )

        ancestors_table = self.queries.ancestors_table
        spr_table = self.queries.spr_table

        if ancestors_table is None or spr_table is None:
            logger.warning("Ancestors or SPR table not available for ancestors query")
            return []

        async with engine.connect() as conn:
            # Get all ancestor IDs for this place (excluding the place itself)
            ancestor_query = select(
                ancestors_table.c.ancestor_id, ancestors_table.c.ancestor_placetype
            ).where(
                and_(
                    ancestors_table.c.id == place_id,
                    ancestors_table.c.ancestor_id != place_id,  # Exclude self
                )
            )
            result = await conn.execute(ancestor_query)
            ancestor_rows = result.fetchall()

            if not ancestor_rows:
                return []

            # Get place data for each ancestor
            ancestors = []
            # Define hierarchy levels
            hierarchy_order = [
                "neighbourhood",
                "locality",
                "borough",
                "county",
                "region",
                "country",
                "continent",
                "planet",
            ]

            for row in ancestor_rows:
                ancestor_id = row.ancestor_id
                ancestor_placetype = row.ancestor_placetype

                # Get the ancestor place data
                assert spr_table is not None  # Already checked above
                place_query = select(spr_table).where(spr_table.c.id == ancestor_id)
                result = await conn.execute(place_query)
                place_row = result.first()

                if place_row:
                    # Calculate level (0 = immediate parent, higher = more distant)
                    level = (
                        hierarchy_order.index(ancestor_placetype)
                        if ancestor_placetype in hierarchy_order
                        else 99
                    )

                    ancestor = WOFAncestor(
                        id=place_row.id,
                        name=place_row.name,
                        placetype=self._coerce_placetype(place_row.placetype),
                        country=(
                            place_row.country if hasattr(place_row, "country") else None
                        ),
                        level=level,
                    )
                    ancestors.append(ancestor)

            # Sort ancestors by hierarchy level (immediate parent first)
            ancestors.sort(key=lambda a: a.level)

        return ancestors

    async def execute_batch_query(
        self, place_ids: List[int], include_geometry: bool = False
    ) -> List[Union[WOFPlace, WOFPlaceWithGeometry]]:
        """
        Get multiple places by IDs.

        Args:
            place_ids: List of place IDs
            include_geometry: Whether to include geometry

        Returns:
            List of places (may be shorter than place_ids if some not found)
        """
        # SQLite has a limit of 999 variables in a single query
        # We need to chunk the IDs to avoid hitting this limit
        CHUNK_SIZE = 900  # Use 900 to be safe with the 999 limit

        places: List[Union[WOFPlace, WOFPlaceWithGeometry]] = []

        # Process in chunks if necessary
        if len(place_ids) > CHUNK_SIZE:
            for i in range(0, len(place_ids), CHUNK_SIZE):
                chunk_ids = place_ids[i : i + CHUNK_SIZE]

                # Build query for this chunk
                query = self.queries.build_batch_query(chunk_ids, include_geometry)

                # Get the engine
                engine = self.session.get_async_engine()
                if not engine:
                    raise RuntimeError(
                        "Not connected. Session manager must be connected first."
                    )

                # Execute query
                async with engine.connect() as conn:
                    result = await conn.execute(query)
                    rows = result.fetchall()

                # Transform rows for this chunk
                for row in rows:
                    place: Union[WOFPlace, WOFPlaceWithGeometry]
                    if include_geometry and "geojson" in row._mapping:
                        place = self.transform_row_with_geometry(row)
                    else:
                        place = self.transform_row_to_place(row)
                    places.append(place)
        else:
            # Original logic for small batches
            # Build query
            query = self.queries.build_batch_query(place_ids, include_geometry)

            # Get the engine
            engine = self.session.get_async_engine()
            if not engine:
                raise RuntimeError(
                    "Not connected. Session manager must be connected first."
                )

            # Execute query
            async with engine.connect() as conn:
                result = await conn.execute(query)
                rows = result.fetchall()

            # Transform rows
            for row in rows:
                current_place: Union[WOFPlace, WOFPlaceWithGeometry]
                if include_geometry and "geojson" in row._mapping:
                    current_place = self.transform_row_with_geometry(row)
                else:
                    current_place = self.transform_row_to_place(row)
                places.append(current_place)

        return places

    def transform_row_to_place(self, row: Row) -> WOFPlace:
        """
        Transform database row to WOFPlace model.

        Args:
            row: SQLAlchemy result row

        Returns:
            WOFPlace model instance
        """
        # Handle superseded_by and supersedes fields
        superseded_by = row.superseded_by if hasattr(row, "superseded_by") else None
        supersedes = row.supersedes if hasattr(row, "supersedes") else None

        # Convert from string representation to list if needed
        if superseded_by and isinstance(superseded_by, str):
            try:
                superseded_by = json.loads(superseded_by) if superseded_by != "" else []
            except (json.JSONDecodeError, TypeError):
                superseded_by = []

        if supersedes and isinstance(supersedes, str):
            try:
                supersedes = json.loads(supersedes) if supersedes != "" else []
            except (json.JSONDecodeError, TypeError):
                supersedes = []

        # Handle bbox
        bbox = None
        if all(hasattr(row, f) for f in ["min_lon", "min_lat", "max_lon", "max_lat"]):
            if row.min_lon is not None and row.min_lat is not None:
                bbox = [row.min_lon, row.min_lat, row.max_lon, row.max_lat]

        # Convert lastmodified to datetime if needed
        lastmodified = None
        if hasattr(row, "lastmodified") and row.lastmodified:
            if isinstance(row.lastmodified, str):
                try:
                    lastmodified = datetime.fromisoformat(
                        row.lastmodified.replace(" ", "T")
                    )
                except (ValueError, AttributeError):
                    lastmodified = None
            elif isinstance(row.lastmodified, datetime):
                lastmodified = row.lastmodified
            elif isinstance(row.lastmodified, (int, float)):
                # Unix timestamp
                try:
                    lastmodified = datetime.fromtimestamp(row.lastmodified)
                except (ValueError, OSError):
                    lastmodified = None

        # Handle centroid for compatibility with latitude/longitude properties
        centroid = None
        if hasattr(row, "latitude") and hasattr(row, "longitude"):
            if row.longitude is not None and row.latitude is not None:
                centroid = [row.longitude, row.latitude]

        # Handle status fields - convert to datetime for deprecated/cessation
        deprecated = None
        if hasattr(row, "is_deprecated") and row.is_deprecated:
            # For now, use a default datetime if deprecated is true
            deprecated = datetime.now()

        cessation = None
        if hasattr(row, "is_ceased") and row.is_ceased:
            # For now, use a default datetime if ceased is true
            cessation = datetime.now()

        return WOFPlace(
            id=row.id,
            parent_id=row.parent_id if hasattr(row, "parent_id") else None,
            name=row.name,
            placetype=self._coerce_placetype(row.placetype),
            country=row.country if hasattr(row, "country") else None,
            repo=row.repo if hasattr(row, "repo") else None,
            centroid=centroid,
            bbox=bbox,
            is_current=bool(row.is_current) if hasattr(row, "is_current") else True,
            deprecated=deprecated,
            cessation=cessation,
            superseded_by=superseded_by or [],
            supersedes=supersedes or [],
            lastmodified=lastmodified,
        )

    def transform_row_with_geometry(self, row: Row) -> WOFPlaceWithGeometry:
        """
        Transform database row to WOFPlaceWithGeometry model.

        Args:
            row: SQLAlchemy result row with geojson

        Returns:
            WOFPlaceWithGeometry model instance
        """
        # Get base place
        base = self.transform_row_to_place(row)

        # Parse geojson
        geojson = None
        if hasattr(row, "geojson") and row.geojson:
            try:
                geojson = json.loads(row.geojson)
            except (json.JSONDecodeError, TypeError):
                geojson = None

        return WOFPlaceWithGeometry(
            **base.model_dump(),
            geometry=geojson,  # Field is called 'geometry', not 'geojson'
        )
