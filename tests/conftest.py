"""
Shared test fixtures for wof-explorer test suite.

This conftest.py provides reusable fixtures following the testing standards
defined in docs/TESTING_STANDARDS.md. All test modules can access these fixtures
without explicit imports.
"""

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
import pytest_asyncio

from wof_explorer.backends.sqlite import SQLiteWOFConnector as WOFConnector
from wof_explorer.models.filters import WOFSearchFilters
from wof_explorer.processing.collections import PlaceCollection


# ============= TEST DATA MODELS =============


@dataclass
class TestData:
    """
    Known test IDs from the Barbados test database.

    The Barbados database is used for testing because it's:
    - Small (~5MB) for fast downloads and tests
    - Complete with real geographic hierarchy
    - Stable and unlikely to change significantly
    """

    country_id: int = 85632491  # Barbados (country)
    locality_id: int = 1326720241  # Moore Hill (locality)
    region_id: int = 85670295  # Saint Michael (region)
    bridgetown_id: int = 102027145  # Bridgetown (locality)

    # Note: No neighborhoods in Barbados test data
    neighborhood_id: int = 0


# ============= SESSION-SCOPED FIXTURES =============


@pytest.fixture(scope="session")
def test_db_path() -> Path:
    """
    Provides path to Barbados test database.
    Downloads automatically if not present.

    This fixture is session-scoped to avoid downloading the database
    multiple times during a test run.

    Returns:
        Path: Absolute path to the Barbados test database

    Raises:
        pytest.skip: If database download fails or times out
    """
    # Use dedicated test data directory at repository root
    test_data_dir = (
        Path(__file__).parent.parent.parent / "wof-test-data"
    )
    test_data_dir.mkdir(exist_ok=True)

    # Check if test database already exists
    test_db = test_data_dir / "whosonfirst-data-admin-bb-latest.db"

    if not test_db.exists():
        # Download Barbados (small country) for testing
        script_path = (
            Path(__file__).parent.parent / "scripts" / "wof-download.py"
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


# ============= FUNCTION-SCOPED FIXTURES =============


@pytest.fixture
def test_data() -> TestData:
    """
    Provides known test IDs from Barbados database.

    Use this fixture when you need specific, known place IDs for testing.
    These IDs are stable and guaranteed to exist in the Barbados test database.

    Returns:
        TestData: Dataclass containing known test place IDs

    Example:
        async def test_get_place(connector, test_data):
            place = await connector.get_place(test_data.country_id)
            assert place.id == test_data.country_id
    """
    return TestData()


@pytest_asyncio.fixture
async def connector(test_db_path):
    """
    Provides connected WOF connector with automatic cleanup.

    This fixture creates a SQLite connector, establishes the connection,
    and ensures proper cleanup after the test completes. The connector
    is automatically disconnected even if the test fails.

    Args:
        test_db_path: Path to test database (from test_db_path fixture)

    Yields:
        WOFConnector: Connected connector instance

    Example:
        async def test_search(connector):
            cursor = await connector.search(WOFSearchFilters(limit=10))
            assert cursor.total_count >= 0
    """
    connector = WOFConnector(str(test_db_path))
    await connector.connect()

    yield connector

    # Cleanup: Always disconnect, even if test fails
    if hasattr(connector, "_connected") and connector._connected:
        await connector.disconnect()


@pytest_asyncio.fixture
async def sample_collection(connector) -> PlaceCollection:
    """
    Provides a PlaceCollection with real data for testing.

    This fixture performs a simple search and returns a small collection
    of places. Useful for testing collection operations without needing
    to set up search filters in every test.

    Args:
        connector: Connected WOF connector (from connector fixture)

    Returns:
        PlaceCollection: Collection containing up to 10 places

    Example:
        async def test_collection_length(sample_collection):
            assert len(sample_collection) > 0
            assert len(sample_collection) <= 10
    """
    cursor = await connector.search(WOFSearchFilters(limit=10))
    return await cursor.fetch_all()


@pytest_asyncio.fixture
async def barbados_places(connector) -> PlaceCollection:
    """
    Provides collection of all places in Barbados for testing.

    This fixture fetches all places from the Barbados test database,
    useful for testing operations that need to work with a complete
    geographic dataset.

    Args:
        connector: Connected WOF connector (from connector fixture)

    Returns:
        PlaceCollection: Collection containing all Barbados places

    Example:
        async def test_filter_localities(barbados_places):
            localities = [p for p in barbados_places if p.placetype == "locality"]
            assert len(localities) > 0
    """
    cursor = await connector.search(WOFSearchFilters())
    return await cursor.fetch_all()


@pytest_asyncio.fixture
async def bridgetown_cursor(connector):
    """
    Provides cursor for Bridgetown search results.

    Bridgetown is the capital of Barbados and a known locality in the
    test database. This fixture provides a cursor for tests that need
    to work with a specific, known place.

    Args:
        connector: Connected WOF connector (from connector fixture)

    Returns:
        Cursor: Search cursor for Bridgetown results

    Example:
        async def test_bridgetown_exists(bridgetown_cursor):
            assert bridgetown_cursor.total_count > 0
            places = await bridgetown_cursor.fetch_all()
            assert any("Bridgetown" in p.name for p in places)
    """
    return await connector.search(
        WOFSearchFilters(name="Bridgetown", placetype="locality")
    )


# ============= PARAMETRIZED TEST DATA =============


@pytest.fixture(params=["locality", "region", "country"])
def placetype(request):
    """
    Parametrized fixture providing different placetypes.

    Use this fixture with parametrized tests that need to test behavior
    across different placetypes. The test will run once for each placetype.

    Returns:
        str: One of "locality", "region", or "country"

    Example:
        async def test_search_by_placetype(connector, placetype):
            cursor = await connector.search(
                WOFSearchFilters(placetype=placetype, limit=1)
            )
            if cursor.total_count > 0:
                places = await cursor.fetch_all()
                assert places[0].placetype == placetype
    """
    return request.param


@pytest.fixture(params=[True, False])
def include_geometry(request):
    """
    Parametrized fixture for geometry inclusion flag.

    Use this fixture to test operations both with and without geometry
    inclusion, ensuring behavior is correct in both cases.

    Returns:
        bool: True or False

    Example:
        async def test_fetch_with_geometry(connector, include_geometry):
            cursor = await connector.search(WOFSearchFilters(limit=1))
            places = await cursor.fetch_all(include_geometry=include_geometry)
            if include_geometry and len(places) > 0:
                assert hasattr(places[0], 'geometry')
    """
    return request.param


# ============= MARKER CONFIGURATION =============

# Markers are configured in pyproject.toml under [tool.pytest.ini_options]
# Available markers:
# - @pytest.mark.unit: Unit tests (isolated components)
# - @pytest.mark.integration: Integration tests (component interaction)
# - @pytest.mark.contract: Contract tests (interface compliance)
# - @pytest.mark.wof: Tests requiring WhosOnFirst database
# - @pytest.mark.sqlite: Tests requiring SQLite database
# - @pytest.mark.slow: Tests taking >1 second
# - @pytest.mark.benchmark: Performance benchmark tests
# - @pytest.mark.explorer: Database exploration features
# - @pytest.mark.cursor: Cursor-based navigation
# - @pytest.mark.serialization: Data serialization (GeoJSON, CSV, WKT)
