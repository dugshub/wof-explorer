"""
WOF data models shared across all backends.

These models define the data structures used throughout the WOF connector,
independent of the backend implementation.
"""

# Core place models
from wof_explorer.models.places import (
    WOFPlace,
    WOFPlaceWithGeometry,
    WOFName,
    # Re-exported for compatibility
    BBox,
    WOFAncestor,
    WOFHierarchy,
    WOFSearchResult,
)

# Hierarchy models (new)
from wof_explorer.models.hierarchy import (
    WOFPlaceRef,
    HierarchyPath,
    AncestorChain,
    HierarchyRelationship,
)

# Geometry models (new)
from wof_explorer.models.geometry import (
    WOFGeometry,
    WOFBounds,
    WOFCentroid,
    GeometryCollection,
    SpatialReference,
)

# Result containers (new)
from wof_explorer.models.results import (
    BatchResult,
    CursorResult,
    AggregateResult,
    SpatialResult,
    ValidationResult,
    ExportResult,
    ComparisonResult,
    AnalysisResult,
)

# Filter models
from wof_explorer.models.filters import (
    WOFSearchFilters,
    WOFFilters,
    WOFExpansion,
    WOFBatchFilter,
)

__all__ = [
    # Place models
    "WOFPlace",
    "WOFPlaceWithGeometry",
    "WOFName",
    # Hierarchy models
    "WOFPlaceRef",
    "WOFAncestor",
    "WOFHierarchy",
    "HierarchyPath",
    "AncestorChain",
    "HierarchyRelationship",
    # Geometry models
    "BBox",  # Kept for compatibility
    "WOFGeometry",
    "WOFBounds",
    "WOFCentroid",
    "GeometryCollection",
    "SpatialReference",
    # Result containers
    "WOFSearchResult",
    "BatchResult",
    "CursorResult",
    "AggregateResult",
    "SpatialResult",
    "ValidationResult",
    "ExportResult",
    "ComparisonResult",
    "AnalysisResult",
    # Filter models
    "WOFSearchFilters",
    "WOFFilters",
    "WOFExpansion",
    "WOFBatchFilter",
]
