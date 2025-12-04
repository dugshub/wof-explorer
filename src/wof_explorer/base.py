"""
Abstract base class for WOF connectors.

Defines the interface that all WOF connector backends must implement.
Part of the Infrastructure Subsystems Pattern.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Union
from pathlib import Path
import warnings

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wof_explorer.discovery.explorer import WOFExplorer
    from wof_explorer.processing.cursors import WOFSearchCursor

from wof_explorer.models.places import (
    WOFPlace,
    WOFPlaceWithGeometry,
    WOFAncestor,
)
from wof_explorer.models.filters import (
    WOFSearchFilters,
    WOFFilters,
    WOFExpansion,
)


class WOFConnectorBase(ABC):
    """
    Abstract base class for WhosOnFirst data connectors.

    This class defines the contract that all backend implementations
    (SQLite, PostGIS, API, etc.) must fulfill. It's part of the
    Infrastructure Subsystems Pattern, allowing swappable backends.

    Attributes:
        db_paths: Path(s) to data source(s)
        is_multi_db: Whether using multiple databases
        is_connected: Whether currently connected
    """

    def __init__(
        self, db_paths: Optional[Union[str, Path, List[Union[str, Path]]]] = None
    ):
        """
        Initialize the connector.

        Args:
            db_paths: Path(s) to data source(s). Implementation-specific.
                     Could be file paths for SQLite, connection strings for PostGIS,
                     or API endpoints for remote backends.
        """
        # Convert to list of Paths for consistency
        if db_paths is None:
            self.db_paths = []
        elif isinstance(db_paths, (str, Path)):
            self.db_paths = [Path(db_paths)]
        else:
            self.db_paths = [Path(p) for p in db_paths]

        self.is_multi_db = len(self.db_paths) > 1
        self._connected = False

    # ============= ABSTRACT PROPERTIES =============

    @property
    def is_connected(self) -> bool:
        """Check if connector is connected to data source."""
        return self._connected

    # ============= CONNECTION MANAGEMENT =============

    @abstractmethod
    async def connect(self) -> None:
        """
        Initialize connection to data source.

        Must be idempotent (safe to call multiple times).
        Should set self._connected = True when successful.
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Close connection to data source.

        Must be idempotent (safe to call multiple times).
        Should set self._connected = False when complete.
        """
        pass

    def _ensure_connected(self) -> None:
        """
        Ensure connector is connected.

        Raises:
            RuntimeError: If not connected
        """
        if not self._connected:
            raise RuntimeError("Connector is not connected. Call connect() first.")

    # ============= SEARCH OPERATIONS =============

    @abstractmethod
    async def search(self, filters: WOFSearchFilters) -> "WOFSearchCursor":
        """
        Search for places matching filters.

        Args:
            filters: Search criteria including placetype, name, country, etc.

        Returns:
            WOFSearchCursor: Cursor for iterating over results

        Raises:
            RuntimeError: If not connected
        """
        pass

    # ============= RETRIEVAL OPERATIONS =============

    @abstractmethod
    async def get_place(
        self, place_id: int, include_geometry: bool = False
    ) -> Optional[Union[WOFPlace, WOFPlaceWithGeometry]]:
        """
        Get a single place by ID.

        Args:
            place_id: WhosOnFirst place ID
            include_geometry: Whether to include geometry data

        Returns:
            Place object or None if not found

        Raises:
            RuntimeError: If not connected
        """
        pass

    async def get_places(
        self, place_ids: List[int], include_geometry: bool = False
    ) -> List[Union[WOFPlace, WOFPlaceWithGeometry]]:
        """
        Get multiple places by IDs.

        Default implementation calls get_place for each ID.
        Backends can override for batch optimization.

        Args:
            place_ids: List of WhosOnFirst place IDs
            include_geometry: Whether to include geometry data

        Returns:
            List of place objects (excludes not found)
        """
        places = []
        for place_id in place_ids:
            place = await self.get_place(place_id, include_geometry)
            if place:
                places.append(place)
        return places

    # ============= HIERARCHY OPERATIONS =============

    @abstractmethod
    async def get_children(
        self, parent_id: int, filters: Optional[WOFFilters] = None
    ) -> List[WOFPlace]:
        """
        Get direct children of a place.

        Args:
            parent_id: Parent place ID
            filters: Optional filters to apply

        Returns:
            List of child places

        Raises:
            RuntimeError: If not connected
        """
        pass

    @abstractmethod
    async def get_ancestors(self, place_id: int) -> List[WOFAncestor]:
        """
        Get ancestors of a place (parent to root).

        Args:
            place_id: Place ID

        Returns:
            List of ancestors ordered from immediate parent to root

        Raises:
            RuntimeError: If not connected
        """
        pass

    async def get_descendants(
        self, ancestor_id: int, filters: Optional[WOFFilters] = None
    ) -> List[WOFPlace]:
        """
        Get all descendants of a place (recursive children).

        Default implementation can be overridden for optimization.

        Args:
            ancestor_id: Ancestor place ID
            filters: Optional filters to apply

        Returns:
            List of descendant places
        """
        # Default recursive implementation
        descendants = []
        children = await self.get_children(ancestor_id, filters)
        descendants.extend(children)

        # Recursively get descendants
        for child in children:
            child_descendants = await self.get_descendants(child.id, filters)
            descendants.extend(child_descendants)

        return descendants

    # ============= EXPLORER PROPERTY =============

    @property
    def explorer(self) -> "WOFExplorer":
        """
        Get explorer for discovery operations.

        Returns:
            WOFExplorer: Explorer instance for this connector
        """
        if not hasattr(self, "_explorer"):
            from wof_explorer.discovery.explorer import WOFExplorer

            self._explorer = WOFExplorer(self)
        return self._explorer

    # ============= CAPABILITY DECLARATIONS =============

    @property
    def supports_multi_database(self) -> bool:
        """Whether backend supports multiple databases."""
        return False

    @property
    def supports_spatial_queries(self) -> bool:
        """Whether backend supports spatial operations (ST_Within, etc.)."""
        return False

    @property
    def supports_full_text_search(self) -> bool:
        """Whether backend supports full text search."""
        return False

    @property
    def supports_async(self) -> bool:
        """Whether backend supports async operations."""
        return True

    @property
    def supports_transactions(self) -> bool:
        """Whether backend supports transactions."""
        return False

    @property
    def supports_batch_operations(self) -> bool:
        """Whether backend supports batch operations."""
        return False

    # ============= DEPRECATED METHODS (for compatibility) =============

    async def get_places_by_ids(
        self,
        place_ids: List[int],
        include_geometry: bool = False,
        expansion: Optional[WOFExpansion] = None,
    ) -> List[Union[WOFPlace, WOFPlaceWithGeometry]]:
        """
        DEPRECATED: Use get_places() instead.

        Kept for backward compatibility.
        """
        warnings.warn(
            "get_places_by_ids is deprecated and will be removed in v1.0. Use connector.get_places() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return await self.get_places(place_ids, include_geometry)

    async def database_summary(self) -> Dict[str, Any]:
        """
        DEPRECATED: Use explorer.database_summary() instead.

        Kept for backward compatibility.
        """
        warnings.warn(
            "database_summary is deprecated and will be removed in v1.0. Use connector.explorer.database_summary() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return await self.explorer.database_summary()

    async def discover_places(
        self,
        placetype: str,
        parent_id: Optional[int] = None,
        parent_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        DEPRECATED: Use explorer.discover_places() instead.

        Kept for backward compatibility.
        """
        warnings.warn(
            "discover_places is deprecated and will be removed in v1.0. Use connector.explorer.discover_places() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return await self.explorer.discover_places(
            placetype, parent_name, parent_id, limit
        )

    async def suggest_starting_points(self) -> Dict[str, Any]:
        """
        DEPRECATED: Use explorer.suggest_starting_points() instead.

        Kept for backward compatibility.
        """
        warnings.warn(
            "suggest_starting_points is deprecated and will be removed in v1.0. Use connector.explorer.suggest_starting_points() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return await self.explorer.suggest_starting_points()

    async def top_cities_by_coverage(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        DEPRECATED: Use explorer.top_cities_by_coverage() instead.

        Kept for backward compatibility.
        """
        warnings.warn(
            "top_cities_by_coverage is deprecated and will be removed in v1.0. Use connector.explorer.top_cities_by_coverage() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return await self.explorer.top_cities_by_coverage(limit)
