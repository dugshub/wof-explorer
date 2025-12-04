"""
Core place models for WOF Explorer.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List, TYPE_CHECKING
from datetime import datetime
from pydantic import BaseModel, field_serializer, field_validator, ConfigDict
from wof_explorer.types import PlaceID, ParentID, PlaceType, coerce_placetype
from wof_explorer.models.hierarchy import WOFAncestor, WOFHierarchy
from wof_explorer.models.results import WOFSearchResult
from wof_explorer.models.geometry import BBox

if TYPE_CHECKING:
    from .geometry import WOFBounds, WOFCentroid, WOFGeometry
    from .hierarchy import WOFPlaceRef


class WOFPlace(BaseModel):
    """Core WhosOnFirst place model."""

    # Identity
    id: PlaceID
    name: str
    placetype: PlaceType

    # Hierarchy
    parent_id: ParentID = None

    # Status
    is_current: bool = True
    deprecated: Optional[datetime] = None
    cessation: Optional[datetime] = None
    superseded_by: Optional[List[PlaceID]] = None
    supersedes: Optional[List[PlaceID]] = None

    @property
    def is_active(self) -> bool:
        """Alias for is_current for backward compatibility."""
        return self.is_current

    # Location hierarchy fields
    country: Optional[str] = None
    region: Optional[str] = None
    county: Optional[str] = None
    locality: Optional[str] = None
    neighbourhood: Optional[str] = None

    # Spatial (basic) - stored as lists for compatibility
    bbox: Optional[List[float]] = None  # [min_lon, min_lat, max_lon, max_lat]
    centroid: Optional[List[float]] = None  # [lon, lat]

    # Metadata
    population: Optional[int] = None
    area_m2: Optional[float] = None
    source: Optional[str] = None
    lastmodified: Optional[datetime] = None
    repo: Optional[str] = None

    model_config = ConfigDict(
        frozen=False,
        extra="allow",  # Allow extra fields from database
    )

    @field_validator("placetype", mode="before")
    @classmethod
    def _coerce_placetype(cls, value):
        """Allow string placetype inputs for backward compatibility."""
        if value is None:
            return PlaceType.CUSTOM
        return coerce_placetype(value)

    @field_validator("superseded_by", "supersedes", mode="before")
    @classmethod
    def _coerce_to_list(cls, value):
        """Convert single values to lists for superseded_by and supersedes fields."""
        if value is None:
            return None
        if isinstance(value, (int, str)):
            return [int(value)]
        if isinstance(value, list):
            return [int(v) for v in value]
        return value

    @field_serializer("placetype")
    def _serialize_placetype(self, value: PlaceType) -> str:
        return value.value

    def get_status(self) -> str:
        """Get place status."""
        if self.cessation:
            return "ceased"
        elif self.deprecated:
            return "deprecated"
        elif self.superseded_by:
            return "superseded"
        elif self.supersedes:
            return "superseding"
        else:
            return "current"

    def get_bounds(self) -> Optional[WOFBounds]:
        """Get bounds object."""
        if self.bbox and len(self.bbox) == 4:
            from .geometry import WOFBounds

            return WOFBounds(
                min_lon=self.bbox[0],
                min_lat=self.bbox[1],
                max_lon=self.bbox[2],
                max_lat=self.bbox[3],
            )
        return None

    def get_centroid(self) -> Optional[WOFCentroid]:
        """Get centroid object."""
        if self.centroid and len(self.centroid) == 2:
            from .geometry import WOFCentroid

            return WOFCentroid(
                lon=self.centroid[0], lat=self.centroid[1], source="computed"
            )
        return None

    def get_hierarchy_fields(self) -> Dict[str, Optional[str]]:
        """Get hierarchy location fields."""
        return {
            "country": self.country,
            "region": self.region,
            "county": self.county,
            "locality": self.locality,
            "neighbourhood": self.neighbourhood,
        }

    def is_administrative(self) -> bool:
        """Check if place is administrative level."""
        from wof_explorer.types import PlaceType

        return PlaceType.is_admin_level(self.placetype)

    def to_reference(self) -> WOFPlaceRef:
        """Convert to lightweight reference."""
        from .hierarchy import WOFPlaceRef

        return WOFPlaceRef(id=self.id, name=self.name, placetype=self.placetype)

    @property
    def latitude(self) -> Optional[float]:
        """Get latitude from centroid."""
        if self.centroid and len(self.centroid) >= 2:
            return self.centroid[1]
        return None

    @property
    def longitude(self) -> Optional[float]:
        """Get longitude from centroid."""
        if self.centroid and len(self.centroid) >= 2:
            return self.centroid[0]
        return None

    @property
    def is_deprecated(self) -> bool:
        """Check if place is deprecated."""
        return bool(self.deprecated)

    @property
    def is_ceased(self) -> bool:
        """Check if place is ceased."""
        return bool(self.cessation)

    @property
    def is_superseded(self) -> bool:
        """Check if place is superseded."""
        return bool(self.superseded_by)

    @property
    def is_superseding(self) -> bool:
        """Check if place is superseding others."""
        return bool(self.supersedes)

    @property
    def is_current_status(self) -> bool:
        """Check if place is current (not deprecated, ceased, or superseded)."""
        return not (self.is_deprecated or self.is_ceased or self.is_superseded)


class WOFPlaceWithGeometry(WOFPlace):
    """Place model with full geometry data."""

    geometry: Optional[Dict[str, Any]] = None

    def get_geometry(self) -> Optional[WOFGeometry]:
        """Get geometry object."""
        if self.geometry:
            from .geometry import WOFGeometry

            # Handle nested Feature geometry
            geom = self.geometry
            if geom.get("type") == "Feature":
                geom = geom.get("geometry", {})

            if geom and "type" in geom and "coordinates" in geom:
                geom_type = geom.get("type")
                geom_coords = geom.get("coordinates")
                if geom_type and geom_coords is not None:
                    return WOFGeometry(type=geom_type, coordinates=geom_coords)
        return None

    def has_geometry(self) -> bool:
        """Check if place has geometry."""
        return self.geometry is not None

    def get_geometry_type(self) -> Optional[str]:
        """Get geometry type."""
        if self.geometry:
            geom = self.geometry
            if geom.get("type") == "Feature":
                geom = geom.get("geometry", {})
            return geom.get("type")
        return None


# Note: WOFAncestor moved to hierarchy.py


class WOFName(BaseModel):
    """Alternative name for a place."""

    place_id: PlaceID
    language: str
    name: str
    preferred: bool = False
    colloquial: bool = False
    historic: bool = False

    model_config = ConfigDict(frozen=True)

    def is_english(self) -> bool:
        """Check if name is English."""
        return self.language.startswith("eng")

    def is_preferred(self) -> bool:
        """Check if name is preferred."""
        return self.preferred or "_x_preferred" in self.language

    def is_colloquial(self) -> bool:
        """Check if name is colloquial."""
        return self.colloquial or "_x_colloquial" in self.language


# Note: WOFHierarchy moved to hierarchy.py


# Note: WOFSearchResult moved to results.py

# For backward compatibility, re-export from new locations

# Export all public items
__all__ = [
    "WOFPlace",
    "WOFPlaceWithGeometry",
    "WOFName",
    # Re-exported for compatibility
    "WOFAncestor",
    "WOFHierarchy",
    "WOFSearchResult",
    "BBox",
]
