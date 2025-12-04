"""
WhosOnFirst data exploration and discovery tools.
Provides methods for understanding and navigating WOF databases.
"""

from typing import Dict, Any, List, Optional, TYPE_CHECKING
from sqlalchemy import select, func, and_

from wof_explorer.models.filters import WOFSearchFilters
from wof_explorer.types import PlaceType, PlacetypeLike

if TYPE_CHECKING:
    from wof_explorer.base import WOFConnectorBase as WOFConnector


class WOFExplorer:
    """
    Discovery and exploration tools for WhosOnFirst data.

    This class provides methods for exploring WOF databases without
    prior knowledge of their contents, including summary statistics,
    discovery methods, and quality assessments.
    """

    def __init__(self, connector: "WOFConnector", engine=None, tables=None):
        """
        Initialize explorer with a connector instance.

        Args:
            connector: WOFConnector instance to use for data access
            engine: Optional async engine (for direct access)
            tables: Optional table definitions (for direct access)
        """
        self._connector = connector
        self._engine = engine
        self._direct_tables = tables

    # ============= Property access to connector internals =============
    # Using friend class pattern for clean access to connector's internals

    @property
    def _tables(self):
        """Access connector's table definitions."""
        return self._direct_tables or self._connector._tables

    @property
    def _async_engine(self):
        """Access connector's async engine."""
        return self._engine or self._connector._async_engine

    def _ensure_connected(self):
        """Ensure connector is connected."""
        return self._connector._ensure_connected()

    # ============= Discovery Methods =============

    async def database_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the connected database.

        Provides an overview of what's in the database including:
        - Total number of places
        - Breakdown by placetype
        - Breakdown by country
        - Breakdown by data source (repo)
        - Hierarchical coverage summary

        Returns:
            Dictionary with database statistics

        Example:
            >>> summary = await connector.explorer.database_summary()
            >>> print(f"Total places: {summary['total_places']}")
            >>> print(f"Countries: {list(summary['by_country'].keys())}")
        """
        self._ensure_connected()

        if not self._async_engine:
            return {
                "total_places": 0,
                "by_placetype": {},
                "by_country": {},
                "by_repo": {},
                "database": None,
            }

        spr = self._tables["spr"]

        async with self._async_engine.connect() as conn:
            # Count by placetype
            placetype_query = select(
                spr.c.placetype, func.count(spr.c.id).label("count")
            ).group_by(spr.c.placetype)

            placetype_result = await conn.execute(placetype_query)
            placetype_counts = {row.placetype: row.count for row in placetype_result}

            # Count by country
            country_query = (
                select(spr.c.country, func.count(spr.c.id).label("count"))
                .where(spr.c.country.isnot(None))
                .group_by(spr.c.country)
            )

            country_result = await conn.execute(country_query)
            country_counts = {row.country: row.count for row in country_result}

            # Count by repo
            repo_query = (
                select(spr.c.repo, func.count(spr.c.id).label("count"))
                .where(spr.c.repo.isnot(None))
                .group_by(spr.c.repo)
            )

            repo_result = await conn.execute(repo_query)
            repo_counts = {row.repo: row.count for row in repo_result}

            # Total count
            total_query = select(func.count(spr.c.id))
            total_result = await conn.execute(total_query)
            total_places = total_result.scalar() or 0

        return {
            "total_places": total_places,
            "by_placetype": placetype_counts,
            "by_country": country_counts,
            "by_repo": repo_counts,
            "database": (
                self._connector.db_path.stem
                if hasattr(self._connector, "db_path")
                else None
            ),
            "hierarchical_coverage": self._get_hierarchical_summary(placetype_counts),
        }

    async def discover_places(
        self,
        level: PlacetypeLike = PlaceType.COUNTRY,
        parent_name: Optional[str] = None,
        parent_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Discover places at a specific hierarchical level.

        Useful for exploring the database structure without knowing
        specific place names or IDs.

        Args:
            level: Placetype level to discover (default: country)
            parent_name: Optional parent name to filter by
            parent_id: Optional parent ID to filter by
            limit: Maximum number of results (default: 100)

        Returns:
            List of places with basic information

        Example:
            >>> # Discover all countries
            >>> countries = await connector.explorer.discover_places('country')
            >>>
            >>> # Discover regions in United States
            >>> us_regions = await connector.explorer.discover_places(
            ...     'region', parent_name='United States'
            ... )
        """
        self._ensure_connected()

        # Build filters
        from wof_explorer.types import coerce_placetype

        placetype = coerce_placetype(level) if level is not None else None
        filters = WOFSearchFilters(placetype=placetype, is_current=True, limit=limit)

        # Add parent filters if provided
        if parent_name:
            filters.ancestor_name = parent_name
        elif parent_id:
            filters.ancestor_id = parent_id

        # Search
        cursor = await self._connector.search(filters)
        places = await cursor.fetch_all()

        # Return simplified info
        return [
            {
                "id": p.id,
                "name": p.name,
                "placetype": (
                    p.placetype.value
                    if hasattr(p.placetype, "value")
                    else str(p.placetype)
                ),
                "country": p.country,
                "parent_id": p.parent_id,
            }
            for p in places.places
        ]

    async def top_cities_by_coverage(
        self, limit: int = 10, min_neighborhoods: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find cities with the best neighborhood coverage.

        Useful for finding well-mapped areas for testing or demonstration.

        Args:
            limit: Number of cities to return (default: 10)
            min_neighborhoods: Minimum neighborhoods required (default: 5)

        Returns:
            List of cities with neighborhood counts

        Example:
            >>> cities = await connector.explorer.top_cities_by_coverage()
            >>> for city in cities:
            ...     print(f"{city['name']}: {city['neighborhood_count']} neighborhoods")
        """
        self._ensure_connected()

        if not self._tables or "spr" not in self._tables:
            return []

        spr = self._tables["spr"]

        async with self._async_engine.connect() as conn:
            # Subquery to count neighborhoods per locality
            neighborhood_counts = (
                select(
                    spr.c.parent_id.label("locality_id"),
                    func.count(spr.c.id).label("neighborhood_count"),
                )
                .where(and_(spr.c.placetype == "neighbourhood", spr.c.is_current == 1))
                .group_by(spr.c.parent_id)
                .subquery()
            )

            # Join with localities to get names
            query = (
                select(
                    spr.c.id,
                    spr.c.name,
                    spr.c.country,
                    neighborhood_counts.c.neighborhood_count,
                )
                .select_from(
                    spr.join(
                        neighborhood_counts,
                        spr.c.id == neighborhood_counts.c.locality_id,
                    )
                )
                .where(
                    and_(
                        spr.c.placetype == "locality",
                        spr.c.is_current == 1,
                        neighborhood_counts.c.neighborhood_count >= min_neighborhoods,
                    )
                )
                .order_by(neighborhood_counts.c.neighborhood_count.desc())
                .limit(limit)
            )

            result = await conn.execute(query)

            cities = []
            for row in result:
                cities.append(
                    {
                        "id": row.id,
                        "name": row.name,
                        "country": row.country,
                        "neighborhood_count": row.neighborhood_count,
                    }
                )

        return cities

    async def suggest_starting_points(self) -> Dict[str, Any]:
        """
        Suggest good starting points for exploring the data.

        Returns places that are good examples for testing or demonstration,
        including:
        - A well-connected place with full hierarchy
        - Places with interesting properties
        - Examples of different placetypes

        Returns:
            Dictionary with suggested starting points

        Example:
            >>> suggestions = await connector.explorer.suggest_starting_points()
            >>> test_city = suggestions['well_mapped_city']
            >>> print(f"Try exploring {test_city['name']} (ID: {test_city['id']})")
        """
        self._ensure_connected()

        suggestions: dict[str, Any] = {}

        # Find a well-mapped city
        cities = await self.top_cities_by_coverage(limit=1)
        if cities:
            suggestions["well_mapped_city"] = cities[0]

        # Find example countries
        countries = await self.discover_places(PlaceType.COUNTRY, limit=5)
        if countries:
            suggestions["example_countries"] = countries

        # Find a place with complete hierarchy
        spr = self._tables["spr"]
        ancestors = self._tables.get("ancestors")

        if ancestors is not None:
            async with self._async_engine.connect() as conn:
                # Find a neighborhood that has ancestors at multiple hierarchy levels
                # The ancestors table has: id, ancestor_id, ancestor_placetype, lastmodified
                # We look for neighborhoods with at least country and locality ancestors
                query = (
                    select(spr.c.id, spr.c.name, spr.c.placetype)
                    .where(
                        and_(
                            spr.c.placetype == "neighbourhood",
                            spr.c.is_current == 1,
                            spr.c.parent_id.isnot(None),
                            spr.c.country.isnot(None),
                        )
                    )
                    .limit(1)
                )

                result = await conn.execute(query)
                row = result.first()

                if row:
                    suggestions["complete_hierarchy_example"] = {
                        "id": row.id,
                        "name": row.name,
                        "placetype": row.placetype,
                    }

        # Get placetype diversity
        summary = await self.database_summary()
        suggestions["available_placetypes"] = list(summary["by_placetype"].keys())
        suggestions["total_places"] = summary["total_places"]

        return suggestions

    async def check_data_quality(self, sample_size: int = 1000) -> Dict[str, Any]:
        """
        Assess data quality with various metrics.

        Samples the database to check:
        - Completeness of required fields
        - Percentage with coordinates
        - Percentage with valid geometries
        - Hierarchy completeness

        Args:
            sample_size: Number of records to sample (default: 1000)

        Returns:
            Dictionary with quality metrics

        Example:
            >>> quality = await connector.explorer.check_data_quality()
            >>> print(f"Coordinate coverage: {quality['coordinate_coverage']:.1%}")
        """
        self._ensure_connected()

        spr = self._tables["spr"]

        async with self._async_engine.connect() as conn:
            # Sample records
            sample_query = select(spr).limit(sample_size)
            result = await conn.execute(sample_query)
            rows = result.fetchall()

            if not rows:
                return {"error": "No data found"}

            # Calculate metrics
            total = len(rows)
            with_coords = sum(1 for r in rows if r.latitude and r.longitude)
            with_parent = sum(1 for r in rows if r.parent_id)
            with_country = sum(1 for r in rows if r.country)
            with_name = sum(1 for r in rows if r.name)
            current = sum(1 for r in rows if r.is_current)

            # Check geometry table if exists
            geom_coverage = 0.0
            if "geojson" in self._tables:
                geojson = self._tables["geojson"]
                geom_query = select(func.count(geojson.c.id))
                geom_result = await conn.execute(geom_query)
                geom_count = int(geom_result.scalar() or 0)

                total_query = select(func.count(spr.c.id))
                total_result = await conn.execute(total_query)
                total_count = int(total_result.scalar() or 1)

                geom_coverage = geom_count / total_count if total_count > 0 else 0

        return {
            "sample_size": total,
            "coordinate_coverage": with_coords / total if total > 0 else 0,
            "parent_id_coverage": with_parent / total if total > 0 else 0,
            "country_coverage": with_country / total if total > 0 else 0,
            "name_coverage": with_name / total if total > 0 else 0,
            "current_percentage": current / total if total > 0 else 0,
            "geometry_coverage": geom_coverage,
        }

    # ============= Helper Methods =============

    def _get_hierarchical_summary(
        self, placetype_counts: Dict[str, int]
    ) -> Dict[str, int]:
        """
        Get summary of hierarchical coverage.

        Args:
            placetype_counts: Dictionary of placetype counts

        Returns:
            Dictionary with counts at each hierarchical level
        """
        hierarchy = {
            "countries": 0,
            "regions": 0,
            "counties": 0,
            "localities": 0,
            "neighborhoods": 0,
        }

        for placetype, count in placetype_counts.items():
            if placetype == "country":
                hierarchy["countries"] += count
            elif placetype in ["region", "state", "province"]:
                hierarchy["regions"] += count
            elif placetype == "county":
                hierarchy["counties"] += count
            elif placetype in ["locality", "localadmin"]:
                hierarchy["localities"] += count
            elif placetype in ["neighbourhood", "neighborhood"]:
                hierarchy["neighborhoods"] += count

        return hierarchy
