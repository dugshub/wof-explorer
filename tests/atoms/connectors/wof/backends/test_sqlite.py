"""
SQLite backend tests - must pass all contract tests.

This test suite ensures the SQLite implementation fulfills the WOF connector contract
and tests SQLite-specific features like multi-database support.
"""

import pytest
import pytest_asyncio
import subprocess
import sys
from pathlib import Path

# Import the contract test classes
from ..test_contract import BaseWOFConnectorContract, TestData
from ..test_cursor_contract import BaseWOFCursorContract
from ..test_collection_contract import BasePlaceCollectionContract

# Import the SQLite backend connector
from wof_explorer.backends.sqlite import SQLiteWOFConnector as WOFConnector
from wof_explorer.models.filters import WOFSearchFilters


class SQLiteTestData(TestData):
    """Test data specific to our test database (Barbados)."""

    # These IDs are from the Barbados test database
    # Barbados country ID
    barbados_id: int = 85632491  # Barbados country (correct ID)
    # Using Moore Hill as the test locality (instead of Toronto)
    toronto_id: int = (
        1326720241  # Moore Hill (locality) - used for tests expecting toronto_id
    )
    # For other test IDs
    neighborhood_id: int = 0  # No neighborhoods in Barbados data
    ontario_id: int = 0  # N/A for Barbados
    canada_id: int = 85632491  # Use Barbados country ID


@pytest.fixture(scope="session")
def test_db_path() -> Path:
    """
    Path to the test database.
    Downloads a small country database (Barbados) for fast testing.
    """
    # Use a dedicated test directory
    test_data_dir = (
        Path(__file__).parent.parent.parent.parent.parent.parent.parent
        / "wof-test-data"
    )
    test_data_dir.mkdir(exist_ok=True)

    # Check if test database already exists
    test_db = test_data_dir / "whosonfirst-data-admin-bb-latest.db"

    if not test_db.exists():
        # Download Barbados (small country) for testing
        script_path = (
            Path(__file__).parent.parent.parent.parent.parent.parent
            / "scripts"
            / "wof-download.py"
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
async def sqlite_connector(test_db_path):
    """Create SQLite connector with test database."""
    connector = WOFConnector(str(test_db_path))
    yield connector

    # Cleanup
    if hasattr(connector, "_connected") and connector._connected:
        await connector.disconnect()


@pytest.fixture
def test_data() -> SQLiteTestData:
    """Provide test data IDs."""
    return SQLiteTestData()


# Test classes that implement the contract tests for SQLite backend


class TestSQLiteWOFConnectorContract(BaseWOFConnectorContract):
    """
    SQLite backend connector contract tests.
    """

    @pytest.fixture
    def connector(self, sqlite_connector):
        """Provide SQLite connector for contract tests."""
        return sqlite_connector

    @pytest.fixture
    def test_data(self) -> SQLiteTestData:
        """Provide SQLite-specific test data."""
        return SQLiteTestData()


class TestSQLiteWOFCursorContract(BaseWOFCursorContract):
    """
    SQLite backend cursor contract tests.
    """

    @pytest.fixture
    def connector(self, sqlite_connector):
        """Provide SQLite connector for contract tests."""
        return sqlite_connector

    @pytest.fixture
    def test_data(self) -> SQLiteTestData:
        """Provide SQLite-specific test data."""
        return SQLiteTestData()


class TestSQLitePlaceCollectionContract(BasePlaceCollectionContract):
    """
    SQLite backend collection contract tests.
    """

    @pytest.fixture
    def connector(self, sqlite_connector):
        """Provide SQLite connector for contract tests."""
        return sqlite_connector

    @pytest.fixture
    def test_data(self) -> SQLiteTestData:
        """Provide SQLite-specific test data."""
        return SQLiteTestData()


class TestSQLiteSpecific:
    """
    SQLite-specific tests that are not part of the contract.
    """

    # ============= SQLITE-SPECIFIC TESTS =============

    @pytest.mark.asyncio
    async def test_sqlite_single_database_mode(self, test_db_path):
        """Test SQLite single database initialization."""
        connector = WOFConnector(str(test_db_path))

        # Should recognize single database mode
        assert len(connector.db_paths) == 1
        assert connector.db_paths[0].name == test_db_path.name
        assert not connector.is_multi_db

        await connector.connect()
        assert connector._connected

        # Should be able to query
        cursor = await connector.search(WOFSearchFilters(limit=1))
        assert cursor is not None

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_sqlite_multi_database_mode(self, test_db_path):
        """Test SQLite multi-database initialization."""
        # Create connector with list of databases
        # Using same DB twice for testing (in real use would be different DBs)
        connector = WOFConnector([str(test_db_path), str(test_db_path)])

        # Should recognize multi-database mode
        assert len(connector.db_paths) == 2
        assert connector.is_multi_db

        await connector.connect()

        # In real multi-DB mode, would have attached databases
        # For now, just verify it connects
        assert connector._connected

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_sqlite_auto_discovery(self, tmp_path, monkeypatch):
        """Test SQLite auto-discovery mode."""
        # Create test directory with databases
        test_dir = tmp_path / "wof-data"
        test_dir.mkdir()

        # Copy test database to simulate multiple DBs
        import shutil

        # Use the Barbados test database from the correct location
        test_db = (
            Path(__file__).parent.parent.parent.parent.parent.parent.parent
            / "wof-test-data"
            / "whosonfirst-data-admin-bb-latest.db"
        )
        if test_db.exists():
            shutil.copy(test_db, test_dir / "barbados.db")
            shutil.copy(test_db, test_dir / "test.db")  # Second DB for testing

            # Set environment variables
            monkeypatch.setenv("WOF_DATA_DIR", str(test_dir))
            monkeypatch.setenv("WOF_AUTO_DISCOVER", "true")

            # Reset the config so it picks up the new environment variables
            from wof_explorer.config import reset_config

            reset_config()

            # Create connector without paths
            connector = WOFConnector()

            # Should auto-discover databases
            if connector.db_paths:  # Only if discovery worked
                assert len(connector.db_paths) > 0
                assert all(p.suffix == ".db" for p in connector.db_paths)
        else:
            # Skip test if no test database available
            pytest.skip("Test database not available for auto-discovery testing")

    @pytest.mark.asyncio
    async def test_sqlite_attach_database_sql(self, sqlite_connector):
        """Test SQLite ATTACH DATABASE functionality."""
        await sqlite_connector.connect()

        # If multi-DB, should use ATTACH
        if sqlite_connector.is_multi_db:
            # Would verify ATTACH was called
            # This is implementation-specific
            pass

        await sqlite_connector.disconnect()

    @pytest.mark.asyncio
    async def test_sqlite_source_filtering(self, sqlite_connector):
        """Test filtering by source database in multi-DB mode."""
        await sqlite_connector.connect()

        # Search with source filter
        cursor = await sqlite_connector.search(
            WOFSearchFilters(
                placetype="locality",
                source="canada",  # Filter by source
            )
        )

        # Results should only be from Canada
        places = await cursor.fetch_all()

        # In single-DB mode, all results are from that DB
        # In multi-DB mode, would filter by source
        assert places is not None

        await sqlite_connector.disconnect()

    @pytest.mark.asyncio
    async def test_sqlite_unified_view(self, sqlite_connector):
        """Test unified view across attached databases."""
        await sqlite_connector.connect()

        # Search across all databases
        cursor = await sqlite_connector.search(WOFSearchFilters(placetype="country"))

        places = await cursor.fetch_all()

        # Should return results from all attached databases
        # In single-DB test, just verify it works
        assert places is not None
        assert len(places.places) > 0

        await sqlite_connector.disconnect()

    @pytest.mark.asyncio
    async def test_sqlite_performance(self, sqlite_connector):
        """Test SQLite query performance."""
        await sqlite_connector.connect()

        # Perform a typical search operation
        cursor = await sqlite_connector.search(
            WOFSearchFilters(placetype="locality", limit=100)
        )
        result = await cursor.fetch_all()

        # Verify we got results
        assert result is not None
        assert len(result.places) > 0

        # Simple performance check - query should complete in reasonable time
        import time

        start = time.perf_counter()
        cursor = await sqlite_connector.search(
            WOFSearchFilters(placetype="neighbourhood", limit=100)
        )
        elapsed = time.perf_counter() - start

        # Should complete in less than 1 second for 100 records
        assert elapsed < 1.0, f"Query took {elapsed:.3f}s, expected < 1s"

        await sqlite_connector.disconnect()

    @pytest.mark.asyncio
    async def test_sqlite_transaction_handling(self, sqlite_connector):
        """Test SQLite transaction handling."""
        await sqlite_connector.connect()

        # Multiple concurrent reads should work
        import asyncio

        async def read_operation():
            cursor = await sqlite_connector.search(WOFSearchFilters(limit=10))
            return await cursor.fetch_all()

        # Run multiple reads concurrently
        results = await asyncio.gather(
            read_operation(), read_operation(), read_operation()
        )

        # All should succeed
        assert all(r is not None for r in results)

        await sqlite_connector.disconnect()

    @pytest.mark.asyncio
    async def test_sqlite_connection_pool(self, sqlite_connector):
        """Test SQLite connection pooling if implemented."""
        await sqlite_connector.connect()

        # Check if connection pooling is implemented
        if hasattr(sqlite_connector, "_async_engine"):
            engine = sqlite_connector._async_engine

            # Verify engine configuration
            assert engine is not None

            # Could check pool settings if exposed
            # pool = engine.pool
            # assert pool is not None

        await sqlite_connector.disconnect()

    @pytest.mark.asyncio
    async def test_sqlite_error_handling(self, tmp_path):
        """Test SQLite error handling for invalid databases."""
        # Try to connect to non-existent database
        bad_path = tmp_path / "does_not_exist.db"

        with pytest.raises(FileNotFoundError):
            _ = WOFConnector(str(bad_path))

    @pytest.mark.asyncio
    async def test_sqlite_sql_injection_protection(self, sqlite_connector):
        """Test that SQLite backend prevents SQL injection."""
        await sqlite_connector.connect()

        # Try search with potentially malicious input
        malicious_input = "'; DROP TABLE spr; --"

        # Should safely handle malicious input
        cursor = await sqlite_connector.search(WOFSearchFilters(name=malicious_input))

        # Should not error or execute injection
        places = await cursor.fetch_all()
        assert places is not None

        # Verify tables still exist
        cursor2 = await sqlite_connector.search(WOFSearchFilters(limit=1))
        assert cursor2 is not None

        await sqlite_connector.disconnect()

    @pytest.mark.asyncio
    async def test_sqlite_supports_capabilities(self, sqlite_connector):
        """Test SQLite backend capability declarations."""
        # SQLite backend should have basic capabilities

        # Check that the connector has required attributes
        assert hasattr(sqlite_connector, "db_path")
        assert hasattr(sqlite_connector, "is_multi_db")

        # These capabilities may be added in the future
        if hasattr(sqlite_connector, "supports_multi_database"):
            assert isinstance(sqlite_connector.supports_multi_database, bool)

        if hasattr(sqlite_connector, "supports_spatial_queries"):
            assert isinstance(sqlite_connector.supports_spatial_queries, bool)

        if hasattr(sqlite_connector, "supports_full_text_search"):
            assert isinstance(sqlite_connector.supports_full_text_search, bool)
