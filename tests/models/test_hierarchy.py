"""
Unit tests for WOF hierarchy models.

Tests verify hierarchy model construction, navigation, and relationships.
"""

import pytest
from wof_explorer.models.hierarchy import (
    WOFPlaceRef,
    WOFAncestor,
    WOFHierarchy,
    HierarchyPath,
    AncestorChain,
    HierarchyRelationship,
)
from wof_explorer.types import PlaceType

# Known Barbados test data
BARBADOS_COUNTRY_ID = 85632491
SAINT_MICHAEL_REGION_ID = 85670295
BRIDGETOWN_LOCALITY_ID = 102027145


class TestWOFPlaceRef:
    """Tests for WOFPlaceRef model."""

    @pytest.mark.unit
    def test_place_ref_construction(self):
        """Place reference can be created with required fields."""
        ref = WOFPlaceRef(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )

        assert ref.id == BARBADOS_COUNTRY_ID
        assert ref.name == "Barbados"
        assert ref.placetype == PlaceType.COUNTRY

    @pytest.mark.unit
    def test_place_ref_hash(self):
        """Place reference is hashable for use in sets."""
        ref1 = WOFPlaceRef(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )
        ref2 = WOFPlaceRef(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )
        ref3 = WOFPlaceRef(
            id=SAINT_MICHAEL_REGION_ID,
            name="Saint Michael",
            placetype="region",
        )

        # Can be added to a set
        refs = {ref1, ref2, ref3}
        # Duplicates removed (same hash)
        assert len(refs) == 2
        assert ref1 in refs
        assert ref3 in refs

    @pytest.mark.unit
    def test_place_ref_frozen(self):
        """Place reference is immutable."""
        ref = WOFPlaceRef(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )

        with pytest.raises(Exception):  # ValidationError from Pydantic
            ref.name = "Changed"

    @pytest.mark.unit
    def test_place_ref_placetype_coercion(self):
        """Placetype string is coerced to PlaceType enum."""
        ref = WOFPlaceRef(
            id=BRIDGETOWN_LOCALITY_ID,
            name="Bridgetown",
            placetype="locality",
        )

        assert isinstance(ref.placetype, PlaceType)
        assert ref.placetype == PlaceType.LOCALITY

    @pytest.mark.unit
    def test_place_ref_placetype_serialization(self):
        """Placetype enum is serialized as string."""
        ref = WOFPlaceRef(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )

        data = ref.model_dump()
        assert data["placetype"] == "country"
        assert isinstance(data["placetype"], str)

    @pytest.mark.unit
    def test_place_ref_none_placetype_defaults_to_custom(self):
        """None placetype defaults to CUSTOM."""
        ref = WOFPlaceRef(
            id=12345,
            name="Test",
            placetype=None,
        )

        assert ref.placetype == PlaceType.CUSTOM

    @pytest.mark.unit
    def test_place_ref_equality(self):
        """Place references with same values are equal."""
        ref1 = WOFPlaceRef(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )
        ref2 = WOFPlaceRef(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )

        assert ref1 == ref2

    @pytest.mark.unit
    def test_place_ref_inequality(self):
        """Place references with different values are not equal."""
        ref1 = WOFPlaceRef(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )
        ref2 = WOFPlaceRef(
            id=SAINT_MICHAEL_REGION_ID,
            name="Saint Michael",
            placetype="region",
        )

        assert ref1 != ref2


class TestWOFAncestor:
    """Tests for WOFAncestor model."""

    @pytest.mark.unit
    def test_ancestor_construction(self):
        """Ancestor can be created with required fields and level."""
        ancestor = WOFAncestor(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
            level=1,
        )

        assert ancestor.id == BARBADOS_COUNTRY_ID
        assert ancestor.name == "Barbados"
        assert ancestor.placetype == PlaceType.COUNTRY
        assert ancestor.level == 1

    @pytest.mark.unit
    def test_ancestor_is_country(self):
        """is_country() returns True for country placetype."""
        country = WOFAncestor(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )

        assert country.is_country() is True

    @pytest.mark.unit
    def test_ancestor_is_not_country(self):
        """is_country() returns False for non-country placetype."""
        region = WOFAncestor(
            id=SAINT_MICHAEL_REGION_ID,
            name="Saint Michael",
            placetype="region",
        )

        assert region.is_country() is False

    @pytest.mark.unit
    def test_ancestor_is_region(self):
        """is_region() returns True for region placetype."""
        region = WOFAncestor(
            id=SAINT_MICHAEL_REGION_ID,
            name="Saint Michael",
            placetype="region",
        )

        assert region.is_region() is True

    @pytest.mark.unit
    def test_ancestor_is_not_region(self):
        """is_region() returns False for non-region placetype."""
        country = WOFAncestor(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )

        assert country.is_region() is False

    @pytest.mark.unit
    def test_ancestor_is_admin(self):
        """is_admin() returns True for administrative placetypes."""
        country = WOFAncestor(id=1, name="Country", placetype="country")
        region = WOFAncestor(id=2, name="Region", placetype="region")
        locality = WOFAncestor(id=3, name="Locality", placetype="locality")

        assert country.is_admin() is True
        assert region.is_admin() is True
        assert locality.is_admin() is True

    @pytest.mark.unit
    def test_ancestor_is_not_admin(self):
        """is_admin() returns False for non-administrative placetypes."""
        neighbourhood = WOFAncestor(id=1, name="Hood", placetype="neighbourhood")

        assert neighbourhood.is_admin() is False

    @pytest.mark.unit
    def test_ancestor_hash(self):
        """Ancestor is hashable for use in sets."""
        ancestor1 = WOFAncestor(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )
        ancestor2 = WOFAncestor(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )

        # Can be added to a set
        ancestors = {ancestor1, ancestor2}
        assert len(ancestors) == 1

    @pytest.mark.unit
    def test_ancestor_with_optional_fields(self):
        """Ancestor can be created with optional country/region fields."""
        ancestor = WOFAncestor(
            id=SAINT_MICHAEL_REGION_ID,
            name="Saint Michael",
            placetype="region",
            country="BB",
            region="Saint Michael",
            level=0,
        )

        assert ancestor.country == "BB"
        assert ancestor.region == "Saint Michael"

    @pytest.mark.unit
    def test_ancestor_default_level_is_zero(self):
        """Ancestor level defaults to 0."""
        ancestor = WOFAncestor(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )

        assert ancestor.level == 0

    @pytest.mark.unit
    def test_ancestor_frozen(self):
        """Ancestor is immutable."""
        ancestor = WOFAncestor(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )

        with pytest.raises(Exception):
            ancestor.level = 5

    @pytest.mark.unit
    def test_ancestor_placetype_coercion(self):
        """Placetype string is coerced to PlaceType enum."""
        ancestor = WOFAncestor(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )

        assert isinstance(ancestor.placetype, PlaceType)
        assert ancestor.placetype == PlaceType.COUNTRY

    @pytest.mark.unit
    def test_ancestor_placetype_serialization(self):
        """Placetype enum is serialized as string."""
        ancestor = WOFAncestor(
            id=BARBADOS_COUNTRY_ID,
            name="Barbados",
            placetype="country",
        )

        data = ancestor.model_dump()
        assert data["placetype"] == "country"
        assert isinstance(data["placetype"], str)


class TestWOFHierarchy:
    """Tests for WOFHierarchy model."""

    @pytest.mark.unit
    def test_hierarchy_construction(self):
        """Hierarchy can be created with place_id."""
        hierarchy = WOFHierarchy(place_id=BRIDGETOWN_LOCALITY_ID)

        assert hierarchy.place_id == BRIDGETOWN_LOCALITY_ID
        assert hierarchy.ancestors == []
        assert hierarchy.descendants_count == {}
        assert hierarchy.parent is None
        assert hierarchy.children == []
        assert hierarchy.siblings == []

    @pytest.mark.unit
    def test_hierarchy_get_country(self):
        """get_country() returns country ancestor."""
        hierarchy = WOFHierarchy(
            place_id=BRIDGETOWN_LOCALITY_ID,
            ancestors=[
                WOFAncestor(
                    id=BARBADOS_COUNTRY_ID,
                    name="Barbados",
                    placetype="country",
                    level=2,
                ),
                WOFAncestor(
                    id=SAINT_MICHAEL_REGION_ID,
                    name="Saint Michael",
                    placetype="region",
                    level=1,
                ),
            ],
        )

        country = hierarchy.get_country()
        assert country is not None
        assert country.id == BARBADOS_COUNTRY_ID
        assert country.placetype == PlaceType.COUNTRY

    @pytest.mark.unit
    def test_hierarchy_get_country_none_without_country(self):
        """get_country() returns None when no country ancestor."""
        hierarchy = WOFHierarchy(
            place_id=BRIDGETOWN_LOCALITY_ID,
            ancestors=[
                WOFAncestor(
                    id=SAINT_MICHAEL_REGION_ID,
                    name="Saint Michael",
                    placetype="region",
                ),
            ],
        )

        assert hierarchy.get_country() is None

    @pytest.mark.unit
    def test_hierarchy_get_region(self):
        """get_region() returns region ancestor."""
        hierarchy = WOFHierarchy(
            place_id=BRIDGETOWN_LOCALITY_ID,
            ancestors=[
                WOFAncestor(
                    id=SAINT_MICHAEL_REGION_ID,
                    name="Saint Michael",
                    placetype="region",
                ),
            ],
        )

        region = hierarchy.get_region()
        assert region is not None
        assert region.id == SAINT_MICHAEL_REGION_ID
        assert region.placetype == PlaceType.REGION

    @pytest.mark.unit
    def test_hierarchy_get_region_none_without_region(self):
        """get_region() returns None when no region ancestor."""
        hierarchy = WOFHierarchy(
            place_id=BRIDGETOWN_LOCALITY_ID,
            ancestors=[
                WOFAncestor(
                    id=BARBADOS_COUNTRY_ID,
                    name="Barbados",
                    placetype="country",
                ),
            ],
        )

        assert hierarchy.get_region() is None

    @pytest.mark.unit
    def test_hierarchy_get_admin_chain(self):
        """get_admin_chain() returns only administrative ancestors."""
        hierarchy = WOFHierarchy(
            place_id=12345,
            ancestors=[
                WOFAncestor(id=1, name="Country", placetype="country"),
                WOFAncestor(id=2, name="Region", placetype="region"),
                WOFAncestor(id=3, name="Locality", placetype="locality"),
                WOFAncestor(id=4, name="Neighbourhood", placetype="neighbourhood"),
            ],
        )

        admin_chain = hierarchy.get_admin_chain()
        assert len(admin_chain) == 3
        assert all(a.is_admin() for a in admin_chain)

    @pytest.mark.unit
    def test_hierarchy_get_ancestor_by_type(self):
        """get_ancestor_by_type() finds ancestor of specific type."""
        hierarchy = WOFHierarchy(
            place_id=BRIDGETOWN_LOCALITY_ID,
            ancestors=[
                WOFAncestor(
                    id=BARBADOS_COUNTRY_ID,
                    name="Barbados",
                    placetype="country",
                ),
                WOFAncestor(
                    id=SAINT_MICHAEL_REGION_ID,
                    name="Saint Michael",
                    placetype="region",
                ),
            ],
        )

        region = hierarchy.get_ancestor_by_type("region")
        assert region is not None
        assert region.id == SAINT_MICHAEL_REGION_ID

    @pytest.mark.unit
    def test_hierarchy_get_ancestor_by_type_not_found(self):
        """get_ancestor_by_type() returns None if type not found."""
        hierarchy = WOFHierarchy(
            place_id=BRIDGETOWN_LOCALITY_ID,
            ancestors=[
                WOFAncestor(
                    id=BARBADOS_COUNTRY_ID,
                    name="Barbados",
                    placetype="country",
                ),
            ],
        )

        assert hierarchy.get_ancestor_by_type("region") is None

    @pytest.mark.unit
    def test_hierarchy_get_depth(self):
        """get_depth() returns number of ancestors."""
        hierarchy = WOFHierarchy(
            place_id=BRIDGETOWN_LOCALITY_ID,
            ancestors=[
                WOFAncestor(id=1, name="A", placetype="country"),
                WOFAncestor(id=2, name="B", placetype="region"),
                WOFAncestor(id=3, name="C", placetype="locality"),
            ],
        )

        assert hierarchy.get_depth() == 3

    @pytest.mark.unit
    def test_hierarchy_is_leaf(self):
        """is_leaf() returns True when no descendants."""
        hierarchy = WOFHierarchy(
            place_id=BRIDGETOWN_LOCALITY_ID,
            descendants_count={},
        )

        assert hierarchy.is_leaf() is True

    @pytest.mark.unit
    def test_hierarchy_is_not_leaf(self):
        """is_leaf() returns False when has descendants."""
        hierarchy = WOFHierarchy(
            place_id=SAINT_MICHAEL_REGION_ID,
            descendants_count={PlaceType.LOCALITY: 5},
        )

        assert hierarchy.is_leaf() is False

    @pytest.mark.unit
    def test_hierarchy_is_root(self):
        """is_root() returns True when no ancestors."""
        hierarchy = WOFHierarchy(
            place_id=BARBADOS_COUNTRY_ID,
            ancestors=[],
        )

        assert hierarchy.is_root() is True

    @pytest.mark.unit
    def test_hierarchy_is_not_root(self):
        """is_root() returns False when has ancestors."""
        hierarchy = WOFHierarchy(
            place_id=BRIDGETOWN_LOCALITY_ID,
            ancestors=[
                WOFAncestor(
                    id=BARBADOS_COUNTRY_ID,
                    name="Barbados",
                    placetype="country",
                ),
            ],
        )

        assert hierarchy.is_root() is False

    @pytest.mark.unit
    def test_hierarchy_has_children(self):
        """has_children() returns True when children present."""
        hierarchy = WOFHierarchy(
            place_id=SAINT_MICHAEL_REGION_ID,
            children=[
                WOFPlaceRef(
                    id=BRIDGETOWN_LOCALITY_ID,
                    name="Bridgetown",
                    placetype="locality",
                ),
            ],
        )

        assert hierarchy.has_children() is True

    @pytest.mark.unit
    def test_hierarchy_has_no_children(self):
        """has_children() returns False when no children."""
        hierarchy = WOFHierarchy(
            place_id=BRIDGETOWN_LOCALITY_ID,
            children=[],
        )

        assert hierarchy.has_children() is False

    @pytest.mark.unit
    def test_hierarchy_has_siblings(self):
        """has_siblings() returns True when siblings present."""
        hierarchy = WOFHierarchy(
            place_id=BRIDGETOWN_LOCALITY_ID,
            siblings=[
                WOFPlaceRef(id=12345, name="Other Locality", placetype="locality"),
            ],
        )

        assert hierarchy.has_siblings() is True

    @pytest.mark.unit
    def test_hierarchy_has_no_siblings(self):
        """has_siblings() returns False when no siblings."""
        hierarchy = WOFHierarchy(
            place_id=BRIDGETOWN_LOCALITY_ID,
            siblings=[],
        )

        assert hierarchy.has_siblings() is False

    @pytest.mark.unit
    def test_hierarchy_get_immediate_parent(self):
        """get_immediate_parent() returns level 0 ancestor."""
        parent = WOFAncestor(
            id=SAINT_MICHAEL_REGION_ID,
            name="Saint Michael",
            placetype="region",
            level=0,
        )
        hierarchy = WOFHierarchy(
            place_id=BRIDGETOWN_LOCALITY_ID,
            ancestors=[
                parent,
                WOFAncestor(
                    id=BARBADOS_COUNTRY_ID,
                    name="Barbados",
                    placetype="country",
                    level=1,
                ),
            ],
        )

        immediate = hierarchy.get_immediate_parent()
        assert immediate is not None
        assert immediate.id == SAINT_MICHAEL_REGION_ID
        assert immediate.level == 0

    @pytest.mark.unit
    def test_hierarchy_get_immediate_parent_from_parent_field(self):
        """get_immediate_parent() falls back to parent field."""
        parent = WOFAncestor(
            id=SAINT_MICHAEL_REGION_ID,
            name="Saint Michael",
            placetype="region",
        )
        hierarchy = WOFHierarchy(
            place_id=BRIDGETOWN_LOCALITY_ID,
            parent=parent,
            ancestors=[],
        )

        immediate = hierarchy.get_immediate_parent()
        assert immediate is not None
        assert immediate.id == SAINT_MICHAEL_REGION_ID

    @pytest.mark.unit
    def test_hierarchy_get_ancestors_by_level(self):
        """get_ancestors_by_level() returns ancestors at specific level."""
        hierarchy = WOFHierarchy(
            place_id=12345,
            ancestors=[
                WOFAncestor(id=1, name="A", placetype="region", level=0),
                WOFAncestor(id=2, name="B", placetype="country", level=1),
                WOFAncestor(id=3, name="C", placetype="region", level=0),
            ],
        )

        level_0 = hierarchy.get_ancestors_by_level(0)
        assert len(level_0) == 2
        assert all(a.level == 0 for a in level_0)

    @pytest.mark.unit
    def test_hierarchy_to_path(self):
        """to_path() converts hierarchy to path string."""
        hierarchy = WOFHierarchy(
            place_id=BRIDGETOWN_LOCALITY_ID,
            ancestors=[
                WOFAncestor(
                    id=SAINT_MICHAEL_REGION_ID,
                    name="Saint Michael",
                    placetype="region",
                    level=0,
                ),
                WOFAncestor(
                    id=BARBADOS_COUNTRY_ID,
                    name="Barbados",
                    placetype="country",
                    level=1,
                ),
            ],
        )

        path = hierarchy.to_path()
        assert path == "Saint Michael > Barbados"

    @pytest.mark.unit
    def test_hierarchy_to_path_custom_separator(self):
        """to_path() uses custom separator."""
        hierarchy = WOFHierarchy(
            place_id=BRIDGETOWN_LOCALITY_ID,
            ancestors=[
                WOFAncestor(id=1, name="A", placetype="region", level=0),
                WOFAncestor(id=2, name="B", placetype="country", level=1),
            ],
        )

        path = hierarchy.to_path(separator=" / ")
        assert path == "A / B"

    @pytest.mark.unit
    def test_hierarchy_to_path_empty(self):
        """to_path() returns empty string when no ancestors."""
        hierarchy = WOFHierarchy(
            place_id=BARBADOS_COUNTRY_ID,
            ancestors=[],
        )

        assert hierarchy.to_path() == ""

    @pytest.mark.unit
    def test_hierarchy_descendants_count_coercion(self):
        """descendants_count keys are coerced to PlaceType."""
        hierarchy = WOFHierarchy(
            place_id=SAINT_MICHAEL_REGION_ID,
            descendants_count={
                "locality": 5,
                "neighbourhood": 20,
            },
        )

        assert PlaceType.LOCALITY in hierarchy.descendants_count
        assert PlaceType.NEIGHBOURHOOD in hierarchy.descendants_count
        assert hierarchy.descendants_count[PlaceType.LOCALITY] == 5
        assert hierarchy.descendants_count[PlaceType.NEIGHBOURHOOD] == 20

    @pytest.mark.unit
    def test_hierarchy_descendants_count_serialization(self):
        """descendants_count is serialized with string keys."""
        hierarchy = WOFHierarchy(
            place_id=SAINT_MICHAEL_REGION_ID,
            descendants_count={PlaceType.LOCALITY: 5},
        )

        data = hierarchy.model_dump()
        assert "locality" in data["descendants_count"]
        assert data["descendants_count"]["locality"] == 5


class TestHierarchyPath:
    """Tests for HierarchyPath model."""

    @pytest.mark.unit
    def test_path_to_string(self):
        """to_string() converts path to string representation."""
        path = HierarchyPath(
            path=[
                WOFPlaceRef(id=1, name="Barbados", placetype="country"),
                WOFPlaceRef(id=2, name="Saint Michael", placetype="region"),
                WOFPlaceRef(id=3, name="Bridgetown", placetype="locality"),
            ]
        )

        result = path.to_string()
        assert result == "Barbados > Saint Michael > Bridgetown"

    @pytest.mark.unit
    def test_path_to_string_custom_separator(self):
        """to_string() uses custom separator."""
        path = HierarchyPath(
            path=[
                WOFPlaceRef(id=1, name="A", placetype="country"),
                WOFPlaceRef(id=2, name="B", placetype="region"),
            ]
        )

        result = path.to_string(separator=" / ")
        assert result == "A / B"

    @pytest.mark.unit
    def test_path_get_types(self):
        """get_types() returns list of placetype strings."""
        path = HierarchyPath(
            path=[
                WOFPlaceRef(id=1, name="A", placetype="country"),
                WOFPlaceRef(id=2, name="B", placetype="region"),
                WOFPlaceRef(id=3, name="C", placetype="locality"),
            ]
        )

        types = path.get_types()
        assert types == ["country", "region", "locality"]

    @pytest.mark.unit
    def test_path_contains_type(self):
        """contains_type() checks if placetype is in path."""
        path = HierarchyPath(
            path=[
                WOFPlaceRef(id=1, name="A", placetype="country"),
                WOFPlaceRef(id=2, name="B", placetype="region"),
            ]
        )

        assert path.contains_type("country") is True
        assert path.contains_type("region") is True
        assert path.contains_type("locality") is False

    @pytest.mark.unit
    def test_path_get_by_type(self):
        """get_by_type() retrieves place by placetype."""
        region_ref = WOFPlaceRef(
            id=SAINT_MICHAEL_REGION_ID,
            name="Saint Michael",
            placetype="region",
        )
        path = HierarchyPath(
            path=[
                WOFPlaceRef(id=1, name="Barbados", placetype="country"),
                region_ref,
                WOFPlaceRef(id=3, name="Bridgetown", placetype="locality"),
            ]
        )

        result = path.get_by_type("region")
        assert result is not None
        assert result.id == SAINT_MICHAEL_REGION_ID

    @pytest.mark.unit
    def test_path_get_by_type_not_found(self):
        """get_by_type() returns None if type not found."""
        path = HierarchyPath(
            path=[
                WOFPlaceRef(id=1, name="A", placetype="country"),
            ]
        )

        assert path.get_by_type("region") is None

    @pytest.mark.unit
    def test_path_get_depth(self):
        """get_depth() returns number of places in path."""
        path = HierarchyPath(
            path=[
                WOFPlaceRef(id=1, name="A", placetype="country"),
                WOFPlaceRef(id=2, name="B", placetype="region"),
                WOFPlaceRef(id=3, name="C", placetype="locality"),
            ]
        )

        assert path.get_depth() == 3

    @pytest.mark.unit
    def test_path_is_valid(self):
        """is_valid() returns True when path has places."""
        path = HierarchyPath(
            path=[
                WOFPlaceRef(id=1, name="A", placetype="country"),
            ]
        )

        assert path.is_valid() is True

    @pytest.mark.unit
    def test_path_is_not_valid(self):
        """is_valid() returns False when path is empty."""
        path = HierarchyPath(path=[])

        assert path.is_valid() is False

    @pytest.mark.unit
    def test_path_reverse(self):
        """reverse() returns path in reverse order."""
        path = HierarchyPath(
            path=[
                WOFPlaceRef(id=1, name="A", placetype="country"),
                WOFPlaceRef(id=2, name="B", placetype="region"),
                WOFPlaceRef(id=3, name="C", placetype="locality"),
            ]
        )

        reversed_path = path.reverse()
        assert reversed_path.to_string() == "C > B > A"
        assert reversed_path.path[0].id == 3
        assert reversed_path.path[-1].id == 1

    @pytest.mark.unit
    def test_path_reverse_does_not_mutate_original(self):
        """reverse() does not mutate original path."""
        path = HierarchyPath(
            path=[
                WOFPlaceRef(id=1, name="A", placetype="country"),
                WOFPlaceRef(id=2, name="B", placetype="region"),
            ]
        )

        reversed_path = path.reverse()
        assert path.path[0].id == 1
        assert reversed_path.path[0].id == 2

    @pytest.mark.unit
    def test_path_truncate(self):
        """truncate() returns path limited to specified depth."""
        path = HierarchyPath(
            path=[
                WOFPlaceRef(id=1, name="A", placetype="country"),
                WOFPlaceRef(id=2, name="B", placetype="region"),
                WOFPlaceRef(id=3, name="C", placetype="locality"),
            ]
        )

        truncated = path.truncate(2)
        assert truncated.get_depth() == 2
        assert truncated.path[0].id == 1
        assert truncated.path[1].id == 2

    @pytest.mark.unit
    def test_path_truncate_does_not_mutate_original(self):
        """truncate() does not mutate original path."""
        path = HierarchyPath(
            path=[
                WOFPlaceRef(id=1, name="A", placetype="country"),
                WOFPlaceRef(id=2, name="B", placetype="region"),
                WOFPlaceRef(id=3, name="C", placetype="locality"),
            ]
        )

        truncated = path.truncate(1)
        assert path.get_depth() == 3
        assert truncated.get_depth() == 1

    @pytest.mark.unit
    def test_path_extend(self):
        """extend() adds new place to path."""
        path = HierarchyPath(
            path=[
                WOFPlaceRef(id=1, name="A", placetype="country"),
                WOFPlaceRef(id=2, name="B", placetype="region"),
            ]
        )

        new_ref = WOFPlaceRef(id=3, name="C", placetype="locality")
        extended = path.extend(new_ref)

        assert extended.get_depth() == 3
        assert extended.path[-1].id == 3

    @pytest.mark.unit
    def test_path_extend_does_not_mutate_original(self):
        """extend() does not mutate original path."""
        path = HierarchyPath(
            path=[
                WOFPlaceRef(id=1, name="A", placetype="country"),
            ]
        )

        new_ref = WOFPlaceRef(id=2, name="B", placetype="region")
        extended = path.extend(new_ref)

        assert path.get_depth() == 1
        assert extended.get_depth() == 2


class TestAncestorChain:
    """Tests for AncestorChain model."""

    @pytest.mark.unit
    def test_chain_get_immediate_parent(self):
        """get_immediate_parent() returns first ancestor."""
        chain = AncestorChain(
            ancestors=[
                WOFAncestor(id=1, name="Parent", placetype="region", level=0),
                WOFAncestor(id=2, name="Grandparent", placetype="country", level=1),
            ]
        )

        parent = chain.get_immediate_parent()
        assert parent is not None
        assert parent.id == 1
        assert parent.name == "Parent"

    @pytest.mark.unit
    def test_chain_get_immediate_parent_empty(self):
        """get_immediate_parent() returns None for empty chain."""
        chain = AncestorChain(ancestors=[])

        assert chain.get_immediate_parent() is None

    @pytest.mark.unit
    def test_chain_get_root(self):
        """get_root() returns last ancestor."""
        chain = AncestorChain(
            ancestors=[
                WOFAncestor(id=1, name="Parent", placetype="region", level=0),
                WOFAncestor(id=2, name="Grandparent", placetype="country", level=1),
            ]
        )

        root = chain.get_root()
        assert root is not None
        assert root.id == 2
        assert root.name == "Grandparent"

    @pytest.mark.unit
    def test_chain_get_root_empty(self):
        """get_root() returns None for empty chain."""
        chain = AncestorChain(ancestors=[])

        assert chain.get_root() is None

    @pytest.mark.unit
    def test_chain_get_at_level(self):
        """get_at_level() returns ancestor at specific level."""
        chain = AncestorChain(
            ancestors=[
                WOFAncestor(id=1, name="A", placetype="region", level=0),
                WOFAncestor(id=2, name="B", placetype="country", level=1),
                WOFAncestor(id=3, name="C", placetype="locality", level=2),
            ]
        )

        level_1 = chain.get_at_level(1)
        assert level_1 is not None
        assert level_1.id == 2

    @pytest.mark.unit
    def test_chain_get_at_level_not_found(self):
        """get_at_level() returns None if level not found."""
        chain = AncestorChain(
            ancestors=[
                WOFAncestor(id=1, name="A", placetype="country", level=0),
            ]
        )

        assert chain.get_at_level(5) is None

    @pytest.mark.unit
    def test_chain_get_countries(self):
        """get_countries() returns all country-level ancestors."""
        chain = AncestorChain(
            ancestors=[
                WOFAncestor(id=1, name="Region", placetype="region", level=0),
                WOFAncestor(id=2, name="Country1", placetype="country", level=1),
                WOFAncestor(id=3, name="Country2", placetype="country", level=2),
            ]
        )

        countries = chain.get_countries()
        assert len(countries) == 2
        assert all(a.is_country() for a in countries)

    @pytest.mark.unit
    def test_chain_get_regions(self):
        """get_regions() returns all region-level ancestors."""
        chain = AncestorChain(
            ancestors=[
                WOFAncestor(id=1, name="Region1", placetype="region", level=0),
                WOFAncestor(id=2, name="Country", placetype="country", level=1),
                WOFAncestor(id=3, name="Region2", placetype="region", level=2),
            ]
        )

        regions = chain.get_regions()
        assert len(regions) == 2
        assert all(a.is_region() for a in regions)

    @pytest.mark.unit
    def test_chain_to_dict(self):
        """to_dict() converts to dictionary keyed by placetype."""
        chain = AncestorChain(
            ancestors=[
                WOFAncestor(
                    id=SAINT_MICHAEL_REGION_ID,
                    name="Saint Michael",
                    placetype="region",
                ),
                WOFAncestor(
                    id=BARBADOS_COUNTRY_ID,
                    name="Barbados",
                    placetype="country",
                ),
            ]
        )

        result = chain.to_dict()
        assert "region" in result
        assert "country" in result
        assert result["region"].id == SAINT_MICHAEL_REGION_ID
        assert result["country"].id == BARBADOS_COUNTRY_ID

    @pytest.mark.unit
    def test_chain_filter_by_type(self):
        """filter_by_type() returns ancestors of specific type."""
        chain = AncestorChain(
            ancestors=[
                WOFAncestor(id=1, name="Region", placetype="region"),
                WOFAncestor(id=2, name="Country", placetype="country"),
                WOFAncestor(id=3, name="Locality", placetype="locality"),
            ]
        )

        regions = chain.filter_by_type("region")
        assert len(regions) == 1
        assert regions[0].placetype == PlaceType.REGION

    @pytest.mark.unit
    def test_chain_filter_by_type_empty(self):
        """filter_by_type() returns empty list if type not found."""
        chain = AncestorChain(
            ancestors=[
                WOFAncestor(id=1, name="Country", placetype="country"),
            ]
        )

        assert chain.filter_by_type("region") == []


class TestHierarchyRelationship:
    """Tests for HierarchyRelationship model."""

    @pytest.mark.unit
    def test_relationship_construction(self):
        """Relationship can be created with required fields."""
        from_place = WOFPlaceRef(
            id=BRIDGETOWN_LOCALITY_ID,
            name="Bridgetown",
            placetype="locality",
        )
        to_place = WOFPlaceRef(
            id=SAINT_MICHAEL_REGION_ID,
            name="Saint Michael",
            placetype="region",
        )

        rel = HierarchyRelationship(
            from_place=from_place,
            to_place=to_place,
            relationship_type="parent",
            distance=1,
        )

        assert rel.from_place.id == BRIDGETOWN_LOCALITY_ID
        assert rel.to_place.id == SAINT_MICHAEL_REGION_ID
        assert rel.relationship_type == "parent"
        assert rel.distance == 1

    @pytest.mark.unit
    def test_relationship_is_direct(self):
        """is_direct() returns True when distance is 1."""
        rel = HierarchyRelationship(
            from_place=WOFPlaceRef(id=1, name="A", placetype="locality"),
            to_place=WOFPlaceRef(id=2, name="B", placetype="region"),
            relationship_type="parent",
            distance=1,
        )

        assert rel.is_direct() is True

    @pytest.mark.unit
    def test_relationship_is_not_direct(self):
        """is_direct() returns False when distance is not 1."""
        rel = HierarchyRelationship(
            from_place=WOFPlaceRef(id=1, name="A", placetype="locality"),
            to_place=WOFPlaceRef(id=2, name="B", placetype="country"),
            relationship_type="ancestor",
            distance=2,
        )

        assert rel.is_direct() is False

    @pytest.mark.unit
    def test_relationship_is_parent_child(self):
        """is_parent_child() returns True for parent/child with distance 1."""
        parent_rel = HierarchyRelationship(
            from_place=WOFPlaceRef(id=1, name="A", placetype="locality"),
            to_place=WOFPlaceRef(id=2, name="B", placetype="region"),
            relationship_type="parent",
            distance=1,
        )
        child_rel = HierarchyRelationship(
            from_place=WOFPlaceRef(id=2, name="B", placetype="region"),
            to_place=WOFPlaceRef(id=1, name="A", placetype="locality"),
            relationship_type="child",
            distance=1,
        )

        assert parent_rel.is_parent_child() is True
        assert child_rel.is_parent_child() is True

    @pytest.mark.unit
    def test_relationship_is_not_parent_child(self):
        """is_parent_child() returns False for non-parent/child."""
        rel = HierarchyRelationship(
            from_place=WOFPlaceRef(id=1, name="A", placetype="locality"),
            to_place=WOFPlaceRef(id=2, name="B", placetype="locality"),
            relationship_type="sibling",
            distance=0,
        )

        assert rel.is_parent_child() is False

    @pytest.mark.unit
    def test_relationship_is_sibling(self):
        """is_sibling() returns True for sibling relationship."""
        rel = HierarchyRelationship(
            from_place=WOFPlaceRef(id=1, name="A", placetype="locality"),
            to_place=WOFPlaceRef(id=2, name="B", placetype="locality"),
            relationship_type="sibling",
        )

        assert rel.is_sibling() is True

    @pytest.mark.unit
    def test_relationship_is_not_sibling(self):
        """is_sibling() returns False for non-sibling relationship."""
        rel = HierarchyRelationship(
            from_place=WOFPlaceRef(id=1, name="A", placetype="locality"),
            to_place=WOFPlaceRef(id=2, name="B", placetype="region"),
            relationship_type="parent",
        )

        assert rel.is_sibling() is False

    @pytest.mark.unit
    def test_relationship_reverse(self):
        """reverse() swaps relationship direction."""
        rel = HierarchyRelationship(
            from_place=WOFPlaceRef(id=1, name="Child", placetype="locality"),
            to_place=WOFPlaceRef(id=2, name="Parent", placetype="region"),
            relationship_type="parent",
            distance=1,
        )

        reversed_rel = rel.reverse()
        assert reversed_rel.from_place.id == 2
        assert reversed_rel.to_place.id == 1
        assert reversed_rel.relationship_type == "child"
        assert reversed_rel.distance == 1

    @pytest.mark.unit
    def test_relationship_reverse_sibling(self):
        """reverse() keeps sibling as sibling."""
        rel = HierarchyRelationship(
            from_place=WOFPlaceRef(id=1, name="A", placetype="locality"),
            to_place=WOFPlaceRef(id=2, name="B", placetype="locality"),
            relationship_type="sibling",
        )

        reversed_rel = rel.reverse()
        assert reversed_rel.relationship_type == "sibling"

    @pytest.mark.unit
    def test_relationship_reverse_ancestor_descendant(self):
        """reverse() swaps ancestor/descendant."""
        rel = HierarchyRelationship(
            from_place=WOFPlaceRef(id=1, name="Descendant", placetype="locality"),
            to_place=WOFPlaceRef(id=2, name="Ancestor", placetype="country"),
            relationship_type="ancestor",
            distance=2,
        )

        reversed_rel = rel.reverse()
        assert reversed_rel.relationship_type == "descendant"

    @pytest.mark.unit
    def test_relationship_default_distance(self):
        """Relationship defaults to distance 1."""
        rel = HierarchyRelationship(
            from_place=WOFPlaceRef(id=1, name="A", placetype="locality"),
            to_place=WOFPlaceRef(id=2, name="B", placetype="region"),
            relationship_type="parent",
        )

        assert rel.distance == 1
