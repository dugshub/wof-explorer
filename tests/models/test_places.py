"""
Unit tests for WOF place models.

Tests verify place construction, properties, serialization, and comparison.
"""

import pytest
from datetime import datetime
from wof_explorer.models.places import WOFPlace, WOFPlaceWithGeometry, WOFName
from wof_explorer.types import PlaceType

# Known test IDs from Barbados database
BARBADOS_COUNTRY_ID = 85632491
SAINT_MICHAEL_REGION_ID = 85670295
BRIDGETOWN_LOCALITY_ID = 102027145


class TestWOFPlaceConstruction:
    """Tests for WOFPlace construction."""

    @pytest.mark.unit
    def test_place_required_fields(self):
        """Place must have id, name, and placetype."""
        place = WOFPlace(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )

        assert place.id == BARBADOS_COUNTRY_ID
        assert place.name == "Barbados"
        assert place.placetype == PlaceType.COUNTRY

    @pytest.mark.unit
    def test_place_optional_fields(self):
        """Place can be created with optional fields."""
        place = WOFPlace(
            id=SAINT_MICHAEL_REGION_ID,
            name="Saint Michael",
            placetype="region",
            parent_id=BARBADOS_COUNTRY_ID,
            country="BB",
            population=120000,
            area_m2=39000000.0,
            source="whosonfirst",
        )

        assert place.parent_id == BARBADOS_COUNTRY_ID
        assert place.country == "BB"
        assert place.population == 120000
        assert place.area_m2 == 39000000.0
        assert place.source == "whosonfirst"

    @pytest.mark.unit
    def test_place_with_geometry(self):
        """Place can store bbox and centroid."""
        place = WOFPlace(
            id=BRIDGETOWN_LOCALITY_ID,
            name="Bridgetown",
            placetype="locality",
            bbox=[-59.62, 13.09, -59.61, 13.10],
            centroid=[-59.615, 13.095],
        )

        assert place.bbox == [-59.62, 13.09, -59.61, 13.10]
        assert place.centroid == [-59.615, 13.095]

    @pytest.mark.unit
    def test_place_without_geometry(self):
        """Place can be created without spatial data."""
        place = WOFPlace(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )

        assert place.bbox is None
        assert place.centroid is None

    @pytest.mark.unit
    def test_place_with_hierarchy_fields(self):
        """Place can store hierarchy location fields."""
        place = WOFPlace(
            id=BRIDGETOWN_LOCALITY_ID,
            name="Bridgetown",
            placetype="locality",
            country="BB",
            region="Saint Michael",
            locality="Bridgetown",
        )

        assert place.country == "BB"
        assert place.region == "Saint Michael"
        assert place.locality == "Bridgetown"

    @pytest.mark.unit
    def test_place_with_status_fields(self):
        """Place can store status information."""
        deprecated_date = datetime(2020, 1, 1)
        place = WOFPlace(
            id=12345,
            name="Old Place",
            placetype="locality",
            is_current=False,
            deprecated=deprecated_date,
            superseded_by=[67890],
        )

        assert place.is_current is False
        assert place.deprecated == deprecated_date
        assert place.superseded_by == [67890]

    @pytest.mark.unit
    def test_place_coerces_placetype_string(self):
        """Placetype string is coerced to PlaceType enum."""
        place = WOFPlace(
            id=12345,
            name="Test",
            placetype="locality",
        )

        assert isinstance(place.placetype, PlaceType)
        assert place.placetype == PlaceType.LOCALITY

    @pytest.mark.unit
    def test_place_normalizes_placetype_variations(self):
        """Placetype variations are normalized."""
        place = WOFPlace(
            id=12345,
            name="Test",
            placetype="neighborhood",  # American spelling
        )

        assert place.placetype == PlaceType.NEIGHBOURHOOD

    @pytest.mark.unit
    def test_place_coerces_superseded_by_single_value(self):
        """Single superseded_by value is converted to list."""
        place = WOFPlace(
            id=12345,
            name="Test",
            placetype="locality",
            superseded_by=67890,  # Single value
        )

        assert place.superseded_by == [67890]
        assert isinstance(place.superseded_by, list)

    @pytest.mark.unit
    def test_place_coerces_supersedes_single_value(self):
        """Single supersedes value is converted to list."""
        place = WOFPlace(
            id=12345,
            name="Test",
            placetype="locality",
            supersedes=67890,  # Single value
        )

        assert place.supersedes == [67890]
        assert isinstance(place.supersedes, list)


class TestWOFPlaceProperties:
    """Tests for WOFPlace properties."""

    @pytest.mark.unit
    def test_place_id_property(self):
        """Place id property returns correct value."""
        place = WOFPlace(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )

        assert place.id == BARBADOS_COUNTRY_ID

    @pytest.mark.unit
    def test_place_name_property(self):
        """Place name property returns correct value."""
        place = WOFPlace(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )

        assert place.name == "Barbados"

    @pytest.mark.unit
    def test_place_placetype_property(self):
        """Place placetype property returns PlaceType enum."""
        place = WOFPlace(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )

        assert place.placetype == PlaceType.COUNTRY
        assert isinstance(place.placetype, PlaceType)

    @pytest.mark.unit
    def test_place_country_property(self):
        """Place country property returns correct value."""
        place = WOFPlace(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
            country="BB",
        )

        assert place.country == "BB"

    @pytest.mark.unit
    def test_place_is_active_property(self):
        """Place is_active property aliases is_current."""
        place = WOFPlace(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
            is_current=True,
        )

        assert place.is_active is True
        assert place.is_current is True

    @pytest.mark.unit
    def test_place_parent_id_property(self):
        """Place parent_id property returns correct value."""
        place = WOFPlace(
            id=SAINT_MICHAEL_REGION_ID,
            name="Saint Michael",
            placetype="region",
            parent_id=BARBADOS_COUNTRY_ID,
        )

        assert place.parent_id == BARBADOS_COUNTRY_ID

    @pytest.mark.unit
    def test_place_parent_id_none_by_default(self):
        """Place parent_id is None by default."""
        place = WOFPlace(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )

        assert place.parent_id is None

    @pytest.mark.unit
    def test_place_latitude_property(self):
        """Place latitude property extracts from centroid."""
        place = WOFPlace(
            id=BRIDGETOWN_LOCALITY_ID,
            name="Bridgetown",
            placetype="locality",
            centroid=[-59.615, 13.095],
        )

        assert place.latitude == 13.095

    @pytest.mark.unit
    def test_place_longitude_property(self):
        """Place longitude property extracts from centroid."""
        place = WOFPlace(
            id=BRIDGETOWN_LOCALITY_ID,
            name="Bridgetown",
            placetype="locality",
            centroid=[-59.615, 13.095],
        )

        assert place.longitude == -59.615

    @pytest.mark.unit
    def test_place_latitude_none_without_centroid(self):
        """Place latitude is None without centroid."""
        place = WOFPlace(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )

        assert place.latitude is None

    @pytest.mark.unit
    def test_place_longitude_none_without_centroid(self):
        """Place longitude is None without centroid."""
        place = WOFPlace(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )

        assert place.longitude is None


class TestWOFPlaceStatus:
    """Tests for WOFPlace status flags."""

    @pytest.mark.unit
    def test_place_is_current(self):
        """Place with is_current=True is current."""
        place = WOFPlace(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
            is_current=True,
        )

        assert place.is_current is True
        assert place.is_current_status is True

    @pytest.mark.unit
    def test_place_is_deprecated(self):
        """Place with deprecated date is deprecated."""
        place = WOFPlace(
            id=12345,
            name="Old Place",
            placetype="locality",
            deprecated=datetime(2020, 1, 1),
        )

        assert place.is_deprecated is True
        assert place.is_current_status is False

    @pytest.mark.unit
    def test_place_is_ceased(self):
        """Place with cessation date is ceased."""
        place = WOFPlace(
            id=12345,
            name="Old Place",
            placetype="locality",
            cessation=datetime(2020, 1, 1),
        )

        assert place.is_ceased is True
        assert place.is_current_status is False

    @pytest.mark.unit
    def test_place_is_superseded(self):
        """Place with superseded_by is superseded."""
        place = WOFPlace(
            id=12345,
            name="Old Place",
            placetype="locality",
            superseded_by=[67890],
        )

        assert place.is_superseded is True
        assert place.is_current_status is False

    @pytest.mark.unit
    def test_place_is_superseding(self):
        """Place with supersedes is superseding."""
        place = WOFPlace(
            id=12345,
            name="New Place",
            placetype="locality",
            supersedes=[67890],
        )

        assert place.is_superseding is True
        # Note: superseding places can still be current
        assert place.is_current_status is True

    @pytest.mark.unit
    def test_place_get_status_current(self):
        """get_status returns 'current' for current places."""
        place = WOFPlace(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
            is_current=True,
        )

        assert place.get_status() == "current"

    @pytest.mark.unit
    def test_place_get_status_ceased(self):
        """get_status returns 'ceased' for ceased places."""
        place = WOFPlace(
            id=12345,
            name="Old Place",
            placetype="locality",
            cessation=datetime(2020, 1, 1),
        )

        assert place.get_status() == "ceased"

    @pytest.mark.unit
    def test_place_get_status_deprecated(self):
        """get_status returns 'deprecated' for deprecated places."""
        place = WOFPlace(
            id=12345,
            name="Old Place",
            placetype="locality",
            deprecated=datetime(2020, 1, 1),
        )

        assert place.get_status() == "deprecated"

    @pytest.mark.unit
    def test_place_get_status_superseded(self):
        """get_status returns 'superseded' for superseded places."""
        place = WOFPlace(
            id=12345,
            name="Old Place",
            placetype="locality",
            superseded_by=[67890],
        )

        assert place.get_status() == "superseded"

    @pytest.mark.unit
    def test_place_get_status_superseding(self):
        """get_status returns 'superseding' for superseding places."""
        place = WOFPlace(
            id=12345,
            name="New Place",
            placetype="locality",
            supersedes=[67890],
        )

        assert place.get_status() == "superseding"


class TestWOFPlaceGeometry:
    """Tests for WOFPlace geometry methods."""

    @pytest.mark.unit
    def test_place_get_bounds(self):
        """get_bounds returns WOFBounds object."""
        place = WOFPlace(
            id=BRIDGETOWN_LOCALITY_ID,
            name="Bridgetown",
            placetype="locality",
            bbox=[-59.62, 13.09, -59.61, 13.10],
        )

        bounds = place.get_bounds()
        assert bounds is not None
        assert bounds.min_lon == -59.62
        assert bounds.min_lat == 13.09
        assert bounds.max_lon == -59.61
        assert bounds.max_lat == 13.10

    @pytest.mark.unit
    def test_place_get_bounds_none_without_bbox(self):
        """get_bounds returns None without bbox."""
        place = WOFPlace(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )

        assert place.get_bounds() is None

    @pytest.mark.unit
    def test_place_get_centroid(self):
        """get_centroid returns WOFCentroid object."""
        place = WOFPlace(
            id=BRIDGETOWN_LOCALITY_ID,
            name="Bridgetown",
            placetype="locality",
            centroid=[-59.615, 13.095],
        )

        centroid = place.get_centroid()
        assert centroid is not None
        assert centroid.lon == -59.615
        assert centroid.lat == 13.095

    @pytest.mark.unit
    def test_place_get_centroid_none_without_centroid(self):
        """get_centroid returns None without centroid."""
        place = WOFPlace(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )

        assert place.get_centroid() is None


class TestWOFPlaceMethods:
    """Tests for WOFPlace methods."""

    @pytest.mark.unit
    def test_place_get_hierarchy_fields(self):
        """get_hierarchy_fields returns hierarchy location fields."""
        place = WOFPlace(
            id=BRIDGETOWN_LOCALITY_ID,
            name="Bridgetown",
            placetype="locality",
            country="BB",
            region="Saint Michael",
            locality="Bridgetown",
        )

        hierarchy = place.get_hierarchy_fields()
        assert hierarchy["country"] == "BB"
        assert hierarchy["region"] == "Saint Michael"
        assert hierarchy["locality"] == "Bridgetown"
        assert hierarchy["county"] is None
        assert hierarchy["neighbourhood"] is None

    @pytest.mark.unit
    def test_place_is_administrative(self):
        """is_administrative returns True for admin placetypes."""
        country = WOFPlace(id=1, name="Test", placetype="country")
        region = WOFPlace(id=2, name="Test", placetype="region")
        locality = WOFPlace(id=3, name="Test", placetype="locality")

        assert country.is_administrative() is True
        assert region.is_administrative() is True
        assert locality.is_administrative() is True

    @pytest.mark.unit
    def test_place_is_not_administrative(self):
        """is_administrative returns False for non-admin placetypes."""
        neighbourhood = WOFPlace(id=1, name="Test", placetype="neighbourhood")
        venue = WOFPlace(id=2, name="Test", placetype="venue")
        building = WOFPlace(id=3, name="Test", placetype="building")

        assert neighbourhood.is_administrative() is False
        assert venue.is_administrative() is False
        assert building.is_administrative() is False

    @pytest.mark.unit
    def test_place_to_reference(self):
        """to_reference creates lightweight WOFPlaceRef."""
        place = WOFPlace(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
            country="BB",
            population=287000,
        )

        ref = place.to_reference()
        assert ref.id == BARBADOS_COUNTRY_ID
        assert ref.name == "Barbados"
        assert ref.placetype == PlaceType.COUNTRY
        # Reference should not include extra fields
        assert not hasattr(ref, "country")
        assert not hasattr(ref, "population")


class TestWOFPlaceSerialization:
    """Tests for WOFPlace serialization."""

    @pytest.mark.unit
    def test_place_model_dump(self):
        """model_dump returns dictionary with all fields."""
        place = WOFPlace(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
            country="BB",
        )

        data = place.model_dump()
        assert isinstance(data, dict)
        assert data["id"] == BARBADOS_COUNTRY_ID
        assert data["name"] == "Barbados"
        assert data["placetype"] == "country"  # Serialized as string
        assert data["country"] == "BB"

    @pytest.mark.unit
    def test_place_serializes_placetype_as_string(self):
        """Placetype enum is serialized as string."""
        place = WOFPlace(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )

        data = place.model_dump()
        assert data["placetype"] == "country"
        assert isinstance(data["placetype"], str)

    @pytest.mark.unit
    def test_place_model_dump_excludes_none_values(self):
        """model_dump can exclude None values."""
        place = WOFPlace(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )

        data = place.model_dump(exclude_none=True)
        assert "parent_id" not in data
        assert "deprecated" not in data
        assert "cessation" not in data

    @pytest.mark.unit
    def test_place_model_dump_json(self):
        """model_dump_json returns JSON string."""
        place = WOFPlace(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )

        json_str = place.model_dump_json()
        assert isinstance(json_str, str)
        assert "Barbados" in json_str
        assert "country" in json_str


class TestWOFPlaceComparison:
    """Tests for WOFPlace equality and hashing."""

    @pytest.mark.unit
    def test_place_equality_by_id(self):
        """Places with same ID are not necessarily equal (Pydantic default)."""
        place1 = WOFPlace(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )
        place2 = WOFPlace(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )

        # Pydantic models use default equality (all fields)
        assert place1 == place2

    @pytest.mark.unit
    def test_place_inequality_different_id(self):
        """Places with different IDs are not equal."""
        place1 = WOFPlace(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )
        place2 = WOFPlace(
            id=SAINT_MICHAEL_REGION_ID,
            name="Saint Michael",
            placetype="region",
        )

        assert place1 != place2

    @pytest.mark.unit
    def test_place_inequality_different_fields(self):
        """Places with same ID but different fields are not equal."""
        place1 = WOFPlace(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
            population=287000,
        )
        place2 = WOFPlace(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
            population=300000,  # Different
        )

        assert place1 != place2

    @pytest.mark.unit
    def test_place_in_collection(self):
        """Places can be stored in collections."""
        place1 = WOFPlace(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )
        place2 = WOFPlace(
            id=SAINT_MICHAEL_REGION_ID,
            name="Saint Michael",
            placetype="region",
        )

        places = [place1, place2]
        assert place1 in places
        assert place2 in places


class TestWOFPlaceEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.unit
    def test_place_with_missing_optional_fields(self):
        """Place can be created with minimal fields."""
        place = WOFPlace(
            id=12345,
            name="Minimal Place",
            placetype="locality",
        )

        assert place.id == 12345
        assert place.name == "Minimal Place"
        assert place.placetype == PlaceType.LOCALITY
        assert place.parent_id is None
        assert place.country is None
        assert place.population is None

    @pytest.mark.unit
    def test_place_with_none_values(self):
        """Place accepts None for optional fields."""
        place = WOFPlace(
            id=12345,
            name="Test",
            placetype="locality",
            parent_id=None,
            country=None,
            population=None,
        )

        assert place.parent_id is None
        assert place.country is None
        assert place.population is None

    @pytest.mark.unit
    def test_place_with_extra_fields(self):
        """Place allows extra fields (extra='allow')."""
        place = WOFPlace(
            id=12345,
            name="Test",
            placetype="locality",
            custom_field="custom_value",
        )

        # Extra fields are stored
        assert hasattr(place, "custom_field")
        assert place.custom_field == "custom_value"

    @pytest.mark.unit
    def test_place_with_empty_superseded_by(self):
        """Place with empty superseded_by list."""
        place = WOFPlace(
            id=12345,
            name="Test",
            placetype="locality",
            superseded_by=[],
        )

        # Empty list is falsy
        assert place.is_superseded is False

    @pytest.mark.unit
    def test_place_with_multiple_superseded_by(self):
        """Place can have multiple superseded_by IDs."""
        place = WOFPlace(
            id=12345,
            name="Test",
            placetype="locality",
            superseded_by=[67890, 11111, 22222],
        )

        assert place.is_superseded is True
        assert len(place.superseded_by) == 3

    @pytest.mark.unit
    def test_place_is_current_default(self):
        """Place is_current defaults to True."""
        place = WOFPlace(
            id=12345,
            name="Test",
            placetype="locality",
        )

        assert place.is_current is True

    @pytest.mark.unit
    def test_place_with_invalid_bbox_length(self):
        """Place with invalid bbox length."""
        place = WOFPlace(
            id=12345,
            name="Test",
            placetype="locality",
            bbox=[-59.62, 13.09],  # Only 2 values
        )

        # get_bounds returns None for invalid bbox
        assert place.get_bounds() is None

    @pytest.mark.unit
    def test_place_with_invalid_centroid_length(self):
        """Place with invalid centroid length."""
        place = WOFPlace(
            id=12345,
            name="Test",
            placetype="locality",
            centroid=[-59.615],  # Only 1 value
        )

        # get_centroid returns None for invalid centroid
        assert place.get_centroid() is None


class TestWOFPlaceWithGeometry:
    """Tests for WOFPlaceWithGeometry model."""

    @pytest.mark.unit
    def test_place_with_geometry_construction(self):
        """WOFPlaceWithGeometry can be created with geometry."""
        place = WOFPlaceWithGeometry(
            id=BRIDGETOWN_LOCALITY_ID,
            name="Bridgetown",
            placetype="locality",
            geometry={
                "type": "Point",
                "coordinates": [-59.615, 13.095],
            },
        )

        assert place.id == BRIDGETOWN_LOCALITY_ID
        assert place.geometry is not None

    @pytest.mark.unit
    def test_place_with_geometry_has_geometry(self):
        """has_geometry returns True when geometry present."""
        place = WOFPlaceWithGeometry(
            id=12345,
            name="Test",
            placetype="locality",
            geometry={"type": "Point", "coordinates": [0, 0]},
        )

        assert place.has_geometry() is True

    @pytest.mark.unit
    def test_place_with_geometry_has_no_geometry(self):
        """has_geometry returns False when geometry absent."""
        place = WOFPlaceWithGeometry(
            id=12345,
            name="Test",
            placetype="locality",
        )

        assert place.has_geometry() is False

    @pytest.mark.unit
    def test_place_with_geometry_get_geometry_type(self):
        """get_geometry_type returns geometry type."""
        place = WOFPlaceWithGeometry(
            id=12345,
            name="Test",
            placetype="locality",
            geometry={"type": "Polygon", "coordinates": [[]]},
        )

        assert place.get_geometry_type() == "Polygon"

    @pytest.mark.unit
    def test_place_with_geometry_get_geometry_type_none(self):
        """get_geometry_type returns None without geometry."""
        place = WOFPlaceWithGeometry(
            id=12345,
            name="Test",
            placetype="locality",
        )

        assert place.get_geometry_type() is None

    @pytest.mark.unit
    def test_place_with_geometry_handles_feature_wrapper(self):
        """get_geometry handles Feature wrapper."""
        place = WOFPlaceWithGeometry(
            id=12345,
            name="Test",
            placetype="locality",
            geometry={
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [0, 0],
                },
            },
        )

        geom_type = place.get_geometry_type()
        assert geom_type == "Point"

    @pytest.mark.unit
    def test_place_with_geometry_get_geometry_object(self):
        """get_geometry returns WOFGeometry object."""
        place = WOFPlaceWithGeometry(
            id=12345,
            name="Test",
            placetype="locality",
            geometry={
                "type": "Point",
                "coordinates": [-59.615, 13.095],
            },
        )

        geom = place.get_geometry()
        assert geom is not None
        assert geom.type == "Point"
        assert geom.coordinates == [-59.615, 13.095]


class TestWOFName:
    """Tests for WOFName model."""

    @pytest.mark.unit
    def test_name_construction(self):
        """WOFName can be created with required fields."""
        name = WOFName(
            place_id=BARBADOS_COUNTRY_ID,
            language="eng",
            name="Barbados",
        )

        assert name.place_id == BARBADOS_COUNTRY_ID
        assert name.language == "eng"
        assert name.name == "Barbados"

    @pytest.mark.unit
    def test_name_with_flags(self):
        """WOFName can store preferred/colloquial flags."""
        name = WOFName(
            place_id=BARBADOS_COUNTRY_ID,
            language="eng_x_preferred",
            name="Barbados",
            preferred=True,
        )

        assert name.preferred is True

    @pytest.mark.unit
    def test_name_is_english(self):
        """is_english returns True for English names."""
        name = WOFName(
            place_id=BARBADOS_COUNTRY_ID,
            language="eng",
            name="Barbados",
        )

        assert name.is_english() is True

    @pytest.mark.unit
    def test_name_is_not_english(self):
        """is_english returns False for non-English names."""
        name = WOFName(
            place_id=BARBADOS_COUNTRY_ID,
            language="fra",
            name="Barbade",
        )

        assert name.is_english() is False

    @pytest.mark.unit
    def test_name_is_preferred(self):
        """is_preferred returns True for preferred names."""
        name = WOFName(
            place_id=BARBADOS_COUNTRY_ID,
            language="eng_x_preferred",
            name="Barbados",
            preferred=True,
        )

        assert name.is_preferred() is True

    @pytest.mark.unit
    def test_name_is_preferred_from_language(self):
        """is_preferred detects from language code."""
        name = WOFName(
            place_id=BARBADOS_COUNTRY_ID,
            language="eng_x_preferred",
            name="Barbados",
        )

        assert name.is_preferred() is True

    @pytest.mark.unit
    def test_name_is_colloquial(self):
        """is_colloquial returns True for colloquial names."""
        name = WOFName(
            place_id=BARBADOS_COUNTRY_ID,
            language="eng_x_colloquial",
            name="Bim",
            colloquial=True,
        )

        assert name.is_colloquial() is True

    @pytest.mark.unit
    def test_name_is_immutable(self):
        """WOFName is frozen (immutable)."""
        name = WOFName(
            place_id=BARBADOS_COUNTRY_ID,
            language="eng",
            name="Barbados",
        )

        with pytest.raises(Exception):  # ValidationError from Pydantic
            name.name = "Changed"
