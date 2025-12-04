"""
SQLite backend connector for WhosOnFirst.

Orchestrates session, queries, and operations.
This is the refactored thin orchestration layer following the
Infrastructure Subsystem Pattern.
"""

import logging
from typing import Optional, List, Dict, Any, Union
from pathlib import Path

from wof_explorer.base import WOFConnectorBase
from wof_explorer.models.places import WOFPlace, WOFPlaceWithGeometry, WOFAncestor
from wof_explorer.models.filters import WOFSearchFilters, WOFFilters
from wof_explorer.processing.cursors import WOFSearchCursor

from .session import SQLiteSessionManager
from .queries import SQLiteQueryBuilder
from .operations import SQLiteOperations

logger = logging.getLogger(__name__)


class SQLiteWOFConnector(WOFConnectorBase):
    """
    Thin orchestration layer for SQLite backend.

    Delegates actual work to specialized components:
    - session: Connection and database management
    - queries: SQL query construction
    - operations: Query execution and data transformation
    """

    def __init__(
        self, db_path: Optional[Union[str, Path, List[Union[str, Path]]]] = None
    ):
        """
        Initialize the WOF connector with single or multiple databases.

        Args:
            db_path: Path to WOF SQLite database file(s).
                    Can be a single path or list of paths.
                    If None, uses configuration default.
        """
        from wof_explorer.config import get_config

        # Get configuration
        self.config = get_config()

        # Determine database path(s)
        if db_path is not None:
            if isinstance(db_path, list):
                # Multiple databases provided
                db_paths = [Path(p) for p in db_path]
                self.db_path = db_paths[0]  # Primary database
            else:
                # Single database
                self.db_path = Path(db_path)
                db_paths = [self.db_path]
        else:
            # Use first configured database as default
            configured = self.config.get_configured_databases()
            if configured:
                self.db_path = configured[0]
                db_paths = [self.db_path]
            else:
                raise FileNotFoundError(
                    f"No WOF databases found in {self.config.data_dir}. "
                    "Set WOF_DATA_DIR or provide explicit path."
                )

        # Initialize base class with paths
        super().__init__(list(db_paths))

        # Validate database exists
        if not self.db_path.exists():
            raise FileNotFoundError(f"WOF database not found: {self.db_path}")

        # Initialize components
        self.session_manager = SQLiteSessionManager(self.db_path, self.config)
        self.query_builder: Optional[SQLiteQueryBuilder] = None
        self.operations: Optional[SQLiteOperations] = None

        # Store references needed by explorer
        self._tables: Optional[Dict[str, Any]] = None
        self._async_engine: Optional[Any] = None

        # Lazy-loaded explorer - note: base class handles this with proper type

    async def connect(self) -> None:
        """Initialize connection and components."""
        if self._connected:
            return

        # Connect via session manager
        engine = await self.session_manager.connect()
        self._async_engine = engine

        # Get tables
        tables = await self.session_manager.get_tables()
        self._tables = tables

        # Initialize query builder with tables
        self.query_builder = SQLiteQueryBuilder(tables)

        # Initialize operations with session, queries, and connector reference
        self.operations = SQLiteOperations(
            self.session_manager, self.query_builder, connector=self
        )

        self._connected = True
        logger.info(f"SQLite connector initialized with database: {self.db_path.name}")

    async def disconnect(self) -> None:
        """Disconnect and clean up resources."""
        if not self._connected:
            return

        await self.session_manager.disconnect()
        self._connected = False
        self._async_engine = None
        self._tables = None
        logger.info("SQLite connector disconnected")

    # ============= SEARCH OPERATIONS =============

    async def search(self, filters: WOFSearchFilters) -> WOFSearchCursor:
        """
        Search for places matching filters.

        Delegates to operations component.
        """
        self._ensure_connected()
        if self.operations is None:
            raise RuntimeError("Operations not initialized")
        return await self.operations.execute_search(filters)

    # ============= RETRIEVAL OPERATIONS =============

    async def get_place(
        self, place_id: int, include_geometry: bool = False
    ) -> Optional[Union[WOFPlace, WOFPlaceWithGeometry]]:
        """
        Get a single place by ID.

        Delegates to operations component.
        """
        self._ensure_connected()
        if self.operations is None:
            raise RuntimeError("Operations not initialized")
        return await self.operations.execute_get_place(place_id, include_geometry)

    async def get_places(
        self, place_ids: List[int], include_geometry: bool = False
    ) -> List[Union[WOFPlace, WOFPlaceWithGeometry]]:
        """
        Get multiple places by IDs.

        Delegates to operations component.
        """
        self._ensure_connected()
        if self.operations is None:
            raise RuntimeError("Operations not initialized")
        return await self.operations.execute_batch_query(place_ids, include_geometry)

    # ============= HIERARCHY OPERATIONS =============

    async def get_ancestors(self, place_id: int) -> List[WOFAncestor]:
        """
        Get ancestors of a place.

        Delegates to operations component.
        """
        self._ensure_connected()
        if self.operations is None:
            raise RuntimeError("Operations not initialized")
        return await self.operations.execute_ancestors_query(place_id)

    async def get_descendants(
        self, place_id: int, filters: Optional[WOFFilters] = None
    ) -> List[WOFPlace]:
        """
        Get all descendants of a place.

        Delegates to operations component.
        """
        self._ensure_connected()
        if self.operations is None:
            raise RuntimeError("Operations not initialized")
        result = await self.operations.execute_hierarchy_query(
            place_id, "descendants", filters
        )
        # Type cast to ensure return type is List[WOFPlace]
        return result  # type: ignore[return-value]

    async def get_children(
        self, place_id: int, filters: Optional[WOFFilters] = None
    ) -> List[WOFPlace]:
        """
        Get direct children of a place.

        Delegates to operations component.
        """
        self._ensure_connected()
        if self.operations is None:
            raise RuntimeError("Operations not initialized")
        result = await self.operations.execute_hierarchy_query(
            place_id, "children", filters
        )
        # Type cast to ensure return type is List[WOFPlace]
        return result  # type: ignore[return-value]

    # ============= UTILITIES =============

    def _ensure_connected(self) -> None:
        """Ensure connector is connected."""
        if not self._connected:
            raise RuntimeError("Not connected. Call connect() first.")

    # ============= EXPLORER PROPERTY =============
    # Note: Base class provides explorer property with proper typing

    # ============= BACKEND INFO =============

    @property
    def backend_type(self) -> str:
        """Backend identifier."""
        return "sqlite"

    @property
    def supports_spatial(self) -> bool:
        """Whether backend supports spatial queries."""
        return False  # Basic SQLite doesn't have spatial extensions

    @property
    def supports_multi_database(self) -> bool:
        """Whether backend supports multiple databases."""
        return False  # Removed multi-database support

    @property
    def databases(self) -> List[str]:
        """List of connected database identifiers."""
        if self._connected and self.db_path:
            return [self.db_path.stem]
        return []
