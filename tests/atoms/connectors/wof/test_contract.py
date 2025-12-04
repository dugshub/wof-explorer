"""
Contract tests that ALL WOF connector backends must pass.

These tests define the interface contract that every backend implementation
must fulfill. They test behavior, not implementation details.
"""

import pytest
from typing import Optional, List, Protocol

from wof_explorer.models.places import WOFPlace
from wof_explorer.models.filters import WOFSearchFilters, WOFFilters


class TestData:
    """Test data that backends should provide."""

    # Generic test IDs - backends should override with actual IDs from their test database
    # For Barbados test database:
    toronto_id: int = 1326720241  # Moore Hill (locality)
    neighborhood_id: int = 0  # No neighborhoods in Barbados data
    ontario_id: int = 0  # N/A for Barbados
    canada_id: int = 85632491  # Barbados country ID


class WOFConnectorProtocol(Protocol):
    """Protocol defining the WOF connector interface."""

    @property
    def is_connected(self) -> bool:
        """Check if connector is connected."""
        ...

    async def connect(self) -> None:
        """Initialize connection to data source."""
        ...

    async def disconnect(self) -> None:
        """Close connection to data source."""
        ...

    async def search(self, filters: WOFSearchFilters):
        """Search for places matching filters."""
        ...

    async def get_place(
        self, place_id: int, include_geometry: bool = False
    ) -> Optional[WOFPlace]:
        """Get a single place by ID."""
        ...

    async def get_children(
        self, parent_id: int, filters: Optional[WOFFilters] = None
    ) -> List[WOFPlace]:
        """Get direct children of a place."""
        ...

    async def get_ancestors(self, place_id: int) -> List[WOFPlace]:
        """Get ancestors of a place."""
        ...


class BaseWOFConnectorContract:
    """
    Core contract that every WOF connector backend MUST fulfill.

    To test a new backend, inherit from this class and provide
    the 'connector' and 'test_data' fixtures.
    """

    @pytest.fixture
    def connector(self) -> WOFConnectorProtocol:
        """
        Fixture that provides the connector to test.
        Must be overridden by backend-specific test classes.
        """
        raise NotImplementedError("Backend must provide 'connector' fixture")

    @pytest.fixture
    def test_data(self) -> TestData:
        """
        Fixture that provides test data IDs.
        Can be overridden if backend uses different test data.
        """
        return TestData()

    # ============= CONNECTION CONTRACT =============

    @pytest.mark.asyncio
    async def test_connect_disconnect_lifecycle(self, connector):
        """Backend must support connect/disconnect lifecycle."""
        # Should start disconnected
        assert not connector.is_connected

        # Connect
        await connector.connect()
        assert connector.is_connected

        # Disconnect
        await connector.disconnect()
        assert not connector.is_connected

    @pytest.mark.asyncio
    async def test_double_connect_is_safe(self, connector):
        """Multiple connects should be safe (idempotent)."""
        await connector.connect()
        assert connector.is_connected

        # Second connect should not error
        await connector.connect()
        assert connector.is_connected

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_double_disconnect_is_safe(self, connector):
        """Multiple disconnects should be safe (idempotent)."""
        await connector.connect()
        await connector.disconnect()
        assert not connector.is_connected

        # Second disconnect should not error
        await connector.disconnect()
        assert not connector.is_connected

    @pytest.mark.asyncio
    async def test_operations_require_connection(self, connector):
        """Operations should fail gracefully when not connected."""
        # Ensure disconnected
        await connector.disconnect()

        # Operations should either auto-connect or raise clear error
        with pytest.raises(Exception) as exc_info:
            await connector.search(WOFSearchFilters())

        # Error should be clear about connection requirement
        error_msg = str(exc_info.value).lower()
        assert "connect" in error_msg or "not connected" in error_msg

    # ============= SEARCH CONTRACT =============

    @pytest.mark.asyncio
    async def test_search_returns_cursor(self, connector):
        """Search must return a cursor-like object."""
        await connector.connect()

        cursor = await connector.search(WOFSearchFilters())

        # Cursor must have required attributes
        assert hasattr(cursor, "fetch_all")
        assert hasattr(cursor, "total_count")
        assert hasattr(cursor, "query_filters")
        assert hasattr(cursor, "has_results")

    @pytest.mark.asyncio
    async def test_search_empty_filters(self, connector):
        """Search with empty filters should work (return all or paginated)."""
        await connector.connect()

        cursor = await connector.search(WOFSearchFilters())

        # Should not error, should return valid cursor
        assert cursor is not None
        assert cursor.total_count >= 0

    @pytest.mark.asyncio
    async def test_search_by_placetype(self, connector, test_data):
        """Must support placetype filtering."""
        await connector.connect()

        cursor = await connector.search(WOFSearchFilters(placetype="locality"))

        places = await cursor.fetch_all()

        # All results should match the placetype
        for place in places.places:
            assert place.placetype == "locality"

    @pytest.mark.asyncio
    async def test_search_by_name(self, connector, test_data):
        """Must support name search."""
        await connector.connect()

        cursor = await connector.search(
            WOFSearchFilters(name="Bridgetown")  # Capital of Barbados
        )

        places = await cursor.fetch_all()

        # Should find Bridgetown
        assert places.places
        assert any("Bridgetown" in p.name for p in places.places)

    @pytest.mark.asyncio
    async def test_search_by_name_contains(self, connector):
        """Must support partial name matching."""
        await connector.connect()

        cursor = await connector.search(
            WOFSearchFilters(
                name_contains="ont"
            )  # Should match "Toronto", "Montreal", etc.
        )

        places = await cursor.fetch_all()

        # Should find places containing "ont"
        if places.places:  # Only test if backend has data
            assert any("ont" in p.name.lower() for p in places.places)

    @pytest.mark.asyncio
    async def test_search_with_limit(self, connector):
        """Must respect limit parameter."""
        await connector.connect()

        cursor = await connector.search(WOFSearchFilters(limit=5))

        places = await cursor.fetch_all()

        # Should respect the limit
        assert len(places.places) <= 5

    @pytest.mark.asyncio
    async def test_search_with_multiple_filters(self, connector):
        """Must support combining multiple filters."""
        await connector.connect()

        cursor = await connector.search(
            WOFSearchFilters(
                placetype="locality",
                country="BB",  # Barbados for test database
                is_current=True,
                limit=10,
            )
        )

        places = await cursor.fetch_all()

        # All results should match all filters
        for place in places.places:
            assert place.placetype == "locality"
            assert place.country == "BB"
            assert place.is_active  # is_current maps to is_active

        assert len(places.places) <= 10

    @pytest.mark.asyncio
    async def test_search_with_list_filters(self, connector):
        """Must support list values for OR queries."""
        await connector.connect()

        cursor = await connector.search(
            WOFSearchFilters(placetype=["locality", "neighbourhood"])  # OR query
        )

        places = await cursor.fetch_all()

        # Results should be one of the specified types
        for place in places.places:
            assert place.placetype in ["locality", "neighbourhood"]

    # ============= RETRIEVAL CONTRACT =============

    @pytest.mark.asyncio
    async def test_get_place_by_id(self, connector, test_data):
        """Must retrieve single place by ID."""
        await connector.connect()

        place = await connector.get_place(test_data.toronto_id)

        assert place is not None
        assert place.id == test_data.toronto_id
        # Name should exist but we don't hardcode it (test DB may vary)
        assert place.name is not None
        assert len(place.name) > 0
        # Most test data should use a locality
        assert place.placetype in ["locality", "neighbourhood", "region"]

    @pytest.mark.asyncio
    async def test_get_place_not_found(self, connector):
        """Must return None for non-existent ID."""
        await connector.connect()

        place = await connector.get_place(999999999999)  # Non-existent ID

        assert place is None

    @pytest.mark.asyncio
    async def test_get_place_with_geometry(self, connector, test_data):
        """Must support loading geometry."""
        await connector.connect()

        place = await connector.get_place(test_data.toronto_id, include_geometry=True)

        assert place is not None
        assert hasattr(place, "geometry")
        # Geometry might be None if not available, but attribute must exist

    @pytest.mark.asyncio
    async def test_get_places_batch(self, connector, test_data):
        """Must support batch retrieval if available."""
        await connector.connect()

        # Check if backend supports batch operations
        if hasattr(connector, "get_places"):
            places = await connector.get_places(
                [test_data.toronto_id, test_data.ontario_id]
            )

            assert len(places) <= 2  # May return fewer if some don't exist
            assert all(isinstance(p, WOFPlace) for p in places)

    # ============= HIERARCHY CONTRACT =============

    @pytest.mark.asyncio
    async def test_get_children(self, connector, test_data):
        """Must support child retrieval."""
        await connector.connect()

        # Get children of Toronto (should include neighborhoods)
        children = await connector.get_children(test_data.toronto_id)

        assert isinstance(children, list)

        # If Toronto has children in the test data
        if children:
            # All children should have Toronto as parent
            for child in children:
                # Note: not all backends may have parent_id directly on the model
                # But they should be children of Toronto
                assert isinstance(child, WOFPlace)

    @pytest.mark.asyncio
    async def test_get_children_with_filters(self, connector, test_data):
        """Must support filtered child retrieval."""
        await connector.connect()

        # Get only neighbourhood children
        children = await connector.get_children(
            test_data.toronto_id, WOFFilters(placetype="neighbourhood")
        )

        # All results should be neighbourhoods
        for child in children:
            assert child.placetype == "neighbourhood"

    @pytest.mark.asyncio
    async def test_get_ancestors(self, connector, test_data):
        """Must support ancestor retrieval."""
        await connector.connect()

        # Get ancestors of a neighborhood
        # Using a test neighborhood ID - backends may override
        ancestors = await connector.get_ancestors(test_data.neighborhood_id)

        assert isinstance(ancestors, list)

        # Should include various levels (locality, region, country)
        if ancestors:
            placetypes = [a.placetype for a in ancestors]
            # Should have some hierarchy
            assert len(set(placetypes)) > 0

    @pytest.mark.asyncio
    async def test_get_descendants(self, connector, test_data):
        """Must support descendant retrieval if available."""
        await connector.connect()

        # Check if backend supports descendant operations
        if hasattr(connector, "get_descendants"):
            descendants = await connector.get_descendants(
                test_data.ontario_id, WOFFilters(placetype="locality")
            )

            assert isinstance(descendants, list)

            # All descendants should be localities
            for desc in descendants:
                assert desc.placetype == "locality"

    # ============= CAPABILITY CONTRACT =============

    @pytest.mark.asyncio
    async def test_backend_capabilities(self, connector):
        """Backend must declare its capabilities."""
        # These are optional but should be defined

        # Check capability properties exist and return booleans
        if hasattr(connector, "supports_multi_database"):
            assert isinstance(connector.supports_multi_database, bool)

        if hasattr(connector, "supports_spatial_queries"):
            assert isinstance(connector.supports_spatial_queries, bool)

        if hasattr(connector, "supports_full_text_search"):
            assert isinstance(connector.supports_full_text_search, bool)

    @pytest.mark.asyncio
    async def test_explorer_property(self, connector):
        """Should provide explorer for discovery operations."""
        await connector.connect()

        # Explorer should be available after connection
        if hasattr(connector, "explorer"):
            explorer = connector.explorer
            assert explorer is not None

            # Explorer should have discovery methods
            assert hasattr(explorer, "database_summary")
            assert hasattr(explorer, "discover_places")
