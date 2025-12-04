"""
Unit tests for WOF cursor classes.

Tests verify cursor behavior including search cursors, batch cursors,
and hierarchy cursors for the two-phase exploration pattern.
These tests focus on cursor-specific functionality, distinct from
the contract tests which verify interface compliance.
"""

import pytest
import pytest_asyncio
import asyncio
from pathlib import Path
import subprocess
import sys

from wof_explorer.backends.sqlite import SQLiteWOFConnector as WOFConnector
from wof_explorer.processing.cursors import (
    WOFSearchCursor,
    WOFBatchCursor,
    WOFHierarchyCursor,
)
from wof_explorer.models.filters import WOFSearchFilters, WOFFilters
from wof_explorer.models.places import WOFPlace
from wof_explorer.processing.collections import PlaceCollection

# Known Barbados test data
BARBADOS_COUNTRY_ID = 85632491
MOORE_HILL_LOCALITY_ID = 1326720241
SAINT_MICHAEL_REGION_ID = 85670295


@pytest.fixture(scope="session")
def test_db_path() -> Path:
    """
    Path to the test database.
    Downloads a small country database (Barbados) for fast testing.
    """
    # Use a dedicated test directory
    test_data_dir = Path(__file__).parent.parent.parent.parent / "wof-test-data"
    test_data_dir.mkdir(exist_ok=True)

    # Check if test database already exists
    test_db = test_data_dir / "whosonfirst-data-admin-bb-latest.db"

    if not test_db.exists():
        # Download Barbados (small country) for testing
        script_path = (
            Path(__file__).parent.parent.parent / "scripts" / "wof-download.py"
        )

        print("\n📥 Downloading test database (Barbados - small)...")
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--countries",
                    "bb",
                    "--output-dir",
                    str(test_data_dir),
                    "--no-combine",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                pytest.skip(f"Failed to download test database: {result.stderr}")

            if not test_db.exists():
                pytest.skip(f"Test database not found after download at {test_db}")

        except subprocess.TimeoutExpired:
            pytest.skip("Test database download timed out")
        except Exception as e:
            pytest.skip(f"Failed to download test database: {e}")

    return test_db


@pytest_asyncio.fixture
async def connector(test_db_path):
    """Provides connected WOF connector with automatic cleanup."""
    connector = WOFConnector(str(test_db_path))
    await connector.connect()
    yield connector
    await connector.disconnect()


class TestWOFSearchCursor:
    """Unit tests for WOFSearchCursor."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_search_cursor_initialization(self, connector):
        """Search cursor should initialize with result data."""
        cursor = await connector.search(WOFSearchFilters(limit=5))

        assert isinstance(cursor, WOFSearchCursor)
        assert hasattr(cursor, "_result")
        assert hasattr(cursor, "_connector")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_search_cursor_places_property(self, connector):
        """Search cursor places property should return list of WOFPlace."""
        cursor = await connector.search(WOFSearchFilters(limit=10))

        places = cursor.places
        assert isinstance(places, list)
        assert all(isinstance(p, WOFPlace) for p in places)
        assert len(places) <= 10

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_search_cursor_total_count_accuracy(self, connector):
        """Total count should reflect actual result count."""
        # Search with known filter
        cursor = await connector.search(WOFSearchFilters(placetype="locality"))

        assert isinstance(cursor.total_count, int)
        assert cursor.total_count >= 0

        # If we have results, verify count is consistent
        if cursor.has_results:
            assert cursor.total_count > 0
            assert len(cursor.places) <= cursor.total_count

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_search_cursor_metadata(self, connector):
        """Cursor should provide access to search metadata."""
        filters = WOFSearchFilters(placetype="locality", limit=5)
        cursor = await connector.search(filters)

        # Verify metadata is accessible
        assert cursor.query_filters is not None
        assert isinstance(cursor.query_filters, dict)
        assert cursor.query_filters["placetype"] == "locality"
        assert cursor.query_filters["limit"] == 5

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_search_cursor_has_results_flag(self, connector):
        """has_results flag should accurately reflect result state."""
        # Search with results
        cursor_with = await connector.search(WOFSearchFilters(limit=5))

        if cursor_with.total_count > 0:
            assert cursor_with.has_results is True
        else:
            assert cursor_with.has_results is False

        # Search without results
        cursor_empty = await connector.search(
            WOFSearchFilters(name="NonExistentPlace12345")
        )
        assert cursor_empty.has_results is False
        assert cursor_empty.total_count == 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_search_cursor_filter_places_method(self, connector):
        """filter_places should filter results by attributes."""
        cursor = await connector.search(WOFSearchFilters(limit=20))

        if len(cursor.places) > 0:
            # Get a placetype from the results
            sample_placetype = cursor.places[0].placetype

            # Filter by that placetype
            filtered = cursor.filter_places(placetype=sample_placetype)

            assert isinstance(filtered, list)
            assert all(p.placetype == sample_placetype for p in filtered)
            assert len(filtered) <= len(cursor.places)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_search_cursor_get_page_info(self, connector):
        """get_page_info should return correct pagination data."""
        cursor = await connector.search(WOFSearchFilters(limit=25))

        page_info = cursor.get_page_info(page_size=10)

        assert isinstance(page_info, dict)
        assert "total_count" in page_info
        assert "page_size" in page_info
        assert "total_pages" in page_info
        assert page_info["page_size"] == 10

        # Verify calculation
        expected_pages = (
            cursor.total_count // 10 + (1 if cursor.total_count % 10 else 0)
        )
        assert page_info["total_pages"] == expected_pages

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_search_cursor_fetch_page(self, connector):
        """fetch_page should return correct page of results."""
        cursor = await connector.search(WOFSearchFilters(limit=25))

        if cursor.total_count >= 10:
            # Fetch first page
            page1 = await cursor.fetch_page(page=1, size=10)

            assert isinstance(page1, PlaceCollection)
            assert len(page1.places) <= 10
            assert all(isinstance(p, WOFPlace) for p in page1.places)

            # Fetch second page
            if cursor.total_count > 10:
                page2 = await cursor.fetch_page(page=2, size=10)
                assert isinstance(page2, PlaceCollection)

                # Pages should have different content
                if len(page1.places) > 0 and len(page2.places) > 0:
                    assert page1.places[0].id != page2.places[0].id

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_search_cursor_fetch_by_ids(self, connector):
        """fetch_by_ids should fetch only specified IDs from cursor."""
        cursor = await connector.search(WOFSearchFilters(limit=10))

        if len(cursor.places) >= 3:
            # Get some IDs from the cursor
            target_ids = [cursor.places[0].id, cursor.places[2].id]

            # Fetch by IDs
            fetched = await cursor.fetch_by_ids(target_ids)

            assert isinstance(fetched, list)
            assert len(fetched) == 2
            assert all(p.id in target_ids for p in fetched)

            # Try with ID not in cursor
            invalid_ids = [999999999]
            fetched_invalid = await cursor.fetch_by_ids(invalid_ids)
            assert len(fetched_invalid) == 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_search_cursor_to_csv_rows(self, connector):
        """to_csv_rows should return CSV-friendly data."""
        cursor = await connector.search(WOFSearchFilters(limit=5))

        if cursor.has_results:
            rows = cursor.to_csv_rows()

            assert isinstance(rows, list)
            assert all(isinstance(row, dict) for row in rows)
            assert len(rows) == len(cursor.places)

            # Check expected columns
            if len(rows) > 0:
                row = rows[0]
                assert "id" in row
                assert "name" in row
                assert "placetype" in row
                assert "latitude" in row
                assert "longitude" in row

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_search_cursor_to_geojson_without_fetch(self, connector):
        """to_geojson should work with lightweight data (no fetch)."""
        cursor = await connector.search(WOFSearchFilters(limit=5))

        if cursor.has_results:
            geojson = await cursor.to_geojson(fetch_geometry=False)

            assert isinstance(geojson, dict)
            assert geojson["type"] == "FeatureCollection"
            assert "features" in geojson
            assert len(geojson["features"]) == len(cursor.places)

            # Verify point geometries
            for feature in geojson["features"]:
                assert feature["type"] == "Feature"
                assert feature["geometry"]["type"] == "Point"
                assert "coordinates" in feature["geometry"]


class TestWOFBatchCursor:
    """Unit tests for WOFBatchCursor."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_batch_cursor_from_ids(self, connector):
        """Batch cursor should initialize with place IDs."""
        ids = [BARBADOS_COUNTRY_ID, MOORE_HILL_LOCALITY_ID]
        batch = WOFBatchCursor(ids, connector)

        assert isinstance(batch, WOFBatchCursor)
        assert batch.place_ids == ids
        assert batch.count == 2

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_batch_cursor_fetch_all(self, connector):
        """fetch_all should return all places for given IDs."""
        ids = [BARBADOS_COUNTRY_ID, MOORE_HILL_LOCALITY_ID]
        batch = WOFBatchCursor(ids, connector)

        places = await batch.fetch_all()

        assert isinstance(places, list)
        assert len(places) == 2
        assert all(isinstance(p, WOFPlace) for p in places)
        assert all(p.id in ids for p in places)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_batch_cursor_fetch_all_with_geometry(self, connector):
        """fetch_all should support geometry fetching."""
        ids = [BARBADOS_COUNTRY_ID]
        batch = WOFBatchCursor(ids, connector)

        places = await batch.fetch_all(include_geometry=True)

        # Should return at least one place (may include alternate geometries)
        assert len(places) >= 1
        # All returned places should be for the requested ID
        assert all(p.id == BARBADOS_COUNTRY_ID for p in places)
        # Geometry should be included
        place = places[0]
        assert hasattr(place, "geometry")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_batch_cursor_process_in_chunks(self, connector):
        """process_in_chunks should yield chunks of results."""
        # Create batch with multiple IDs
        cursor = await connector.search(WOFSearchFilters(limit=20))
        if len(cursor.places) >= 10:
            ids = [p.id for p in cursor.places[:10]]

            batch = WOFBatchCursor(ids, connector)

            chunks = []
            async for chunk in batch.process_in_chunks(chunk_size=3):
                chunks.append(chunk)
                assert isinstance(chunk, list)
                assert all(isinstance(p, WOFPlace) for p in chunk)
                assert len(chunk) <= 3

            # Verify all places were processed
            all_places = [p for chunk in chunks for p in chunk]
            assert len(all_places) == len(ids)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_batch_cursor_empty_ids(self, connector):
        """Batch cursor should handle empty ID list."""
        batch = WOFBatchCursor([], connector)

        assert batch.count == 0
        assert batch.place_ids == []

        places = await batch.fetch_all()
        assert places == []

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_batch_cursor_fetch_hierarchies(self, connector):
        """fetch_hierarchies should return ancestry for all places."""
        ids = [MOORE_HILL_LOCALITY_ID]
        batch = WOFBatchCursor(ids, connector)

        hierarchies = await batch.fetch_hierarchies()

        assert isinstance(hierarchies, list)
        assert len(hierarchies) == 1
        assert "place_id" in hierarchies[0]
        assert "ancestors" in hierarchies[0]
        assert hierarchies[0]["place_id"] == MOORE_HILL_LOCALITY_ID

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_batch_cursor_caching(self, connector):
        """Batch cursor should cache results."""
        ids = [BARBADOS_COUNTRY_ID]
        batch = WOFBatchCursor(ids, connector)

        # First fetch
        places1 = await batch.fetch_all()

        # Second fetch should use cache
        places2 = await batch.fetch_all()

        # Should be same objects (from cache)
        assert places1 is places2

        # Fetching with geometry should bypass cache
        places_with_geom = await batch.fetch_all(include_geometry=True)
        assert places_with_geom is not places1


class TestWOFHierarchyCursor:
    """Unit tests for WOFHierarchyCursor."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_hierarchy_cursor_initialization(self, connector):
        """Hierarchy cursor should initialize with root place."""
        # Get a place to use as root
        place = await connector.get_place(MOORE_HILL_LOCALITY_ID)
        hierarchy = WOFHierarchyCursor(place, connector)

        assert isinstance(hierarchy, WOFHierarchyCursor)
        assert hierarchy.root == place
        assert hierarchy.root.id == MOORE_HILL_LOCALITY_ID

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_hierarchy_cursor_fetch_ancestors(self, connector):
        """fetch_ancestors should return parent places."""
        # Moore Hill should have ancestors (region, country)
        place = await connector.get_place(MOORE_HILL_LOCALITY_ID)
        hierarchy = WOFHierarchyCursor(place, connector)

        ancestors = await hierarchy.fetch_ancestors()

        assert isinstance(ancestors, list)
        # Should have at least country
        assert len(ancestors) > 0
        assert all(isinstance(a, WOFPlace) for a in ancestors)

        # Barbados country should be in ancestors
        ancestor_ids = [a.id for a in ancestors]
        assert BARBADOS_COUNTRY_ID in ancestor_ids

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_hierarchy_cursor_fetch_ancestors_with_geometry(self, connector):
        """fetch_ancestors should support geometry fetching."""
        place = await connector.get_place(MOORE_HILL_LOCALITY_ID)
        hierarchy = WOFHierarchyCursor(place, connector)

        ancestors = await hierarchy.fetch_ancestors(include_geometry=True)

        assert len(ancestors) > 0
        # Geometry should be included
        for ancestor in ancestors:
            assert hasattr(ancestor, "geometry")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_hierarchy_cursor_fetch_descendants(self, connector):
        """fetch_descendants should return child places."""
        # Use Barbados country to find descendants
        place = await connector.get_place(BARBADOS_COUNTRY_ID)
        hierarchy = WOFHierarchyCursor(place, connector)

        descendants = await hierarchy.fetch_descendants()

        assert isinstance(descendants, list)
        # Barbados should have descendants (regions, localities)
        assert len(descendants) > 0
        assert all(isinstance(d, WOFPlace) for d in descendants)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_hierarchy_cursor_with_filters(self, connector):
        """fetch_descendants should respect filters."""
        place = await connector.get_place(BARBADOS_COUNTRY_ID)
        hierarchy = WOFHierarchyCursor(place, connector)

        # Fetch only localities
        filters = WOFFilters(placetype="locality")
        descendants = await hierarchy.fetch_descendants(filters=filters)

        assert all(d.placetype == "locality" for d in descendants)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_hierarchy_cursor_fetch_children(self, connector):
        """fetch_children should return immediate children only."""
        place = await connector.get_place(BARBADOS_COUNTRY_ID)
        hierarchy = WOFHierarchyCursor(place, connector)

        # Fetch immediate children (regions)
        children = await hierarchy.fetch_children(placetype="region")

        assert isinstance(children, list)
        # Children should be regions only
        assert all(c.placetype == "region" for c in children)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_hierarchy_cursor_build_tree(self, connector):
        """build_tree should return complete hierarchy structure."""
        place = await connector.get_place(MOORE_HILL_LOCALITY_ID)
        hierarchy = WOFHierarchyCursor(place, connector)

        tree = await hierarchy.build_tree()

        assert isinstance(tree, dict)
        assert "root" in tree
        assert "ancestors" in tree
        assert "descendants" in tree
        assert "stats" in tree

        # Verify stats
        assert "ancestor_count" in tree["stats"]
        assert "descendant_count" in tree["stats"]
        assert "total_places" in tree["stats"]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_hierarchy_cursor_ancestor_caching(self, connector):
        """Ancestor results should be cached."""
        place = await connector.get_place(MOORE_HILL_LOCALITY_ID)
        hierarchy = WOFHierarchyCursor(place, connector)

        # First fetch
        ancestors1 = await hierarchy.fetch_ancestors()

        # Second fetch (should use cache for metadata)
        ancestors2 = await hierarchy.fetch_ancestors()

        # Should return same number of ancestors
        assert len(ancestors1) == len(ancestors2)


class TestCursorPatterns:
    """Tests for cursor pattern behaviors (Two-Phase Exploration)."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_lightweight_navigation_without_geometry(self, connector):
        """Phase 1: Navigate with minimal data, no geometry fetching."""
        # Phase 1: Lightweight search
        cursor = await connector.search(WOFSearchFilters(placetype="locality", limit=10))

        # Navigate without fetching geometry (lightweight)
        assert cursor.has_results
        places = cursor.places  # Lightweight access

        # Verify we have lightweight data
        assert len(places) > 0
        for place in places:
            assert place.id is not None
            assert place.name is not None
            # Should NOT have geometry yet
            assert not hasattr(place, "geometry")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_selective_geometry_fetching(self, connector):
        """Phase 2: Selectively fetch geometry for chosen places."""
        # Phase 1: Navigate
        cursor = await connector.search(WOFSearchFilters(limit=10))

        if len(cursor.places) > 0:
            # Phase 2: Fetch geometry for selected place
            place_with_geom = await cursor.fetch_one(0, include_geometry=True)

            # Now should have geometry
            assert hasattr(place_with_geom, "geometry")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_cursor_navigation_preserves_state(self, connector):
        """Cursor state should not change during navigation."""
        cursor = await connector.search(WOFSearchFilters(limit=5))

        # Get initial state
        initial_count = cursor.total_count
        initial_ids = [p.id for p in cursor.places]

        # Navigate multiple times
        for _ in range(3):
            for place in cursor:
                _ = place.name

        # State should be unchanged
        assert cursor.total_count == initial_count
        assert [p.id for p in cursor.places] == initial_ids

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_two_phase_exploration_workflow(self, connector):
        """Complete workflow: navigate lightweight, then selective fetch."""
        # Phase 1: Lightweight exploration
        cursor = await connector.search(WOFSearchFilters(placetype="locality", limit=20))

        # Explore without heavy fetching
        interesting_places = []
        for place in cursor.places:
            if "town" in place.name.lower() or "village" in place.name.lower():
                interesting_places.append(place)

        # Phase 2: Fetch only interesting places with geometry
        if len(interesting_places) > 0:
            interesting_ids = [p.id for p in interesting_places]
            detailed_places = await cursor.fetch_by_ids(
                interesting_ids, include_geometry=True
            )

            assert len(detailed_places) == len(interesting_places)
            # Now have geometry for selected places
            for place in detailed_places:
                assert hasattr(place, "geometry")


class TestCursorConcurrency:
    """Tests for concurrent cursor operations (Pattern 6)."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_multiple_cursors_independent(self, connector):
        """Multiple cursors should operate independently."""
        # Create multiple cursors concurrently
        cursors = await asyncio.gather(
            connector.search(WOFSearchFilters(placetype="locality")),
            connector.search(WOFSearchFilters(placetype="region")),
            connector.search(WOFSearchFilters(limit=5)),
        )

        # Each cursor should have independent state
        assert cursors[0].query_filters["placetype"] == "locality"
        assert cursors[1].query_filters["placetype"] == "region"
        assert cursors[2].query_filters["limit"] == 5

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_cursor_concurrent_fetch_operations(self, connector):
        """Cursor should handle concurrent fetch operations."""
        cursor = await connector.search(WOFSearchFilters(limit=10))

        if cursor.has_results:
            # Perform concurrent fetches
            results = await asyncio.gather(
                cursor.fetch_all(include_geometry=False),
                cursor.fetch_all(include_geometry=True),
                cursor.fetch_one(0),
            )

            # All results should be valid
            assert isinstance(results[0], PlaceCollection)
            assert isinstance(results[1], PlaceCollection)
            assert isinstance(results[2], WOFPlace) or results[2] is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_hierarchy_cursor_concurrent_operations(self, connector):
        """Hierarchy cursor should support concurrent operations."""
        place = await connector.get_place(MOORE_HILL_LOCALITY_ID)
        hierarchy = WOFHierarchyCursor(place, connector)

        # Concurrent hierarchy operations
        results = await asyncio.gather(
            hierarchy.fetch_ancestors(),
            hierarchy.fetch_descendants(),
        )

        ancestors, descendants = results

        assert isinstance(ancestors, list)
        assert isinstance(descendants, list)
        assert all(isinstance(a, WOFPlace) for a in ancestors)
        assert all(isinstance(d, WOFPlace) for d in descendants)
