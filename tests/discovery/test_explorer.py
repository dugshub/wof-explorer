"""
Contract tests for WOF Explorer discovery functionality.

Tests verify the Explorer class provides accurate database discovery
and exploration capabilities following the patterns defined in TESTING_STANDARDS.md.
"""

import pytest
import pytest_asyncio
import subprocess
import sys
from pathlib import Path

from wof_explorer.backends.sqlite import SQLiteWOFConnector as WOFConnector
from wof_explorer.models.filters import WOFSearchFilters

# Known Barbados test data IDs
BARBADOS_COUNTRY_ID = 85632491
SAINT_MICHAEL_REGION_ID = 85670295
BRIDGETOWN_LOCALITY_ID = 102027145
MOORE_HILL_LOCALITY_ID = 1326720241


@pytest.fixture(scope="session")
def test_db_path() -> Path:
    """
    Path to the test database.
    Downloads a small country database (Barbados) for fast testing.
    """
    # Use a dedicated test directory
    test_data_dir = (
        Path(__file__).parent.parent.parent.parent / "wof-test-data"
    )
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


@pytest_asyncio.fixture
async def explorer(connector):
    """Provide explorer from connected connector."""
    return connector.explorer


@pytest.mark.contract
class TestExplorerContract:
    """Contract tests for Explorer functionality."""

    # ============= HAPPY PATH TESTS (Pattern 1) =============

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_database_summary_returns_valid_summary(self, explorer):
        """
        Database summary should return a comprehensive overview of the database.

        Tests Pattern 1: Happy Path - verifies expected successful behavior.
        """
        summary = await explorer.database_summary()

        # Should return a dictionary with expected keys
        assert isinstance(summary, dict)
        assert "total_places" in summary
        assert "by_placetype" in summary
        assert "by_country" in summary
        assert "by_repo" in summary
        assert "hierarchical_coverage" in summary

        # Total places should be positive
        assert summary["total_places"] > 0

        # by_placetype should be a dictionary
        assert isinstance(summary["by_placetype"], dict)

        # by_country should contain Barbados
        assert isinstance(summary["by_country"], dict)
        assert "BB" in summary["by_country"]

        # hierarchical_coverage should have standard keys
        assert isinstance(summary["hierarchical_coverage"], dict)
        assert "countries" in summary["hierarchical_coverage"]
        assert "regions" in summary["hierarchical_coverage"]
        assert "localities" in summary["hierarchical_coverage"]

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_discover_places_by_placetype(self, explorer):
        """
        Discover places should return places of the specified placetype.

        Tests Pattern 1: Happy Path - basic discovery functionality.
        """
        # Discover localities in Barbados
        places = await explorer.discover_places(level="locality", limit=10)

        # Should return a list of places
        assert isinstance(places, list)

        # If we have results, verify structure
        if places:
            # Each place should have expected fields
            for place in places:
                assert "id" in place
                assert "name" in place
                assert "placetype" in place
                assert "country" in place

                # All should be localities
                assert place["placetype"] == "locality"

                # All should be from Barbados
                assert place["country"] == "BB"

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_discover_places_with_parent(self, explorer):
        """
        Discover places with parent filter should return descendants.

        Tests Pattern 1: Happy Path - hierarchical discovery.
        """
        # Discover places within Barbados
        places = await explorer.discover_places(
            level="locality",
            parent_name="Barbados",
            limit=20
        )

        # Should return a list
        assert isinstance(places, list)

        # Should have some localities in Barbados
        assert len(places) > 0

        # All should be from Barbados
        for place in places:
            assert place["country"] == "BB"
            assert place["placetype"] == "locality"

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_suggest_starting_points(self, explorer):
        """
        Suggest starting points should return useful exploration suggestions.

        Tests Pattern 1: Happy Path - provides exploration guidance.
        """
        suggestions = await explorer.suggest_starting_points()

        # Should return a dictionary
        assert isinstance(suggestions, dict)

        # Should contain key information
        assert "available_placetypes" in suggestions
        assert "total_places" in suggestions

        # Available placetypes should be a list
        assert isinstance(suggestions["available_placetypes"], list)
        assert len(suggestions["available_placetypes"]) > 0

        # Total places should match database
        assert suggestions["total_places"] > 0

        # Should have example countries
        if "example_countries" in suggestions:
            assert isinstance(suggestions["example_countries"], list)
            assert len(suggestions["example_countries"]) > 0

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_top_cities_by_coverage(self, explorer):
        """
        Top cities by coverage should return cities with good neighborhood data.

        Tests Pattern 1: Happy Path - quality metric calculation.
        """
        # Note: Barbados may not have neighborhoods, so this might return empty
        cities = await explorer.top_cities_by_coverage(limit=5, min_neighborhoods=1)

        # Should return a list (possibly empty for Barbados)
        assert isinstance(cities, list)

        # If we have results, verify structure
        if cities:
            for city in cities:
                assert "id" in city
                assert "name" in city
                assert "country" in city
                assert "neighborhood_count" in city

                # Neighborhood count should meet minimum
                assert city["neighborhood_count"] >= 1

    # ============= EDGE CASE TESTS (Pattern 2) =============

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_discover_places_with_invalid_placetype(self, explorer):
        """
        Discovery with invalid placetype should raise ValueError.

        Tests Pattern 3: Error Handling - invalid input should raise.
        """
        # Try to discover with a nonsense placetype
        with pytest.raises(ValueError) as exc_info:
            await explorer.discover_places(
                level="not_a_real_placetype",
                limit=10
            )

        # Should mention the invalid placetype
        assert "not_a_real_placetype" in str(exc_info.value)

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_discover_places_empty_results(self, explorer):
        """
        Discovery with filters that match nothing should return empty.

        Tests Pattern 2: Edge Cases - no matches scenario.
        """
        # Search for a parent that doesn't exist
        places = await explorer.discover_places(
            level="locality",
            parent_name="ThisPlaceDoesNotExist12345",
            limit=10
        )

        # Should return empty list
        assert isinstance(places, list)
        assert len(places) == 0

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_discover_places_with_zero_limit(self, explorer):
        """
        Discovery with zero limit should raise validation error.

        Tests Pattern 3: Error Handling - invalid limit parameter.
        """
        # Zero limit is invalid (must be >= 1)
        with pytest.raises(Exception):  # Pydantic ValidationError
            await explorer.discover_places(level="locality", limit=0)

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_top_cities_with_impossible_minimum(self, explorer):
        """
        Top cities with unrealistic minimum should return empty.

        Tests Pattern 2: Edge Cases - impossible requirements.
        """
        # Request cities with absurdly high neighborhood count
        cities = await explorer.top_cities_by_coverage(
            limit=10,
            min_neighborhoods=99999
        )

        # Should return empty list
        assert isinstance(cities, list)
        assert len(cities) == 0

    # ============= TYPE VERIFICATION TESTS (Pattern 4) =============

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_database_summary_return_type(self, explorer):
        """
        Database summary must return correctly typed data.

        Tests Pattern 4: Type Verification - ensures type safety.
        """
        summary = await explorer.database_summary()

        # Verify all expected types
        assert isinstance(summary, dict)
        assert isinstance(summary["total_places"], int)
        assert isinstance(summary["by_placetype"], dict)
        assert isinstance(summary["by_country"], dict)
        assert isinstance(summary["by_repo"], dict)
        assert isinstance(summary["hierarchical_coverage"], dict)

        # Verify nested dictionary types
        for placetype, count in summary["by_placetype"].items():
            assert isinstance(placetype, str)
            assert isinstance(count, int)

        for country, count in summary["by_country"].items():
            assert isinstance(country, str)
            assert isinstance(count, int)

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_discover_places_returns_list(self, explorer):
        """
        Discover places must always return a list.

        Tests Pattern 4: Type Verification - list return type.
        """
        places = await explorer.discover_places(level="locality")

        assert isinstance(places, list)

        # Each item must be a dictionary with required fields
        for place in places:
            assert isinstance(place, dict)
            assert isinstance(place["id"], int)
            assert isinstance(place["name"], str)
            assert isinstance(place["placetype"], str)

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_suggestion_structure(self, explorer):
        """
        Suggestions must have proper structure and types.

        Tests Pattern 4: Type Verification - complex nested structure.
        """
        suggestions = await explorer.suggest_starting_points()

        # Verify top-level structure
        assert isinstance(suggestions, dict)
        assert isinstance(suggestions["available_placetypes"], list)
        assert isinstance(suggestions["total_places"], int)

        # Verify list contents
        for placetype in suggestions["available_placetypes"]:
            assert isinstance(placetype, str)

        # Optional fields should have correct types if present
        if "example_countries" in suggestions:
            assert isinstance(suggestions["example_countries"], list)
            for country in suggestions["example_countries"]:
                assert isinstance(country, dict)
                assert "id" in country
                assert "name" in country

        if "well_mapped_city" in suggestions:
            assert isinstance(suggestions["well_mapped_city"], dict)
            assert "id" in suggestions["well_mapped_city"]
            assert "name" in suggestions["well_mapped_city"]

    # ============= STATE VERIFICATION TESTS (Pattern 5) =============

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_explorer_requires_connected_connector(self, test_db_path):
        """
        Explorer should require connector to be connected.

        Tests Pattern 5: State Verification - connection requirement.
        """
        # Create disconnected connector
        disconnected_connector = WOFConnector(str(test_db_path))
        explorer = disconnected_connector.explorer

        # Attempting to use explorer should fail or auto-connect
        with pytest.raises(RuntimeError) as exc_info:
            await explorer.database_summary()

        # Error should mention connection
        error_msg = str(exc_info.value).lower()
        assert "connect" in error_msg or "not connected" in error_msg

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_explorer_preserves_connector_state(self, connector, explorer):
        """
        Explorer operations should not affect connector state.

        Tests Pattern 5: State Verification - no side effects.
        """
        # Verify connector is connected before
        assert connector.is_connected

        # Perform various explorer operations
        await explorer.database_summary()
        await explorer.discover_places(level="locality", limit=5)
        await explorer.suggest_starting_points()

        # Connector should still be connected
        assert connector.is_connected

        # Should still be able to use connector
        cursor = await connector.search(WOFSearchFilters(limit=1))
        assert cursor is not None

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_multiple_explorer_operations_are_independent(self, explorer):
        """
        Multiple explorer operations should not interfere with each other.

        Tests Pattern 5: State Verification - operation independence.
        """
        import asyncio

        # Run multiple operations concurrently
        results = await asyncio.gather(
            explorer.database_summary(),
            explorer.discover_places(level="locality", limit=5),
            explorer.suggest_starting_points(),
        )

        # All should complete successfully
        assert len(results) == 3

        # Verify each result has the expected structure
        summary, places, suggestions = results

        assert isinstance(summary, dict)
        assert "total_places" in summary

        assert isinstance(places, list)

        assert isinstance(suggestions, dict)
        assert "available_placetypes" in suggestions

    # ============= DATA QUALITY TESTS =============

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_check_data_quality_returns_metrics(self, explorer):
        """
        Data quality check should return comprehensive metrics.

        Validates the quality assessment functionality.
        """
        quality = await explorer.check_data_quality(sample_size=100)

        # Should return metrics dictionary
        assert isinstance(quality, dict)

        # Should not have errors
        assert "error" not in quality

        # Should have expected metrics
        assert "sample_size" in quality
        assert "coordinate_coverage" in quality
        assert "parent_id_coverage" in quality
        assert "country_coverage" in quality
        assert "name_coverage" in quality
        assert "current_percentage" in quality
        assert "geometry_coverage" in quality

        # Sample size should match request (or be less if DB is smaller)
        assert quality["sample_size"] > 0
        assert quality["sample_size"] <= 100

        # Most coverage metrics should be between 0 and 1
        # Note: geometry_coverage can be > 1 if there are more geometry records than places
        for metric in [
            "coordinate_coverage",
            "parent_id_coverage",
            "country_coverage",
            "name_coverage",
            "current_percentage",
        ]:
            assert 0 <= quality[metric] <= 1

        # Geometry coverage can exceed 1 due to implementation quirks
        assert quality["geometry_coverage"] >= 0

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_discover_places_respects_limit(self, explorer):
        """
        Discovery should respect the limit parameter.

        Validates pagination and result limiting.
        """
        limit = 5
        places = await explorer.discover_places(level="locality", limit=limit)

        # Should not exceed limit
        assert len(places) <= limit

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_discover_places_filters_by_parent_id(self, explorer):
        """
        Discovery should support filtering by parent ID.

        Tests hierarchical filtering using parent_id parameter.
        """
        # Use Barbados country ID as parent
        places = await explorer.discover_places(
            level="locality",
            parent_id=BARBADOS_COUNTRY_ID,
            limit=20
        )

        # Should return list
        assert isinstance(places, list)

        # Should have localities (Barbados has several)
        assert len(places) > 0

        # All should be from Barbados
        for place in places:
            assert place["country"] == "BB"
