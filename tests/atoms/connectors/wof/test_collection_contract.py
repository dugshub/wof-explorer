"""
Contract tests for PlaceCollection behavior.

PlaceCollections provide data manipulation and serialization capabilities
that must work consistently across all backends.
"""

import pytest
import pytest_asyncio
import json

from wof_explorer.models.filters import WOFSearchFilters
from wof_explorer.models.places import WOFPlace
from wof_explorer.processing.collections import PlaceCollection


class BasePlaceCollectionContract:
    """
    Contract tests for PlaceCollection behavior that all backends must support.

    PlaceCollections are returned from cursor.fetch_all() and provide
    serialization, filtering, and analysis capabilities.
    """

    @pytest.fixture
    def connector(self):
        """
        Fixture that provides the connector to test.
        Must be overridden by backend-specific test classes.
        """
        raise NotImplementedError("Backend must provide 'connector' fixture")

    @pytest_asyncio.fixture
    async def sample_collection(self, connector) -> PlaceCollection:
        """Get a sample collection for testing."""
        await connector.connect()
        cursor = await connector.search(WOFSearchFilters(limit=20))
        return await cursor.fetch_all()

    @pytest_asyncio.fixture
    async def geometry_collection(self, connector) -> PlaceCollection:
        """Get a collection with geometry for testing."""
        await connector.connect()
        cursor = await connector.search(
            WOFSearchFilters(placetype="neighbourhood", limit=5)
        )
        return await cursor.fetch_all(include_geometry=True)

    # ============= COLLECTION BASICS =============

    @pytest.mark.asyncio
    async def test_collection_is_iterable(self, sample_collection):
        """Collections must be iterable."""
        count = 0
        for place in sample_collection:
            assert isinstance(place, WOFPlace)
            count += 1

        assert count == len(sample_collection.places)

    @pytest.mark.asyncio
    async def test_collection_supports_len(self, sample_collection):
        """Collections must support len()."""
        length = len(sample_collection)
        assert isinstance(length, int)
        assert length >= 0
        assert length == len(sample_collection.places)

    @pytest.mark.asyncio
    async def test_collection_supports_indexing(self, sample_collection):
        """Collections must support index access."""
        if len(sample_collection) > 0:
            # Positive indexing
            first = sample_collection[0]
            assert isinstance(first, WOFPlace)

            # Negative indexing
            last = sample_collection[-1]
            assert isinstance(last, WOFPlace)

    @pytest.mark.asyncio
    async def test_collection_has_metadata(self, sample_collection):
        """Collections should have metadata."""
        assert hasattr(sample_collection, "metadata")
        assert isinstance(sample_collection.metadata, dict)

    @pytest.mark.asyncio
    async def test_collection_empty_handling(self, connector):
        """Collections must handle empty results."""
        await connector.connect()

        # Get empty collection
        cursor = await connector.search(WOFSearchFilters(name="ThisDoesNotExist999999"))
        collection = await cursor.fetch_all()

        assert collection.is_empty
        assert len(collection) == 0
        assert collection.places == []

    # ============= SERIALIZATION CONTRACT =============

    @pytest.mark.asyncio
    async def test_collection_to_geojson(self, sample_collection):
        """Collections must support GeoJSON serialization."""
        geojson = sample_collection.to_geojson()

        # Must be valid GeoJSON FeatureCollection
        assert isinstance(geojson, dict)
        assert geojson["type"] == "FeatureCollection"
        assert "features" in geojson
        assert isinstance(geojson["features"], list)

        # Each feature must be valid
        for feature in geojson["features"]:
            assert feature["type"] == "Feature"
            assert "properties" in feature
            assert "geometry" in feature

    @pytest.mark.asyncio
    async def test_collection_to_geojson_with_properties(self, sample_collection):
        """GeoJSON export must support property selection."""
        geojson = sample_collection.to_geojson(
            properties=["name", "placetype", "country"]
        )

        if geojson["features"]:
            feature = geojson["features"][0]
            props = feature["properties"]

            # Selected properties should be present
            assert "name" in props
            assert "placetype" in props
            assert "country" in props

    @pytest.mark.asyncio
    async def test_collection_to_geojson_string(self, sample_collection):
        """Collections must support GeoJSON string export."""
        geojson_str = sample_collection.to_geojson_string()

        # Must be valid JSON
        assert isinstance(geojson_str, str)
        parsed = json.loads(geojson_str)
        assert parsed["type"] == "FeatureCollection"

    @pytest.mark.asyncio
    async def test_collection_to_geojson_with_geometry(self, geometry_collection):
        """GeoJSON export must handle geometry properly."""
        geojson = geometry_collection.to_geojson(use_polygons=True)

        # Features with geometry should have proper geometry objects
        for feature in geojson["features"]:
            geom = feature["geometry"]
            if geom is not None:
                assert "type" in geom
                assert "coordinates" in geom

    @pytest.mark.asyncio
    async def test_collection_to_csv(self, sample_collection):
        """Collections must support CSV export."""
        csv_rows = sample_collection.to_csv_rows()

        # Must return list of dictionaries
        assert isinstance(csv_rows, list)

        if csv_rows:
            # Each row must be a dictionary
            for row in csv_rows:
                assert isinstance(row, dict)

            # All rows should have same keys
            keys = set(csv_rows[0].keys())
            for row in csv_rows[1:]:
                assert set(row.keys()) == keys

    @pytest.mark.asyncio
    async def test_collection_to_wkt(self, geometry_collection):
        """Collections must support WKT export."""
        wkt_list = geometry_collection.to_wkt_list()

        # Must return list
        assert isinstance(wkt_list, list)

        for item in wkt_list:
            assert isinstance(item, dict)
            assert "id" in item
            assert "name" in item
            # WKT might be None if no geometry
            if "wkt" in item and item["wkt"]:
                # Basic WKT validation
                assert isinstance(item["wkt"], str)
                assert any(
                    item["wkt"].startswith(prefix)
                    for prefix in ["POINT", "POLYGON", "MULTIPOLYGON", "LINESTRING"]
                )

    @pytest.mark.asyncio
    async def test_collection_to_dict(self, sample_collection):
        """Collections must support dictionary export."""
        data = sample_collection.to_dict()

        assert isinstance(data, dict)
        assert "places" in data
        assert isinstance(data["places"], list)

        # Each place should be serialized
        for place_dict in data["places"]:
            assert isinstance(place_dict, dict)
            assert "id" in place_dict
            assert "name" in place_dict

    # ============= FILTERING CONTRACT =============

    @pytest.mark.asyncio
    async def test_collection_filter_by_type(self, connector):
        """Collections must support type filtering."""
        await connector.connect()

        # Get mixed collection
        cursor = await connector.search(WOFSearchFilters(limit=50))
        collection = await cursor.fetch_all()

        if not collection.is_empty:
            # Get first placetype we find
            placetype = collection.places[0].placetype

            # Filter by that type
            filtered = collection.filter_by_type(placetype)

            # All results should match
            for place in filtered.places:
                assert place.placetype == placetype

    @pytest.mark.asyncio
    async def test_collection_filter_by_status(self, sample_collection):
        """Collections must support status filtering."""
        # Filter for current/active places
        active = sample_collection.filter_by_status(is_current=True)

        # All results should be active
        for place in active.places:
            assert place.is_active

    @pytest.mark.asyncio
    async def test_collection_filter_custom(self, sample_collection):
        """Collections must support custom filter predicates."""

        # Custom filter function
        def has_long_name(place):
            return len(place.name) > 10

        filtered = sample_collection.filter(has_long_name)

        # All results should match predicate
        for place in filtered.places:
            assert len(place.name) > 10

    @pytest.mark.asyncio
    async def test_collection_find(self, sample_collection):
        """Collections must support finding by name."""
        if not sample_collection.is_empty:
            # Get a name from the collection
            target_name = sample_collection.places[0].name

            # Find by exact name
            found = sample_collection.find(target_name, exact=True)
            assert len(found) > 0
            assert all(p.name == target_name for p in found)

            # Find by partial name
            partial = target_name[:3]
            found_partial = sample_collection.find(partial, exact=False)
            assert all(partial.lower() in p.name.lower() for p in found_partial)

    @pytest.mark.asyncio
    async def test_collection_find_one(self, sample_collection):
        """Collections must support finding single items."""
        if not sample_collection.is_empty:
            target_name = sample_collection.places[0].name

            # Find one by name
            found = sample_collection.find_one(target_name)
            assert found is not None
            assert found.name == target_name

            # Find non-existent
            not_found = sample_collection.find_one("ThisDoesNotExist99999")
            assert not_found is None

    # ============= ANALYSIS CONTRACT =============

    @pytest.mark.asyncio
    async def test_collection_summary(self, sample_collection):
        """Collections must provide summary statistics."""
        summary = sample_collection.summary()

        assert isinstance(summary, dict)
        assert "count" in summary
        assert summary["count"] == len(sample_collection)

        # Should have placetype breakdown
        assert "placetypes" in summary
        assert isinstance(summary["placetypes"], dict)

    @pytest.mark.asyncio
    async def test_collection_group_by(self, sample_collection):
        """Collections must support grouping."""
        if not sample_collection.is_empty:
            # Group by placetype
            grouped = sample_collection.group_by("placetype")

            assert isinstance(grouped, dict)

            # Each group should contain places of that type
            for placetype, places in grouped.items():
                assert all(p.placetype == placetype for p in places)

    @pytest.mark.asyncio
    async def test_collection_unique_values(self, sample_collection):
        """Collections must extract unique values."""
        if not sample_collection.is_empty:
            # Get unique placetypes
            placetypes = sample_collection.unique_values("placetype")

            assert isinstance(placetypes, list)
            # Should have no duplicates
            assert len(placetypes) == len(set(placetypes))

    @pytest.mark.asyncio
    async def test_collection_sample(self, sample_collection):
        """Collections must support sampling."""
        if len(sample_collection) >= 10:
            # Sample subset
            sampled = sample_collection.sample(n=5)

            assert len(sampled) == 5
            # Should be subset of original
            original_ids = {p.id for p in sample_collection.places}
            sample_ids = {p.id for p in sampled.places}
            assert sample_ids.issubset(original_ids)

    @pytest.mark.asyncio
    async def test_collection_describe(self, sample_collection):
        """Collections must provide description."""
        description = sample_collection.describe()

        assert isinstance(description, str)
        assert len(description) > 0

        # Verbose description should be longer
        verbose_desc = sample_collection.describe(verbose=True)
        assert len(verbose_desc) >= len(description)

    # ============= ENRICHMENT CONTRACT =============

    @pytest.mark.asyncio
    async def test_collection_enrich_with_ancestors(self, connector):
        """Collections must support ancestor enrichment."""
        await connector.connect()

        # Get neighborhoods
        cursor = await connector.search(
            WOFSearchFilters(placetype="neighbourhood", limit=5)
        )
        collection = await cursor.fetch_all()

        if not collection.is_empty:
            # Enrich with ancestors
            await collection.enrich_with_ancestors(connector)

            # Places should now have ancestor data
            for place in collection.places:
                if hasattr(place, "ancestors_enriched"):
                    assert place.ancestors_enriched is True

    @pytest.mark.asyncio
    async def test_collection_enriched_summary(self, connector):
        """Enriched collections should provide better summaries."""
        await connector.connect()

        cursor = await connector.search(
            WOFSearchFilters(
                placetype="neighbourhood",
                ancestor_name=["Toronto", "Montreal"],
                limit=10,
            )
        )
        collection = await cursor.fetch_all()

        if not collection.is_empty:
            # Basic summary
            basic_summary = collection.get_summary(enrich_ancestors=False)
            assert "count" in basic_summary

            # Enrich and get enhanced summary
            await collection.enrich_with_ancestors(connector)
            enriched_summary = collection.get_summary()

            # Should have ancestor grouping
            if "by_ancestor" in enriched_summary:
                assert isinstance(enriched_summary["by_ancestor"], dict)

    # ============= GEOMETRY HANDLING =============

    @pytest.mark.asyncio
    async def test_collection_has_geometry_property(self, geometry_collection):
        """Collections must indicate geometry availability."""
        # Collection fetched with geometry should report it
        assert hasattr(geometry_collection, "has_geometry")

        if geometry_collection.has_geometry:
            # At least some places should have geometry
            assert any(hasattr(p, "geometry") for p in geometry_collection.places)

    @pytest.mark.asyncio
    async def test_collection_geometry_types(self, geometry_collection):
        """Collections should handle different geometry types."""
        if geometry_collection.has_geometry:
            geojson = geometry_collection.to_geojson(use_polygons=True)

            # Check geometry types
            geom_types = set()
            for feature in geojson["features"]:
                if feature["geometry"]:
                    geom_types.add(feature["geometry"]["type"])

            # Should handle various geometry types
            valid_types = {
                "Point",
                "Polygon",
                "MultiPolygon",
                "LineString",
                "MultiLineString",
            }
            assert geom_types.issubset(valid_types)
