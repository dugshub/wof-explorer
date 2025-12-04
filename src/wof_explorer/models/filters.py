"""
Filter specifications for WhosOnFirst queries.
These provide clean interfaces for building complex queries.
"""

from typing import Optional, Literal, Union, List
from pydantic import BaseModel, Field, field_serializer, field_validator
from wof_explorer.models.places import BBox
from wof_explorer.types import PlaceType, coerce_placetype


class WOFSearchFilters(BaseModel):
    """
    Tier-1 search filters for finding places.
    These are the primary entry points for discovery.
    """

    # Name search
    name: Optional[str] = Field(default=None, description="Search in place names")
    name_exact: bool = Field(default=False, description="Exact match vs contains")
    name_language: str = Field(default="eng", description="Language for name search")
    name_type: Literal["preferred", "colloquial", "variant", "any"] = Field(
        default="preferred", description="Type of name to search"
    )

    # Type and hierarchy
    placetype: Optional[Union[PlaceType, List[PlaceType]]] = Field(
        default=None, description="Filter by placetype(s)"
    )
    parent_name: Optional[Union[str, List[str]]] = Field(
        default=None, description="Filter by immediate parent's name(s)"
    )
    parent_id: Optional[Union[int, List[int]]] = Field(
        default=None, description="Filter by immediate parent ID(s)"
    )
    ancestor_name: Optional[Union[str, List[str]]] = Field(
        default=None, description="Filter by ancestor's name(s) (any level)"
    )
    ancestor_id: Optional[Union[int, List[int]]] = Field(
        default=None, description="Filter by ancestor ID(s) (any level)"
    )

    # Geographic filters
    bbox: Optional[BBox] = Field(default=None, description="Bounding box filter")
    near_lat: Optional[float] = Field(
        default=None, description="Latitude for proximity search"
    )
    near_lon: Optional[float] = Field(
        default=None, description="Longitude for proximity search"
    )
    radius_km: Optional[float] = Field(
        default=None, description="Radius in km for proximity search"
    )
    under_point: Optional[tuple[float, float]] = Field(
        default=None, description="(lat, lon) - find all places containing this point"
    )

    # Status filters
    is_current: Optional[bool] = Field(
        default=None, description="Filter by current status"
    )
    is_deprecated: Optional[bool] = Field(
        default=None, description="Include deprecated places"
    )
    is_ceased: Optional[bool] = Field(default=None, description="Include ceased places")
    is_superseded: Optional[bool] = Field(
        default=None, description="Include superseded places"
    )
    is_superseding: Optional[bool] = Field(
        default=None, description="Include superseding places"
    )

    # Metadata filters
    country: Optional[Union[str, List[str]]] = Field(
        default=None, description="Filter by country code(s)"
    )
    region: Optional[Union[str, List[str]]] = Field(
        default=None, description="Filter by region code(s)"
    )
    repo: Optional[Union[str, List[str]]] = Field(
        default=None, description="Filter by repo source(s)"
    )

    # Geometry filters
    geometry_type: Optional[Union[str, List[str]]] = Field(
        default=None,
        description="Filter by geometry type(s): 'Polygon', 'MultiPolygon', 'Point', etc. Use 'polygon' to get both Polygon and MultiPolygon",
    )
    exclude_point_geoms: bool = Field(
        default=False, description="Exclude places that only have Point geometries"
    )

    # Result control
    limit: Optional[int] = Field(
        default=None, ge=1, description="Maximum results to return (None for unlimited)"
    )
    offset: Optional[int] = Field(
        default=None, ge=0, description="Number of results to skip"
    )

    # Multi-database filtering
    source: Optional[Union[str, List[str]]] = Field(
        default=None,
        description="Filter by database source (e.g., 'usa', 'canada'). Only used in multi-database mode.",
    )

    @field_validator("placetype", mode="before")
    @classmethod
    def _coerce_placetype(cls, value):
        if value is None:
            return None
        if isinstance(value, (list, tuple, set)):
            return [coerce_placetype(v) for v in value]
        return coerce_placetype(value)

    @field_serializer("placetype")
    def _serialize_placetype(self, value):
        if value is None:
            return None
        if isinstance(value, list):
            return [ptype.value for ptype in value]
        return value.value

    def has_geographic_filter(self) -> bool:
        """Check if any geographic filters are set."""
        return any(
            [
                self.bbox is not None,
                self.near_lat is not None and self.near_lon is not None,
                self.parent_id is not None,
            ]
        )

    def has_status_filter(self) -> bool:
        """Check if any status filters are set."""
        return any(
            [
                self.is_current is not None,
                self.is_deprecated is not None,
                self.is_ceased is not None,
            ]
        )


class WOFFilters(BaseModel):
    """
    Filters for hierarchical queries (children, descendants, ancestors).
    These are applied after finding the root place.
    """

    placetype: Optional[PlaceType] = Field(
        default=None, description="Filter by placetype"
    )
    placetypes: Optional[list[PlaceType]] = Field(
        default=None, description="Filter by multiple placetypes"
    )

    # Status filters - can be different from search filters
    is_current: Optional[bool] = Field(
        default=None, description="Filter by current status"
    )
    is_deprecated: Optional[bool] = Field(
        default=None, description="Filter by deprecated status"
    )
    is_ceased: Optional[bool] = Field(
        default=None, description="Filter by ceased status"
    )
    is_superseded: Optional[bool] = Field(
        default=None, description="Filter by superseded status"
    )
    is_superseding: Optional[bool] = Field(
        default=None, description="Filter by superseding status"
    )

    # Hierarchy depth control
    max_depth: Optional[int] = Field(
        default=None, ge=1, description="Maximum depth for descendants"
    )

    # Result control
    limit: Optional[int] = Field(default=None, ge=1, description="Maximum results")

    @field_validator("placetype", mode="before")
    @classmethod
    def _coerce_primary(cls, value):
        if value is None:
            return None
        return coerce_placetype(value)

    @field_validator("placetypes", mode="before")
    @classmethod
    def _coerce_multiple(cls, value):
        if value is None:
            return None
        return [coerce_placetype(v) for v in value]

    @field_serializer("placetype")
    def _serialize_primary(self, value):
        return value.value if value is not None else None

    @field_serializer("placetypes")
    def _serialize_multiple(self, value):
        if value is None:
            return None
        return [ptype.value for ptype in value]

    def get_placetype_list(self) -> Optional[list[PlaceType]]:
        """Get list of placetypes to filter by."""
        if self.placetypes:
            return self.placetypes
        elif self.placetype:
            return [self.placetype]
        return None

    def should_include_place(
        self, is_current: int, is_deprecated: bool, is_ceased: bool
    ) -> bool:
        """
        Check if a place should be included based on status filters.

        Args:
            is_current: Place's is_current value (-1, 0, 1)
            is_deprecated: Place's is_deprecated flag
            is_ceased: Place's is_ceased flag

        Returns:
            Whether the place matches the filters
        """
        # If no filters set, include everything
        if (
            self.is_current is None
            and self.is_deprecated is None
            and self.is_ceased is None
        ):
            return True

        # Check each filter if set
        if self.is_current is not None:
            current_match = (is_current == 1) == self.is_current
            if not current_match:
                return False

        if self.is_deprecated is not None:
            deprecated_match = is_deprecated == self.is_deprecated
            if not deprecated_match:
                return False

        if self.is_ceased is not None:
            ceased_match = is_ceased == self.is_ceased
            if not ceased_match:
                return False

        return True


class WOFExpansion(BaseModel):
    """
    Configuration for hierarchical expansion operations.
    """

    expansion_type: Literal["children", "descendants", "ancestors"] = Field(
        ..., description="Type of hierarchy expansion"
    )
    filters: Optional[WOFFilters] = Field(
        None, description="Filters to apply to expanded results"
    )
    include_root: bool = Field(True, description="Include the root place in results")

    def get_description(self) -> str:
        """Get human-readable description of the expansion."""
        descriptions = {
            "children": "direct children",
            "descendants": "all descendants",
            "ancestors": "all ancestors",
        }
        desc = descriptions[self.expansion_type]

        if self.filters:
            if self.filters.placetype:
                desc += f" of type '{self.filters.placetype}'"
            if self.filters.is_current is not None:
                desc += f" (current={'yes' if self.filters.is_current else 'no'})"

        return desc


class WOFBatchFilter(BaseModel):
    """
    Filter for batch operations on multiple place IDs.
    """

    place_ids: list[int] = Field(..., min_length=1, max_length=1000)
    include_geometry: bool = Field(False, description="Include GeoJSON geometry")
    include_names: bool = Field(False, description="Include alternative names")
    include_ancestors: bool = Field(False, description="Include ancestor data")


__all__ = [
    "WOFSearchFilters",
    "WOFFilters",
    "WOFExpansion",
    "WOFBatchFilter",
]
