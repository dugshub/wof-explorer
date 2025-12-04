"""
Contract tests for WOF cursor behavior.

Cursors provide lazy-loading access to search results and must implement
a consistent interface across all backends.
"""

import pytest
from typing import Protocol

from wof_explorer.models.filters import WOFSearchFilters
from wof_explorer.models.places import WOFPlace
from wof_explorer.processing.collections import PlaceCollection


class WOFCursorProtocol(Protocol):
    """Protocol defining the cursor interface."""

    @property
    def total_count(self) -> int:
        """Total number of results."""
        ...

    @property
    def query_filters(self) -> dict:
        """Filters used for this search."""
        ...

    @property
    def has_results(self) -> bool:
        """Whether search returned any results."""
        ...

    async def fetch_all(self, include_geometry: bool = False) -> PlaceCollection:
        """Fetch all results as a collection."""
        ...

    async def fetch_one(self, index: int = 0, include_geometry: bool = False):
        """Fetch a single result by index."""
        ...

    def __len__(self) -> int:
        """Return number of results."""
        ...

    def __getitem__(self, index: int):
        """Get a place by index."""
        ...

    def __iter__(self):
        """Iterate over places."""
        ...


class BaseWOFCursorContract:
    """
    Contract tests for cursor behavior that all backends must implement.

    To test a backend's cursors, inherit from this class and provide
    the 'connector' fixture.
    """

    @pytest.fixture
    def connector(self):
        """
        Fixture that provides the connector to test.
        Must be overridden by backend-specific test classes.
        """
        raise NotImplementedError("Backend must provide 'connector' fixture")

    # ============= CURSOR PROPERTIES =============

    @pytest.mark.asyncio
    async def test_cursor_properties(self, connector):
        """Cursor must provide basic properties."""
        await connector.connect()

        cursor = await connector.search(WOFSearchFilters(limit=10))

        # Required properties
        assert hasattr(cursor, "total_count")
        assert isinstance(cursor.total_count, int)
        assert cursor.total_count >= 0

        assert hasattr(cursor, "query_filters")
        assert isinstance(cursor.query_filters, dict)

        assert hasattr(cursor, "has_results")
        assert isinstance(cursor.has_results, bool)

    @pytest.mark.asyncio
    async def test_cursor_preserves_filters(self, connector):
        """Cursor must preserve the original query filters."""
        await connector.connect()

        filters = WOFSearchFilters(placetype="locality", country="CA", limit=5)

        cursor = await connector.search(filters)

        # Cursor should preserve filter information
        assert cursor.query_filters["placetype"] == "locality"
        assert cursor.query_filters["country"] == "CA"
        assert cursor.query_filters["limit"] == 5

    # ============= CURSOR ITERATION =============

    @pytest.mark.asyncio
    async def test_cursor_is_iterable(self, connector):
        """Cursors must be iterable."""
        await connector.connect()

        cursor = await connector.search(WOFSearchFilters(limit=10))

        # Should be able to iterate
        count = 0
        for place in cursor:
            assert isinstance(place, WOFPlace)
            assert hasattr(place, "id")
            assert hasattr(place, "name")
            count += 1

        assert count <= 10

    @pytest.mark.asyncio
    async def test_cursor_supports_len(self, connector):
        """Cursors must support len()."""
        await connector.connect()

        cursor = await connector.search(WOFSearchFilters(limit=5))

        # Should support len()
        length = len(cursor)
        assert isinstance(length, int)
        assert length >= 0
        assert length <= 5

    @pytest.mark.asyncio
    async def test_cursor_supports_indexing(self, connector):
        """Cursors must support index access."""
        await connector.connect()

        cursor = await connector.search(WOFSearchFilters(limit=5))

        if len(cursor) > 0:
            # Should support indexing
            first_place = cursor[0]
            assert isinstance(first_place, WOFPlace)

            # Should support negative indexing
            last_place = cursor[-1]
            assert isinstance(last_place, WOFPlace)

    @pytest.mark.asyncio
    async def test_cursor_index_out_of_bounds(self, connector):
        """Cursor should handle out of bounds indexing appropriately."""
        await connector.connect()

        cursor = await connector.search(WOFSearchFilters(limit=1))

        # Should raise IndexError for out of bounds
        with pytest.raises(IndexError):
            _ = cursor[100]

    # ============= FETCH OPERATIONS =============

    @pytest.mark.asyncio
    async def test_cursor_fetch_all(self, connector):
        """Cursor must support fetch_all operation."""
        await connector.connect()

        cursor = await connector.search(WOFSearchFilters(limit=10))

        collection = await cursor.fetch_all()

        # Must return a PlaceCollection
        assert isinstance(collection, PlaceCollection)
        assert hasattr(collection, "places")
        assert isinstance(collection.places, list)

        # All items must be WOFPlace instances
        for place in collection.places:
            assert isinstance(place, WOFPlace)

        # Should respect limit
        assert len(collection.places) <= 10

    @pytest.mark.asyncio
    async def test_cursor_fetch_all_with_geometry(self, connector):
        """Cursor must support fetching with geometry."""
        await connector.connect()

        cursor = await connector.search(
            WOFSearchFilters(placetype="neighbourhood", limit=5)
        )

        collection = await cursor.fetch_all(include_geometry=True)

        # Should have geometry attribute on places
        for place in collection.places:
            assert hasattr(place, "geometry")
            # Geometry might be None if not available,
            # but the attribute should exist

    @pytest.mark.asyncio
    async def test_cursor_fetch_one(self, connector):
        """Cursor must support fetching single items."""
        await connector.connect()

        cursor = await connector.search(WOFSearchFilters(limit=10))

        if hasattr(cursor, "fetch_one") and len(cursor) > 0:
            # Fetch first item
            place = await cursor.fetch_one(0)
            assert isinstance(place, WOFPlace)

            # Fetch with geometry
            place_with_geom = await cursor.fetch_one(0, include_geometry=True)
            assert hasattr(place_with_geom, "geometry")

    @pytest.mark.asyncio
    async def test_cursor_fetch_slice(self, connector):
        """Cursor might support slice fetching."""
        await connector.connect()

        cursor = await connector.search(WOFSearchFilters(limit=20))

        if hasattr(cursor, "fetch_slice"):
            # Fetch a slice of results
            slice_collection = await cursor.fetch_slice(5, 10)

            assert isinstance(slice_collection, PlaceCollection)
            assert len(slice_collection.places) <= 5

    # ============= EMPTY RESULTS =============

    @pytest.mark.asyncio
    async def test_cursor_empty_results(self, connector):
        """Cursor must handle empty results gracefully."""
        await connector.connect()

        # Search for something that likely doesn't exist
        cursor = await connector.search(
            WOFSearchFilters(name="ThisPlaceDefinitelyDoesNotExist123456789")
        )

        # Should handle empty results
        assert cursor.has_results is False
        assert cursor.total_count == 0
        assert len(cursor) == 0

        # Fetch all should return empty collection
        collection = await cursor.fetch_all()
        assert len(collection.places) == 0

        # Iteration should work but yield nothing
        count = 0
        for _ in cursor:
            count += 1
        assert count == 0

    # ============= CURSOR STATE =============

    @pytest.mark.asyncio
    async def test_cursor_is_immutable(self, connector):
        """Cursor results should be immutable after creation."""
        await connector.connect()

        cursor = await connector.search(WOFSearchFilters(limit=5))

        # Get initial count
        initial_count = cursor.total_count

        # Fetch all shouldn't change cursor state
        _ = await cursor.fetch_all()

        # Cursor should still have same count
        assert cursor.total_count == initial_count

    @pytest.mark.asyncio
    async def test_cursor_multiple_iterations(self, connector):
        """Cursor should support multiple iterations."""
        await connector.connect()

        cursor = await connector.search(WOFSearchFilters(limit=5))

        # First iteration
        first_ids = [place.id for place in cursor]

        # Second iteration should yield same results
        second_ids = [place.id for place in cursor]

        assert first_ids == second_ids

    @pytest.mark.asyncio
    async def test_cursor_concurrent_fetch(self, connector):
        """Cursor should handle concurrent fetch operations."""
        await connector.connect()

        cursor = await connector.search(WOFSearchFilters(limit=10))

        # Concurrent fetches should work
        import asyncio

        results = await asyncio.gather(
            cursor.fetch_all(),
            cursor.fetch_all(include_geometry=True),
        )

        # Both should return valid collections
        assert all(isinstance(r, PlaceCollection) for r in results)

    # ============= CURSOR METADATA =============

    @pytest.mark.asyncio
    async def test_cursor_provides_metadata(self, connector):
        """Cursor should provide search metadata."""
        await connector.connect()

        cursor = await connector.search(
            WOFSearchFilters(placetype="locality", country="CA")
        )

        # Should have access to original search context
        assert cursor.query_filters is not None

        # Should indicate result availability
        if cursor.total_count > 0:
            assert cursor.has_results is True
        else:
            assert cursor.has_results is False

    @pytest.mark.asyncio
    async def test_cursor_places_property(self, connector):
        """Cursor should provide direct access to places."""
        await connector.connect()

        cursor = await connector.search(WOFSearchFilters(limit=5))

        # Should have places property for simple access
        if hasattr(cursor, "places"):
            places = cursor.places
            assert isinstance(places, list)
            assert all(isinstance(p, WOFPlace) for p in places)
