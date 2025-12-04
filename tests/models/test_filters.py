"""
Unit tests for WOF filter models.

Tests verify filter construction, validation, and conversion behavior.
These are pure unit tests with no database dependencies.
"""

import pytest
from pydantic import ValidationError
from wof_explorer.models.filters import (
    WOFSearchFilters,
    WOFFilters,
    WOFExpansion,
    WOFBatchFilter,
)
from wof_explorer.types import PlaceType


class TestWOFSearchFiltersConstruction:
    """Tests for WOFSearchFilters construction and defaults."""

    @pytest.mark.unit
    def test_search_filters_default_values(self):
        """Empty filters should have sensible defaults."""
        filters = WOFSearchFilters()

        assert filters.placetype is None
        assert filters.name is None
        assert filters.name_exact is False
        assert filters.name_language == "eng"
        assert filters.name_type == "preferred"
        assert filters.parent_name is None
        assert filters.parent_id is None
        assert filters.ancestor_name is None
        assert filters.ancestor_id is None
        assert filters.bbox is None
        assert filters.near_lat is None
        assert filters.near_lon is None
        assert filters.radius_km is None
        assert filters.under_point is None
        assert filters.is_current is None
        assert filters.is_deprecated is None
        assert filters.is_ceased is None
        assert filters.is_superseded is None
        assert filters.is_superseding is None
        assert filters.country is None
        assert filters.region is None
        assert filters.repo is None
        assert filters.geometry_type is None
        assert filters.exclude_point_geoms is False
        assert filters.limit is None
        assert filters.offset is None
        assert filters.source is None

    @pytest.mark.unit
    def test_search_filters_with_single_values(self):
        """Filters should accept single values for all fields."""
        filters = WOFSearchFilters(
            name="Toronto",
            placetype="locality",
            country="CA",
            is_current=True,
            limit=10,
            offset=5,
        )

        assert filters.name == "Toronto"
        assert filters.placetype == PlaceType.LOCALITY
        assert filters.country == "CA"
        assert filters.is_current is True
        assert filters.limit == 10
        assert filters.offset == 5

    @pytest.mark.unit
    def test_search_filters_with_list_values(self):
        """Filters should accept lists for multi-value fields."""
        filters = WOFSearchFilters(
            placetype=["locality", "neighbourhood"],
            ancestor_name=["Toronto", "Vancouver"],
            country=["CA", "US"],
        )

        assert isinstance(filters.placetype, list)
        assert len(filters.placetype) == 2
        assert PlaceType.LOCALITY in filters.placetype
        assert PlaceType.NEIGHBOURHOOD in filters.placetype

        assert isinstance(filters.ancestor_name, list)
        assert "Toronto" in filters.ancestor_name
        assert "Vancouver" in filters.ancestor_name

        assert isinstance(filters.country, list)
        assert "CA" in filters.country
        assert "US" in filters.country

    @pytest.mark.unit
    def test_search_filters_placetype_validation(self):
        """Placetype should be validated and coerced to PlaceType enum."""
        # Valid placetype string
        filters = WOFSearchFilters(placetype="locality")
        assert filters.placetype == PlaceType.LOCALITY

        # Valid PlaceType enum
        filters = WOFSearchFilters(placetype=PlaceType.REGION)
        assert filters.placetype == PlaceType.REGION

        # Normalized variations (neighborhood -> neighbourhood)
        filters = WOFSearchFilters(placetype="neighborhood")
        assert filters.placetype == PlaceType.NEIGHBOURHOOD

        # List of placetypes
        filters = WOFSearchFilters(placetype=["locality", PlaceType.REGION])
        assert PlaceType.LOCALITY in filters.placetype
        assert PlaceType.REGION in filters.placetype

    @pytest.mark.unit
    def test_search_filters_invalid_placetype(self):
        """Invalid placetype should raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            WOFSearchFilters(placetype="invalid_type")

        assert "placetype" in str(exc_info.value).lower()

    @pytest.mark.unit
    def test_search_filters_name_options(self):
        """Name search options should be properly set."""
        filters = WOFSearchFilters(
            name="San Francisco",
            name_exact=True,
            name_language="fra",
            name_type="colloquial",
        )

        assert filters.name == "San Francisco"
        assert filters.name_exact is True
        assert filters.name_language == "fra"
        assert filters.name_type == "colloquial"

    @pytest.mark.unit
    def test_search_filters_bbox(self):
        """Bounding box filter should be stored correctly."""
        bbox = (-122.5, 37.7, -122.3, 37.8)
        filters = WOFSearchFilters(bbox=bbox)

        assert filters.bbox == bbox

    @pytest.mark.unit
    def test_search_filters_proximity_search(self):
        """Proximity search parameters should be stored correctly."""
        filters = WOFSearchFilters(near_lat=37.7749, near_lon=-122.4194, radius_km=10.0)

        assert filters.near_lat == 37.7749
        assert filters.near_lon == -122.4194
        assert filters.radius_km == 10.0

    @pytest.mark.unit
    def test_search_filters_under_point(self):
        """Under point filter should be stored correctly."""
        point = (37.7749, -122.4194)
        filters = WOFSearchFilters(under_point=point)

        assert filters.under_point == point

    @pytest.mark.unit
    def test_search_filters_geometry_type(self):
        """Geometry type filter should accept single or multiple values."""
        # Single value
        filters = WOFSearchFilters(geometry_type="Polygon")
        assert filters.geometry_type == "Polygon"

        # Multiple values
        filters = WOFSearchFilters(geometry_type=["Polygon", "MultiPolygon"])
        assert "Polygon" in filters.geometry_type
        assert "MultiPolygon" in filters.geometry_type

    @pytest.mark.unit
    def test_search_filters_exclude_point_geoms(self):
        """Exclude point geometries flag should be stored correctly."""
        filters = WOFSearchFilters(exclude_point_geoms=True)
        assert filters.exclude_point_geoms is True

        filters = WOFSearchFilters(exclude_point_geoms=False)
        assert filters.exclude_point_geoms is False


class TestWOFSearchFiltersBehavior:
    """Tests for WOFSearchFilters behavior."""

    @pytest.mark.unit
    def test_has_geographic_filter_with_bbox(self):
        """Should detect geographic filter with bbox."""
        filters = WOFSearchFilters(bbox=(-122.5, 37.7, -122.3, 37.8))
        assert filters.has_geographic_filter() is True

    @pytest.mark.unit
    def test_has_geographic_filter_with_proximity(self):
        """Should detect geographic filter with proximity search."""
        filters = WOFSearchFilters(near_lat=37.7749, near_lon=-122.4194)
        assert filters.has_geographic_filter() is True

    @pytest.mark.unit
    def test_has_geographic_filter_with_parent_id(self):
        """Should detect geographic filter with parent_id."""
        filters = WOFSearchFilters(parent_id=85922583)
        assert filters.has_geographic_filter() is True

    @pytest.mark.unit
    def test_has_geographic_filter_without_filters(self):
        """Should return False when no geographic filters are set."""
        filters = WOFSearchFilters(name="Toronto")
        assert filters.has_geographic_filter() is False

    @pytest.mark.unit
    def test_has_status_filter_with_is_current(self):
        """Should detect status filter with is_current."""
        filters = WOFSearchFilters(is_current=True)
        assert filters.has_status_filter() is True

    @pytest.mark.unit
    def test_has_status_filter_with_is_deprecated(self):
        """Should detect status filter with is_deprecated."""
        filters = WOFSearchFilters(is_deprecated=True)
        assert filters.has_status_filter() is True

    @pytest.mark.unit
    def test_has_status_filter_with_is_ceased(self):
        """Should detect status filter with is_ceased."""
        filters = WOFSearchFilters(is_ceased=True)
        assert filters.has_status_filter() is True

    @pytest.mark.unit
    def test_has_status_filter_without_filters(self):
        """Should return False when no status filters are set."""
        filters = WOFSearchFilters(name="Toronto")
        assert filters.has_status_filter() is False

    @pytest.mark.unit
    def test_ancestor_id_vs_parent_id(self):
        """Ancestor ID and parent ID should be independent filters."""
        filters = WOFSearchFilters(ancestor_id=85633793, parent_id=85688637)

        assert filters.ancestor_id == 85633793
        assert filters.parent_id == 85688637
        assert filters.ancestor_id != filters.parent_id

    @pytest.mark.unit
    def test_ancestor_name_vs_parent_name(self):
        """Ancestor name and parent name should be independent filters."""
        filters = WOFSearchFilters(
            ancestor_name="California", parent_name="San Francisco"
        )

        assert filters.ancestor_name == "California"
        assert filters.parent_name == "San Francisco"
        assert filters.ancestor_name != filters.parent_name

    @pytest.mark.unit
    def test_limit_and_offset(self):
        """Limit and offset should work together for pagination."""
        filters = WOFSearchFilters(limit=20, offset=40)

        assert filters.limit == 20
        assert filters.offset == 40

    @pytest.mark.unit
    def test_limit_validation(self):
        """Limit must be positive."""
        # Valid limit
        filters = WOFSearchFilters(limit=100)
        assert filters.limit == 100

        # Zero limit should fail
        with pytest.raises(ValidationError):
            WOFSearchFilters(limit=0)

        # Negative limit should fail
        with pytest.raises(ValidationError):
            WOFSearchFilters(limit=-1)

    @pytest.mark.unit
    def test_offset_validation(self):
        """Offset must be non-negative."""
        # Valid offset
        filters = WOFSearchFilters(offset=0)
        assert filters.offset == 0

        filters = WOFSearchFilters(offset=100)
        assert filters.offset == 100

        # Negative offset should fail
        with pytest.raises(ValidationError):
            WOFSearchFilters(offset=-1)

    @pytest.mark.unit
    def test_multiple_status_filters(self):
        """Multiple status filters should be allowed."""
        filters = WOFSearchFilters(is_current=True, is_deprecated=False, is_ceased=False)

        assert filters.is_current is True
        assert filters.is_deprecated is False
        assert filters.is_ceased is False


class TestWOFFilters:
    """Tests for base WOFFilters class."""

    @pytest.mark.unit
    def test_base_filters_default_values(self):
        """Base filters should have sensible defaults."""
        filters = WOFFilters()

        assert filters.placetype is None
        assert filters.placetypes is None
        assert filters.is_current is None
        assert filters.is_deprecated is None
        assert filters.is_ceased is None
        assert filters.is_superseded is None
        assert filters.is_superseding is None
        assert filters.max_depth is None
        assert filters.limit is None

    @pytest.mark.unit
    def test_base_filters_placetype(self):
        """Base filters should accept single placetype."""
        filters = WOFFilters(placetype="locality")

        assert filters.placetype == PlaceType.LOCALITY

    @pytest.mark.unit
    def test_base_filters_placetypes(self):
        """Base filters should accept multiple placetypes."""
        filters = WOFFilters(placetypes=["locality", "neighbourhood"])

        assert isinstance(filters.placetypes, list)
        assert len(filters.placetypes) == 2
        assert PlaceType.LOCALITY in filters.placetypes
        assert PlaceType.NEIGHBOURHOOD in filters.placetypes

    @pytest.mark.unit
    def test_base_filters_is_current(self):
        """Base filters should accept is_current filter."""
        filters = WOFFilters(is_current=True)
        assert filters.is_current is True

        filters = WOFFilters(is_current=False)
        assert filters.is_current is False

    @pytest.mark.unit
    def test_base_filters_max_depth(self):
        """Base filters should accept max_depth for descendants."""
        filters = WOFFilters(max_depth=3)
        assert filters.max_depth == 3

    @pytest.mark.unit
    def test_base_filters_max_depth_validation(self):
        """Max depth must be positive."""
        # Valid max_depth
        filters = WOFFilters(max_depth=1)
        assert filters.max_depth == 1

        # Zero max_depth should fail
        with pytest.raises(ValidationError):
            WOFFilters(max_depth=0)

        # Negative max_depth should fail
        with pytest.raises(ValidationError):
            WOFFilters(max_depth=-1)

    @pytest.mark.unit
    def test_get_placetype_list_with_single(self):
        """get_placetype_list should return list with single placetype."""
        filters = WOFFilters(placetype="locality")
        placetype_list = filters.get_placetype_list()

        assert placetype_list is not None
        assert len(placetype_list) == 1
        assert PlaceType.LOCALITY in placetype_list

    @pytest.mark.unit
    def test_get_placetype_list_with_multiple(self):
        """get_placetype_list should return placetypes list."""
        filters = WOFFilters(placetypes=["locality", "neighbourhood"])
        placetype_list = filters.get_placetype_list()

        assert placetype_list is not None
        assert len(placetype_list) == 2
        assert PlaceType.LOCALITY in placetype_list
        assert PlaceType.NEIGHBOURHOOD in placetype_list

    @pytest.mark.unit
    def test_get_placetype_list_with_none(self):
        """get_placetype_list should return None when no placetypes set."""
        filters = WOFFilters()
        placetype_list = filters.get_placetype_list()

        assert placetype_list is None

    @pytest.mark.unit
    def test_get_placetype_list_prefers_placetypes(self):
        """get_placetype_list should prefer placetypes over placetype."""
        filters = WOFFilters(
            placetype="locality", placetypes=["neighbourhood", "region"]
        )
        placetype_list = filters.get_placetype_list()

        assert placetype_list is not None
        assert len(placetype_list) == 2
        assert PlaceType.NEIGHBOURHOOD in placetype_list
        assert PlaceType.REGION in placetype_list
        assert PlaceType.LOCALITY not in placetype_list

    @pytest.mark.unit
    def test_should_include_place_no_filters(self):
        """should_include_place should return True when no filters set."""
        filters = WOFFilters()

        # Should include all combinations
        assert filters.should_include_place(1, False, False) is True
        assert filters.should_include_place(0, True, False) is True
        assert filters.should_include_place(-1, False, True) is True

    @pytest.mark.unit
    def test_should_include_place_is_current_filter(self):
        """should_include_place should filter by is_current."""
        filters = WOFFilters(is_current=True)

        # Should include current (is_current=1)
        assert filters.should_include_place(1, False, False) is True

        # Should exclude non-current (is_current=0 or -1)
        assert filters.should_include_place(0, False, False) is False
        assert filters.should_include_place(-1, False, False) is False

    @pytest.mark.unit
    def test_should_include_place_is_deprecated_filter(self):
        """should_include_place should filter by is_deprecated."""
        filters = WOFFilters(is_deprecated=True)

        # Should include deprecated
        assert filters.should_include_place(1, True, False) is True

        # Should exclude non-deprecated
        assert filters.should_include_place(1, False, False) is False

    @pytest.mark.unit
    def test_should_include_place_is_ceased_filter(self):
        """should_include_place should filter by is_ceased."""
        filters = WOFFilters(is_ceased=True)

        # Should include ceased
        assert filters.should_include_place(1, False, True) is True

        # Should exclude non-ceased
        assert filters.should_include_place(1, False, False) is False

    @pytest.mark.unit
    def test_should_include_place_combined_filters(self):
        """should_include_place should handle combined filters correctly."""
        filters = WOFFilters(is_current=True, is_deprecated=False)

        # Should include current and not deprecated
        assert filters.should_include_place(1, False, False) is True

        # Should exclude current but deprecated
        assert filters.should_include_place(1, True, False) is False

        # Should exclude not current (even if not deprecated)
        assert filters.should_include_place(0, False, False) is False


class TestFilterValidation:
    """Tests for filter validation."""

    @pytest.mark.unit
    def test_empty_filters_allowed(self):
        """Empty filters should be allowed."""
        # WOFSearchFilters
        search_filters = WOFSearchFilters()
        assert search_filters is not None

        # WOFFilters
        base_filters = WOFFilters()
        assert base_filters is not None

    @pytest.mark.unit
    def test_invalid_placetype_handling(self):
        """Invalid placetype should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            WOFSearchFilters(placetype="not_a_real_placetype")

        assert "placetype" in str(exc_info.value).lower()

    @pytest.mark.unit
    def test_invalid_name_type(self):
        """Invalid name_type should raise ValidationError."""
        with pytest.raises(ValidationError):
            WOFSearchFilters(name_type="invalid")

    @pytest.mark.unit
    def test_valid_name_types(self):
        """All valid name types should be accepted."""
        for name_type in ["preferred", "colloquial", "variant", "any"]:
            filters = WOFSearchFilters(name_type=name_type)
            assert filters.name_type == name_type

    @pytest.mark.unit
    def test_placetype_list_with_invalid_item(self):
        """List of placetypes with invalid item should raise ValidationError."""
        with pytest.raises(ValidationError):
            WOFSearchFilters(placetype=["locality", "invalid_type"])


class TestFilterSerialization:
    """Tests for filter serialization."""

    @pytest.mark.unit
    def test_search_filters_to_dict(self):
        """Filters should serialize to dict correctly."""
        filters = WOFSearchFilters(
            name="Toronto",
            placetype="locality",
            is_current=True,
            limit=10,
        )

        data = filters.model_dump()

        assert isinstance(data, dict)
        assert data["name"] == "Toronto"
        assert data["placetype"] == "locality"  # Serialized to string
        assert data["is_current"] is True
        assert data["limit"] == 10

    @pytest.mark.unit
    def test_search_filters_from_dict(self):
        """Filters should deserialize from dict correctly."""
        data = {
            "name": "Toronto",
            "placetype": "locality",
            "is_current": True,
            "limit": 10,
        }

        filters = WOFSearchFilters(**data)

        assert filters.name == "Toronto"
        assert filters.placetype == PlaceType.LOCALITY
        assert filters.is_current is True
        assert filters.limit == 10

    @pytest.mark.unit
    def test_filters_exclude_none_values(self):
        """Serialization should handle None values correctly."""
        filters = WOFSearchFilters(name="Toronto", limit=10)

        # Default serialization includes None values
        data = filters.model_dump()
        assert "name" in data
        assert "limit" in data
        assert "placetype" in data
        assert data["placetype"] is None

        # exclude_none removes None values
        data = filters.model_dump(exclude_none=True)
        assert "name" in data
        assert "limit" in data
        assert "placetype" not in data

    @pytest.mark.unit
    def test_placetype_serialization_single(self):
        """Single placetype should serialize to string value."""
        filters = WOFSearchFilters(placetype="locality")
        data = filters.model_dump()

        assert data["placetype"] == "locality"
        assert isinstance(data["placetype"], str)

    @pytest.mark.unit
    def test_placetype_serialization_list(self):
        """Placetype list should serialize to list of string values."""
        filters = WOFSearchFilters(placetype=["locality", "neighbourhood"])
        data = filters.model_dump()

        assert isinstance(data["placetype"], list)
        assert "locality" in data["placetype"]
        assert "neighbourhood" in data["placetype"]

    @pytest.mark.unit
    def test_base_filters_serialization(self):
        """Base filters should serialize correctly."""
        filters = WOFFilters(
            placetype="locality", is_current=True, max_depth=3, limit=100
        )

        data = filters.model_dump()

        assert data["placetype"] == "locality"
        assert data["is_current"] is True
        assert data["max_depth"] == 3
        assert data["limit"] == 100


class TestWOFExpansion:
    """Tests for WOFExpansion configuration model."""

    @pytest.mark.unit
    def test_expansion_default_values(self):
        """Expansion should have sensible defaults."""
        expansion = WOFExpansion(expansion_type="children")

        assert expansion.expansion_type == "children"
        assert expansion.filters is None
        assert expansion.include_root is True

    @pytest.mark.unit
    def test_expansion_types(self):
        """All expansion types should be accepted."""
        for exp_type in ["children", "descendants", "ancestors"]:
            expansion = WOFExpansion(expansion_type=exp_type)
            assert expansion.expansion_type == exp_type

    @pytest.mark.unit
    def test_expansion_with_filters(self):
        """Expansion should accept filters."""
        filters = WOFFilters(placetype="locality", is_current=True)
        expansion = WOFExpansion(expansion_type="descendants", filters=filters)

        assert expansion.filters is not None
        assert expansion.filters.placetype == PlaceType.LOCALITY
        assert expansion.filters.is_current is True

    @pytest.mark.unit
    def test_expansion_include_root(self):
        """Expansion should allow controlling root inclusion."""
        expansion = WOFExpansion(expansion_type="children", include_root=False)
        assert expansion.include_root is False

        expansion = WOFExpansion(expansion_type="children", include_root=True)
        assert expansion.include_root is True

    @pytest.mark.unit
    def test_expansion_description_children(self):
        """get_description should describe children expansion."""
        expansion = WOFExpansion(expansion_type="children")
        desc = expansion.get_description()

        assert "direct children" in desc

    @pytest.mark.unit
    def test_expansion_description_descendants(self):
        """get_description should describe descendants expansion."""
        expansion = WOFExpansion(expansion_type="descendants")
        desc = expansion.get_description()

        assert "all descendants" in desc

    @pytest.mark.unit
    def test_expansion_description_ancestors(self):
        """get_description should describe ancestors expansion."""
        expansion = WOFExpansion(expansion_type="ancestors")
        desc = expansion.get_description()

        assert "all ancestors" in desc

    @pytest.mark.unit
    def test_expansion_description_with_placetype_filter(self):
        """get_description should include placetype filter."""
        filters = WOFFilters(placetype="locality")
        expansion = WOFExpansion(expansion_type="children", filters=filters)
        desc = expansion.get_description()

        assert "locality" in desc

    @pytest.mark.unit
    def test_expansion_description_with_is_current_filter(self):
        """get_description should include is_current filter."""
        filters = WOFFilters(is_current=True)
        expansion = WOFExpansion(expansion_type="children", filters=filters)
        desc = expansion.get_description()

        assert "current=yes" in desc

        filters = WOFFilters(is_current=False)
        expansion = WOFExpansion(expansion_type="children", filters=filters)
        desc = expansion.get_description()

        assert "current=no" in desc


class TestWOFBatchFilter:
    """Tests for WOFBatchFilter model."""

    @pytest.mark.unit
    def test_batch_filter_default_values(self):
        """Batch filter should have sensible defaults."""
        batch = WOFBatchFilter(place_ids=[123, 456])

        assert batch.place_ids == [123, 456]
        assert batch.include_geometry is False
        assert batch.include_names is False
        assert batch.include_ancestors is False

    @pytest.mark.unit
    def test_batch_filter_with_options(self):
        """Batch filter should accept all options."""
        batch = WOFBatchFilter(
            place_ids=[123, 456],
            include_geometry=True,
            include_names=True,
            include_ancestors=True,
        )

        assert batch.place_ids == [123, 456]
        assert batch.include_geometry is True
        assert batch.include_names is True
        assert batch.include_ancestors is True

    @pytest.mark.unit
    def test_batch_filter_empty_list_validation(self):
        """Batch filter should require at least one place ID."""
        with pytest.raises(ValidationError) as exc_info:
            WOFBatchFilter(place_ids=[])

        assert "place_ids" in str(exc_info.value).lower()

    @pytest.mark.unit
    def test_batch_filter_max_length_validation(self):
        """Batch filter should enforce maximum list length."""
        # Within limit
        valid_ids = list(range(1000))
        batch = WOFBatchFilter(place_ids=valid_ids)
        assert len(batch.place_ids) == 1000

        # Over limit
        invalid_ids = list(range(1001))
        with pytest.raises(ValidationError) as exc_info:
            WOFBatchFilter(place_ids=invalid_ids)

        assert "place_ids" in str(exc_info.value).lower()

    @pytest.mark.unit
    def test_batch_filter_single_id(self):
        """Batch filter should accept single place ID."""
        batch = WOFBatchFilter(place_ids=[123])

        assert batch.place_ids == [123]
        assert len(batch.place_ids) == 1
