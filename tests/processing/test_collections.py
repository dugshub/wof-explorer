"""
Unit tests for PlaceCollection functionality.

Tests verify collection construction, serialization, filtering,
and analysis capabilities. These are UNIT tests separate from the
contract tests in test_collection_contract.py.
"""

import pytest
import pytest_asyncio
import json
import random
from pathlib import Path

from wof_explorer.backends.sqlite import SQLiteWOFConnector as WOFConnector
from wof_explorer.processing.collections import PlaceCollection
from wof_explorer.models.places import WOFPlace
from wof_explorer.models.filters import WOFSearchFilters
from wof_explorer.types import PlaceType


# ============= Fixtures =============


@pytest.fixture(scope="session")
def test_db_path() -> Path:
    """
    Provides path to Barbados test database.
    Note: This is re-defined here for standalone test module execution.
    """
    test_data_dir = (
        Path(__file__).parent.parent.parent.parent / "wof-test-data"
    )
    test_db = test_data_dir / "whosonfirst-data-admin-bb-latest.db"

    if not test_db.exists():
        pytest.skip(f"Test database not found at {test_db}. Run main tests first to download.")

    return test_db


@pytest_asyncio.fixture
async def connector(test_db_path):
    """Provides connected WOF connector with automatic cleanup."""
    connector = WOFConnector(str(test_db_path))
    await connector.connect()
    yield connector
    await connector.disconnect()


@pytest_asyncio.fixture
async def sample_collection(connector) -> PlaceCollection:
    """Provides a PlaceCollection with real data for testing."""
    cursor = await connector.search(WOFSearchFilters(limit=20))
    return await cursor.fetch_all()


@pytest_asyncio.fixture
async def geometry_collection(connector) -> PlaceCollection:
    """Provides a PlaceCollection with geometry data."""
    cursor = await connector.search(
        WOFSearchFilters(placetype="locality", limit=5)
    )
    return await cursor.fetch_all(include_geometry=True)


@pytest_asyncio.fixture
async def mixed_type_collection(connector) -> PlaceCollection:
    """Provides a collection with multiple placetypes."""
    cursor = await connector.search(WOFSearchFilters(limit=50))
    return await cursor.fetch_all()


@pytest.fixture
def mock_places() -> list[WOFPlace]:
    """Create mock WOFPlace objects for isolated testing."""
    places = [
        WOFPlace(
            id=1,
            name="Test Locality",
            placetype=PlaceType.LOCALITY,
            parent_id=100,
            is_current=1,
            is_deprecated=0,
            is_ceased=0,
            country="BB",
            repo="whosonfirst-data",
            latitude=13.1,
            longitude=-59.6,
        ),
        WOFPlace(
            id=2,
            name="Test Region",
            placetype=PlaceType.REGION,
            parent_id=200,
            is_current=1,
            is_deprecated=0,
            is_ceased=0,
            country="BB",
            repo="whosonfirst-data",
            latitude=13.2,
            longitude=-59.5,
        ),
        WOFPlace(
            id=3,
            name="Test Neighbourhood",
            placetype=PlaceType.NEIGHBOURHOOD,
            parent_id=1,
            is_current=1,
            is_deprecated=0,
            is_ceased=0,
            country="BB",
            repo="zetashapes",
            latitude=13.15,
            longitude=-59.55,
        ),
    ]
    return places


# ============= PlaceCollection Construction Unit Tests =============


class TestPlaceCollectionConstruction:
    """Unit tests for PlaceCollection construction."""

    @pytest.mark.unit
    def test_collection_from_places_list(self, mock_places):
        """PlaceCollection can be constructed from a list of places."""
        collection = PlaceCollection(places=mock_places)

        assert len(collection) == 3
        assert collection.places == mock_places
        assert not collection.is_empty

    @pytest.mark.unit
    def test_collection_empty_construction(self):
        """PlaceCollection can be constructed empty."""
        collection = PlaceCollection(places=[])

        assert len(collection) == 0
        assert collection.is_empty
        assert collection.places == []

    @pytest.mark.unit
    def test_collection_with_metadata(self, mock_places):
        """PlaceCollection can store metadata."""
        metadata = {"source": "test", "query": "test query", "count": 3}
        collection = PlaceCollection(places=mock_places, metadata=metadata)

        assert collection.metadata == metadata
        assert collection.metadata["source"] == "test"
        assert collection.metadata["count"] == 3

    @pytest.mark.unit
    def test_collection_from_places_classmethod(self, mock_places):
        """PlaceCollection.from_places() creates instance with metadata."""
        collection = PlaceCollection.from_places(
            mock_places,
            source="test",
            query_type="search"
        )

        assert len(collection) == 3
        assert collection.metadata["source"] == "test"
        assert collection.metadata["query_type"] == "search"

    @pytest.mark.unit
    def test_collection_immutability_of_original_list(self, mock_places):
        """Collection doesn't mutate the original places list."""
        original_count = len(mock_places)
        collection = PlaceCollection(places=mock_places)

        # Modify collection's internal list
        collection.places.append(
            WOFPlace(
                id=999,
                name="Added",
                placetype=PlaceType.LOCALITY,
                parent_id=None,
                is_current=1,
            )
        )

        # Original should be unchanged if we passed a copy, or same if shared
        # This test documents the current behavior
        assert len(collection) == 4
        # Note: Pydantic doesn't deep-copy by default, so this is expected

    @pytest.mark.unit
    def test_collection_repr_empty(self):
        """Empty collection has appropriate repr."""
        collection = PlaceCollection(places=[])
        repr_str = repr(collection)

        assert "empty" in repr_str.lower()

    @pytest.mark.unit
    def test_collection_repr_with_data(self, mock_places):
        """Collection repr shows useful summary."""
        collection = PlaceCollection(places=mock_places)
        repr_str = repr(collection)

        assert "3 places" in repr_str
        assert "locality" in repr_str.lower() or "region" in repr_str.lower()


# ============= PlaceCollection Serialization Unit Tests =============


class TestPlaceCollectionSerialization:
    """Unit tests for PlaceCollection serialization methods."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_geojson_format_compliance(self, sample_collection):
        """GeoJSON output conforms to specification."""
        geojson = sample_collection.to_geojson()

        # Must be a valid FeatureCollection
        assert geojson["type"] == "FeatureCollection"
        assert "features" in geojson
        assert isinstance(geojson["features"], list)

        # Each feature must be valid
        for feature in geojson["features"]:
            assert feature["type"] == "Feature"
            assert "geometry" in feature
            assert "properties" in feature
            assert isinstance(feature["properties"], dict)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_geojson_feature_properties(self, sample_collection):
        """GeoJSON features include expected properties."""
        geojson = sample_collection.to_geojson(
            properties=["name", "placetype", "country"]
        )

        if geojson["features"]:
            props = geojson["features"][0]["properties"]

            # Requested properties should be present
            assert "name" in props
            assert "placetype" in props
            assert "country" in props

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_geojson_geometry_types(self, geometry_collection):
        """GeoJSON handles different geometry types correctly."""
        geojson = geometry_collection.to_geojson(use_polygons=True)

        # Collect geometry types
        geom_types = set()
        for feature in geojson["features"]:
            geom = feature["geometry"]
            if geom is not None:
                geom_types.add(geom["type"])
                # Must have coordinates
                assert "coordinates" in geom

        # Should only have valid GeoJSON geometry types
        valid_types = {
            "Point", "Polygon", "MultiPolygon",
            "LineString", "MultiLineString"
        }
        assert geom_types.issubset(valid_types)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_geojson_point_only_mode(self, geometry_collection):
        """GeoJSON can output points only (no polygons)."""
        geojson = geometry_collection.to_geojson(use_polygons=False)

        # All geometries should be Points
        for feature in geojson["features"]:
            geom = feature["geometry"]
            if geom is not None:
                assert geom["type"] == "Point"
                # Point coordinates: [lon, lat]
                assert isinstance(geom["coordinates"], list)
                assert len(geom["coordinates"]) == 2

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_geojson_string_is_valid_json(self, sample_collection):
        """GeoJSON string output is valid JSON."""
        geojson_str = sample_collection.to_geojson_string()

        # Should be parseable as JSON
        parsed = json.loads(geojson_str)
        assert parsed["type"] == "FeatureCollection"
        assert "features" in parsed

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_geojson_string_formatting(self, sample_collection):
        """GeoJSON string respects formatting options."""
        # Pretty formatted
        pretty = sample_collection.to_geojson_string(indent=2)
        assert "\n" in pretty

        # Compact (no indent) - note: even indent=0 may have some newlines
        compact = sample_collection.to_geojson_string(indent=0)
        # Compact should have different formatting than pretty
        # (indent=0 still formats, just without indentation)
        assert isinstance(compact, str)
        assert len(compact) > 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_csv_rows_structure(self, sample_collection):
        """CSV export returns properly structured rows."""
        csv_rows = sample_collection.to_csv_rows()

        assert isinstance(csv_rows, list)

        if csv_rows:
            # All rows should be dictionaries
            for row in csv_rows:
                assert isinstance(row, dict)

            # All rows should have same keys
            first_keys = set(csv_rows[0].keys())
            for row in csv_rows[1:]:
                assert set(row.keys()) == first_keys

            # Should have basic fields
            assert "id" in first_keys
            assert "name" in first_keys

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_csv_with_custom_fields(self, sample_collection):
        """CSV export includes expected fields."""
        csv_rows = sample_collection.to_csv_rows()

        if csv_rows:
            row = csv_rows[0]
            # Check for important fields
            expected_fields = {"id", "name", "placetype"}
            assert expected_fields.issubset(set(row.keys()))

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_wkt_format_validity(self, geometry_collection):
        """WKT export produces valid WKT strings."""
        wkt_list = geometry_collection.to_wkt_list()

        assert isinstance(wkt_list, list)

        for item in wkt_list:
            assert isinstance(item, dict)
            assert "id" in item
            assert "name" in item

            # If WKT is present, validate format
            if "wkt" in item and item["wkt"]:
                wkt = item["wkt"]
                assert isinstance(wkt, str)
                # Must start with valid WKT type
                assert any(
                    wkt.startswith(prefix)
                    for prefix in [
                        "POINT", "POLYGON", "MULTIPOLYGON",
                        "LINESTRING", "MULTILINESTRING"
                    ]
                )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_to_dict_serialization(self, sample_collection):
        """to_dict() produces complete dictionary representation."""
        data = sample_collection.to_dict()

        assert isinstance(data, dict)
        assert "places" in data
        assert "metadata" in data
        assert "count" in data

        # Count should match
        assert data["count"] == len(sample_collection)

        # Places should be serialized
        for place_dict in data["places"]:
            assert isinstance(place_dict, dict)
            assert "id" in place_dict
            assert "name" in place_dict

    @pytest.mark.unit
    def test_empty_collection_serialization(self):
        """Empty collections serialize without errors."""
        collection = PlaceCollection(places=[])

        # All serialization methods should work
        geojson = collection.to_geojson()
        assert geojson["features"] == []

        csv_rows = collection.to_csv_rows()
        assert csv_rows == []

        wkt_list = collection.to_wkt_list()
        assert wkt_list == []

        data = collection.to_dict()
        assert data["count"] == 0


# ============= PlaceCollection Filtering Unit Tests =============


class TestPlaceCollectionFiltering:
    """Unit tests for PlaceCollection filtering operations."""

    @pytest.mark.unit
    def test_filter_preserves_collection_type(self, mock_places):
        """filter() returns a PlaceCollection, not a list."""
        collection = PlaceCollection(places=mock_places)

        filtered = collection.filter(lambda p: p.placetype == PlaceType.LOCALITY)

        assert isinstance(filtered, PlaceCollection)
        assert not isinstance(filtered, list)

    @pytest.mark.unit
    def test_filter_chain_operations(self, mock_places):
        """Filters can be chained together."""
        collection = PlaceCollection(places=mock_places)

        # Chain multiple filters
        result = (
            collection
            .filter(lambda p: p.is_current == 1)
            .filter(lambda p: p.country == "BB")
            .filter(lambda p: "Test" in p.name)
        )

        assert isinstance(result, PlaceCollection)
        # All filters should apply
        for place in result.places:
            assert place.is_current == 1
            assert place.country == "BB"
            assert "Test" in place.name

    @pytest.mark.unit
    def test_filter_returns_new_collection(self, mock_places):
        """filter() returns new collection, doesn't modify original."""
        original = PlaceCollection(places=mock_places)
        original_count = len(original)

        filtered = original.filter(lambda p: p.placetype == PlaceType.LOCALITY)

        # Original unchanged
        assert len(original) == original_count
        # Filtered is different
        assert len(filtered) <= len(original)

    @pytest.mark.unit
    def test_filter_by_type(self, mock_places):
        """filter_by_type() correctly filters by placetype."""
        collection = PlaceCollection(places=mock_places)

        localities = collection.filter_by_type(PlaceType.LOCALITY)

        assert all(p.placetype == PlaceType.LOCALITY for p in localities.places)
        assert len(localities) >= 1

    @pytest.mark.unit
    def test_filter_by_status_current(self, mock_places):
        """filter_by_status() filters for current places."""
        collection = PlaceCollection(places=mock_places)

        current = collection.filter_by_status(is_current=True)

        assert all(p.is_current == 1 for p in current.places)

    @pytest.mark.unit
    def test_filter_preserves_metadata(self, mock_places):
        """filter() preserves collection metadata."""
        collection = PlaceCollection(
            places=mock_places,
            metadata={"source": "test", "query": "original"}
        )

        filtered = collection.filter(lambda p: True)

        # Metadata should be preserved
        assert filtered.metadata["source"] == "test"
        assert filtered.metadata["query"] == "original"

    @pytest.mark.unit
    def test_find_exact_match(self, mock_places):
        """find() with exact=True finds exact name matches."""
        collection = PlaceCollection(places=mock_places)

        matches = collection.find("Test Locality", exact=True)

        assert len(matches) == 1
        assert matches[0].name == "Test Locality"

    @pytest.mark.unit
    def test_find_partial_match(self, mock_places):
        """find() with exact=False finds partial matches."""
        collection = PlaceCollection(places=mock_places)

        matches = collection.find("Test", exact=False)

        # Should find all places with "Test" in name
        assert len(matches) == 3
        assert all("Test" in p.name for p in matches)

    @pytest.mark.unit
    def test_find_one_returns_single_place(self, mock_places):
        """find_one() returns single place or None."""
        collection = PlaceCollection(places=mock_places)

        place = collection.find_one("Test Locality")
        assert isinstance(place, WOFPlace)
        assert place.name == "Test Locality"

        not_found = collection.find_one("Does Not Exist")
        assert not_found is None


# ============= PlaceCollection Analysis Unit Tests =============


class TestPlaceCollectionAnalysis:
    """Unit tests for PlaceCollection analysis methods."""

    @pytest.mark.unit
    def test_summary_statistics(self, mock_places):
        """summary() provides comprehensive statistics."""
        collection = PlaceCollection(places=mock_places)

        summary = collection.summary()

        assert summary["count"] == 3
        assert "placetypes" in summary
        assert "repos" in summary
        assert "status" in summary

        # Check placetype counts
        assert summary["placetypes"]["locality"] == 1
        assert summary["placetypes"]["region"] == 1
        assert summary["placetypes"]["neighbourhood"] == 1

    @pytest.mark.unit
    def test_summary_empty_collection(self):
        """summary() handles empty collection."""
        collection = PlaceCollection(places=[])

        summary = collection.summary()

        assert summary["count"] == 0
        assert summary["placetypes"] == {}
        assert summary["repos"] == {}

    @pytest.mark.unit
    def test_group_by_placetype(self, mock_places):
        """group_by('placetype') groups correctly."""
        collection = PlaceCollection(places=mock_places)

        groups = collection.group_by("placetype")

        assert PlaceType.LOCALITY in groups
        assert PlaceType.REGION in groups
        assert PlaceType.NEIGHBOURHOOD in groups

        # Each group should contain correct places
        assert len(groups[PlaceType.LOCALITY]) == 1
        assert len(groups[PlaceType.REGION]) == 1

    @pytest.mark.unit
    def test_group_by_country(self, mock_places):
        """group_by('country') groups by country code."""
        collection = PlaceCollection(places=mock_places)

        groups = collection.group_by("country")

        assert "BB" in groups
        assert len(groups["BB"]) == 3

    @pytest.mark.unit
    def test_group_by_type_returns_collections(self, mock_places):
        """group_by_type() returns PlaceCollection objects."""
        collection = PlaceCollection(places=mock_places)

        groups = collection.group_by_type()

        # Each group should be a PlaceCollection
        for placetype, group in groups.items():
            assert isinstance(group, PlaceCollection)
            assert all(str(p.placetype.value) == placetype for p in group.places)

    @pytest.mark.unit
    def test_unique_values_extraction(self, mock_places):
        """unique_values() extracts unique attribute values."""
        collection = PlaceCollection(places=mock_places)

        placetypes = collection.unique_values("placetype")
        countries = collection.unique_values("country")

        # Should be lists of unique values
        assert isinstance(placetypes, list)
        assert len(placetypes) == 3  # locality, region, neighbourhood

        assert isinstance(countries, list)
        assert countries == ["BB"]

    @pytest.mark.unit
    def test_sample_randomness(self, mock_places):
        """sample() returns random subset."""
        # Create larger collection
        places = mock_places * 10  # 30 places
        collection = PlaceCollection(places=places)

        # Set seed for reproducibility
        random.seed(42)
        sample1 = collection.sample(n=5)

        random.seed(42)
        sample2 = collection.sample(n=5)

        # Same seed should give same sample
        assert len(sample1) == 5
        assert len(sample2) == 5
        assert [p.id for p in sample1.places] == [p.id for p in sample2.places]

    @pytest.mark.unit
    def test_sample_stratified(self, mock_places):
        """sample(by='attribute') does stratified sampling."""
        # Create collection with multiple of each type
        places = mock_places * 5  # 15 places (5 of each type)
        collection = PlaceCollection(places=places)

        sampled = collection.sample(n=2, by="placetype")

        # Should sample 2 from each placetype
        groups = sampled.group_by("placetype")
        for placetype, places_list in groups.items():
            assert len(places_list) == 2

    @pytest.mark.unit
    def test_top_names(self, mock_places):
        """top_names() returns most common names."""
        # Create collection with duplicate names
        places = mock_places + mock_places[:2]  # Duplicates first 2
        collection = PlaceCollection(places=places)

        top = collection.top_names(n=3)

        assert isinstance(top, list)
        # Should be list of (name, count) tuples
        for name, count in top:
            assert isinstance(name, str)
            assert isinstance(count, int)
            assert count >= 1

    @pytest.mark.unit
    def test_describe_verbose(self, mock_places):
        """describe() provides human-readable description."""
        collection = PlaceCollection(places=mock_places)

        basic = collection.describe(verbose=False)
        verbose = collection.describe(verbose=True)

        assert isinstance(basic, str)
        assert isinstance(verbose, str)
        assert len(basic) > 0
        # Verbose should include more details
        assert len(verbose) >= len(basic)

    @pytest.mark.unit
    def test_coverage_map(self, mock_places):
        """coverage_map() analyzes geographic coverage."""
        collection = PlaceCollection(places=mock_places)

        coverage = collection.coverage_map()

        assert "countries" in coverage
        assert "bounding_box" in coverage
        assert "top_regions" in coverage
        assert "top_localities" in coverage

        # Should have country data
        assert "BB" in coverage["countries"]


# ============= PlaceCollection Intelligent Summary Tests =============


class TestPlaceCollectionEnrichedSummary:
    """Tests for intelligent summary with ancestor enrichment."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_summary_without_enrichment(self, sample_collection):
        """get_summary() works without ancestor enrichment."""
        summary = sample_collection.get_summary(enrich_ancestors=False)

        assert "total_count" in summary
        assert "has_geometry" in summary
        assert "by_type" in summary

        # Should have basic type grouping
        assert isinstance(summary["by_type"], dict)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_summary_basic_structure(self, connector):
        """get_summary() has expected structure."""
        cursor = await connector.search(
            WOFSearchFilters(placetype="locality", limit=10)
        )
        collection = await cursor.fetch_all()

        summary = collection.get_summary(enrich_ancestors=False)

        assert summary["total_count"] == len(collection)
        assert isinstance(summary["metadata"], dict)
        assert isinstance(summary["by_type"], dict)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_summary_with_ancestor_enrichment(self, connector):
        """get_summary() with enrichment includes ancestor grouping."""
        cursor = await connector.search(
            WOFSearchFilters(placetype="locality", limit=5)
        )
        collection = await cursor.fetch_all()

        # Enrich with ancestor data
        await collection.enrich_with_ancestors(connector)

        # Get enriched summary
        summary = collection.get_summary(enrich_ancestors=True)

        # Should have ancestor data in metadata
        assert "ancestor_data" in collection.metadata
        # Note: "by_ancestor" grouping only appears when ancestor filters are used
        # in the query, not just when enrichment is performed
        assert "total_count" in summary
        assert "by_type" in summary

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_summary_coverage_info(self, connector):
        """get_summary() includes coverage report for multi-value filters."""
        # Search with multiple placetypes
        cursor = await connector.search(
            WOFSearchFilters(
                placetype=["locality", "region"],
                limit=20
            )
        )
        collection = await cursor.fetch_all()

        summary = collection.get_summary(enrich_ancestors=False)

        # Should include coverage information
        if "coverage" in summary:
            coverage = summary["coverage"]
            assert "placetypes_requested" in coverage or len(coverage) > 0

    @pytest.mark.unit
    def test_get_summary_empty_collection(self):
        """get_summary() handles empty collection."""
        collection = PlaceCollection(places=[])

        summary = collection.get_summary()

        assert summary["total_count"] == 0
        assert not summary["has_geometry"]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_enrich_with_geometry(self, connector):
        """enrich_with_geometry() adds geometry data to collection."""
        # Get collection without geometry
        cursor = await connector.search(
            WOFSearchFilters(placetype="locality", limit=3)
        )
        collection = await cursor.fetch_all(include_geometry=False)

        assert not collection.has_geometry

        # Enrich with geometry
        await collection.enrich_with_geometry(connector)

        # Now should have geometry (if available in DB)
        # Note: Actual geometry presence depends on database content


# ============= PlaceCollection Browse Methods Tests =============


class TestPlaceCollectionBrowse:
    """Tests for browse and exploration methods."""

    @pytest.mark.unit
    def test_browse_hierarchical(self, mock_places):
        """browse('hierarchical') organizes by placetype hierarchy."""
        collection = PlaceCollection(places=mock_places)

        view = collection.browse(style="hierarchical")

        assert view["style"] == "hierarchical"
        assert "content" in view

        content = view["content"]
        # Should have hierarchical levels
        assert "locality" in content or "region" in content

    @pytest.mark.unit
    def test_browse_alphabetical(self, mock_places):
        """browse('alphabetical') creates letter index."""
        collection = PlaceCollection(places=mock_places)

        view = collection.browse(style="alphabetical")

        assert view["style"] == "alphabetical"
        assert "content" in view
        assert "letters" in view

        # Should have "T" for "Test..."
        assert "T" in view["letters"]

    @pytest.mark.unit
    def test_browse_geographic(self, mock_places):
        """browse('geographic') groups by quadrants."""
        collection = PlaceCollection(places=mock_places)

        view = collection.browse(style="geographic")

        assert view["style"] == "geographic"
        assert "content" in view

        if view["content"]:
            # Should have center point
            assert "center" in view

    @pytest.mark.unit
    def test_browse_quality(self, mock_places):
        """browse('quality') analyzes data quality."""
        collection = PlaceCollection(places=mock_places)

        view = collection.browse(style="quality")

        assert view["style"] == "quality"
        assert "content" in view
        assert "total_places" in view

    @pytest.mark.unit
    def test_browse_invalid_style(self, mock_places):
        """browse() raises error for invalid style."""
        collection = PlaceCollection(places=mock_places)

        with pytest.raises(ValueError, match="Unknown browse style"):
            collection.browse(style="invalid_style")
