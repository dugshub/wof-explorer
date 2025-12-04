"""
Hierarchy models for WOF place relationships.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_serializer, field_validator, ConfigDict
from wof_explorer.types import (
    PlaceID,
    PlaceType,
    PlacetypeLike,
    coerce_placetype,
    normalize_placetype,
)


class WOFPlaceRef(BaseModel):
    """Lightweight reference to a place."""

    id: PlaceID
    name: str
    placetype: PlaceType

    model_config = ConfigDict(frozen=True)

    def __hash__(self):
        """Make hashable for use in sets."""
        return hash((self.id, self.name, self.placetype))

    @field_validator("placetype", mode="before")
    @classmethod
    def _coerce_placetype(cls, value):
        if value is None:
            return PlaceType.CUSTOM
        return coerce_placetype(value)

    @field_serializer("placetype")
    def _serialize_placetype(self, value: PlaceType) -> str:
        return value.value


class WOFAncestor(BaseModel):
    """Represents an ancestor in the geographic hierarchy."""

    id: PlaceID
    name: str
    placetype: PlaceType
    country: Optional[str] = None
    region: Optional[str] = None
    level: int = Field(0, description="Hierarchy level (0=immediate parent)")

    model_config = ConfigDict(frozen=True)

    def is_country(self) -> bool:
        """Check if ancestor is country level."""
        return self.placetype is PlaceType.COUNTRY

    def is_region(self) -> bool:
        """Check if ancestor is region level."""
        return self.placetype is PlaceType.REGION

    def is_admin(self) -> bool:
        """Check if ancestor is administrative level."""
        return PlaceType.is_admin_level(self.placetype)

    def __hash__(self):
        """Make hashable for use in sets."""
        return hash((self.id, self.name, self.placetype))

    @field_validator("placetype", mode="before")
    @classmethod
    def _coerce_placetype(cls, value):
        if value is None:
            return PlaceType.CUSTOM
        return coerce_placetype(value)

    @field_serializer("placetype")
    def _serialize_placetype(self, value: PlaceType) -> str:
        return value.value


class WOFHierarchy(BaseModel):
    """Complete hierarchy information for a place."""

    place_id: PlaceID
    ancestors: List[WOFAncestor] = Field(default_factory=list)
    descendants_count: Dict[PlaceType, int] = Field(default_factory=dict)
    parent: Optional[WOFAncestor] = None
    children: List[WOFPlaceRef] = Field(default_factory=list)
    siblings: List[WOFPlaceRef] = Field(default_factory=list)

    def get_country(self) -> Optional[WOFAncestor]:
        """Get country ancestor."""
        for ancestor in self.ancestors:
            if ancestor.is_country():
                return ancestor
        return None

    def get_region(self) -> Optional[WOFAncestor]:
        """Get region ancestor."""
        for ancestor in self.ancestors:
            if ancestor.is_region():
                return ancestor
        return None

    def get_admin_chain(self) -> List[WOFAncestor]:
        """Get administrative hierarchy chain."""
        return [a for a in self.ancestors if a.is_admin()]

    @field_validator("descendants_count", mode="before")
    @classmethod
    def _coerce_descendants_count(
        cls, value: Optional[Dict[Any, int]]
    ) -> Dict[PlaceType, int]:
        if not value:
            return {}
        coerced: Dict[PlaceType, int] = {}
        for key, count in value.items():
            coerced[coerce_placetype(key)] = count
        return coerced

    @field_serializer("descendants_count")
    def _serialize_descendants_count(
        self, value: Dict[PlaceType, int]
    ) -> Dict[str, int]:
        return {ptype.value: count for ptype, count in value.items()}

    def get_ancestor_by_type(self, placetype: PlacetypeLike) -> Optional[WOFAncestor]:
        """Get ancestor of specific type."""
        target = normalize_placetype(placetype)
        for ancestor in self.ancestors:
            if ancestor.placetype.value == target:
                return ancestor
        return None

    def get_depth(self) -> int:
        """Get depth in hierarchy."""
        return len(self.ancestors)

    def is_leaf(self) -> bool:
        """Check if place has no descendants."""
        return sum(self.descendants_count.values()) == 0

    def is_root(self) -> bool:
        """Check if place has no ancestors."""
        return len(self.ancestors) == 0

    def has_children(self) -> bool:
        """Check if place has direct children."""
        return len(self.children) > 0

    def has_siblings(self) -> bool:
        """Check if place has siblings."""
        return len(self.siblings) > 0

    def get_immediate_parent(self) -> Optional[WOFAncestor]:
        """Get immediate parent (level 0 ancestor)."""
        for ancestor in self.ancestors:
            if ancestor.level == 0:
                return ancestor
        return self.parent

    def get_ancestors_by_level(self, level: int) -> List[WOFAncestor]:
        """Get all ancestors at specific level."""
        return [a for a in self.ancestors if a.level == level]

    def to_path(self, separator: str = " > ") -> str:
        """Convert hierarchy to path string."""
        # Sort ancestors by level
        sorted_ancestors = sorted(self.ancestors, key=lambda a: a.level)
        path_parts = [a.name for a in sorted_ancestors]
        return separator.join(path_parts) if path_parts else ""


class HierarchyPath(BaseModel):
    """Represents a path through the hierarchy."""

    path: List[WOFPlaceRef]

    def to_string(self, separator: str = " > ") -> str:
        """Convert path to string representation."""
        return separator.join(p.name for p in self.path)

    def get_types(self) -> List[str]:
        """Get placetypes in path."""
        return [p.placetype.value for p in self.path]

    def contains_type(self, placetype: PlacetypeLike) -> bool:
        """Check if path contains placetype."""
        return normalize_placetype(placetype) in self.get_types()

    def get_by_type(self, placetype: PlacetypeLike) -> Optional[WOFPlaceRef]:
        """Get place in path by type."""
        target = normalize_placetype(placetype)
        for place in self.path:
            if place.placetype.value == target:
                return place
        return None

    def get_depth(self) -> int:
        """Get depth of path."""
        return len(self.path)

    def is_valid(self) -> bool:
        """Check if path is valid (has places)."""
        return len(self.path) > 0

    def reverse(self) -> "HierarchyPath":
        """Return reversed path (leaf to root)."""
        return HierarchyPath(path=list(reversed(self.path)))

    def truncate(self, depth: int) -> "HierarchyPath":
        """Truncate path to specified depth."""
        return HierarchyPath(path=self.path[:depth])

    def extend(self, place: WOFPlaceRef) -> "HierarchyPath":
        """Extend path with new place."""
        new_path = self.path.copy()
        new_path.append(place)
        return HierarchyPath(path=new_path)


class AncestorChain(BaseModel):
    """Chain of ancestors from immediate parent to root."""

    ancestors: List[WOFAncestor]

    def get_immediate_parent(self) -> Optional[WOFAncestor]:
        """Get immediate parent."""
        return self.ancestors[0] if self.ancestors else None

    def get_root(self) -> Optional[WOFAncestor]:
        """Get root ancestor."""
        return self.ancestors[-1] if self.ancestors else None

    def get_at_level(self, level: int) -> Optional[WOFAncestor]:
        """Get ancestor at specific level."""
        for ancestor in self.ancestors:
            if ancestor.level == level:
                return ancestor
        return None

    def get_countries(self) -> List[WOFAncestor]:
        """Get all country-level ancestors."""
        return [a for a in self.ancestors if a.is_country()]

    def get_regions(self) -> List[WOFAncestor]:
        """Get all region-level ancestors."""
        return [a for a in self.ancestors if a.is_region()]

    def to_dict(self) -> Dict[str, WOFAncestor]:
        """Convert to dictionary keyed by placetype."""
        return {a.placetype.value: a for a in self.ancestors}

    def filter_by_type(self, placetype: PlacetypeLike) -> List[WOFAncestor]:
        """Filter ancestors by placetype."""
        target = normalize_placetype(placetype)
        return [a for a in self.ancestors if a.placetype.value == target]


class HierarchyRelationship(BaseModel):
    """Represents a relationship between two places in hierarchy."""

    from_place: WOFPlaceRef
    to_place: WOFPlaceRef
    relationship_type: str  # parent, child, ancestor, descendant, sibling
    distance: int = Field(1, description="Number of levels apart")

    def is_direct(self) -> bool:
        """Check if relationship is direct (distance = 1)."""
        return self.distance == 1

    def is_parent_child(self) -> bool:
        """Check if this is a parent-child relationship."""
        return self.relationship_type in ["parent", "child"] and self.distance == 1

    def is_sibling(self) -> bool:
        """Check if this is a sibling relationship."""
        return self.relationship_type == "sibling"

    def reverse(self) -> "HierarchyRelationship":
        """Reverse the relationship direction."""
        reverse_types = {
            "parent": "child",
            "child": "parent",
            "ancestor": "descendant",
            "descendant": "ancestor",
            "sibling": "sibling",
        }
        return HierarchyRelationship(
            from_place=self.to_place,
            to_place=self.from_place,
            relationship_type=reverse_types.get(
                self.relationship_type, self.relationship_type
            ),
            distance=self.distance,
        )


# Export all public items
__all__ = [
    "WOFPlaceRef",
    "WOFAncestor",
    "WOFHierarchy",
    "HierarchyPath",
    "AncestorChain",
    "HierarchyRelationship",
]
