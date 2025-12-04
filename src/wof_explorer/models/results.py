"""
Result container models for WOF queries.
"""

from typing import List, Optional, Dict, Any, Generic, TypeVar, Tuple
from pydantic import BaseModel, Field, ConfigDict
from wof_explorer.types import PlaceID, CursorState

T = TypeVar("T")


class WOFSearchResult(BaseModel):
    """
    Container for search results with metadata.

    This is the PUBLIC API model that represents search results
    in the domain layer. It is strictly typed with no extra fields.
    """

    total_count: int
    returned_count: int
    offset: int = 0
    limit: Optional[int] = None
    has_more: bool = False
    query_time_ms: Optional[float] = None
    filters_applied: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")  # Strict - no extra fields allowed

    def get_page_info(self) -> Dict[str, Any]:
        """Get pagination information."""
        per_page = self.limit or 100
        current_page = (self.offset // per_page) + 1 if per_page else 1
        total_pages = (
            (self.total_count // per_page) + 1
            if per_page and self.total_count > 0
            else 1
        )

        return {
            "page": current_page,
            "per_page": per_page,
            "total_pages": total_pages,
            "has_next": self.has_more,
            "has_prev": self.offset > 0,
            "total_count": self.total_count,
            "returned_count": self.returned_count,
        }

    def is_empty(self) -> bool:
        """Check if result is empty."""
        return self.total_count == 0

    def is_partial(self) -> bool:
        """Check if this is a partial result."""
        return self.has_more or bool(
            self.limit and self.returned_count < self.total_count
        )


class BatchResult(BaseModel, Generic[T]):
    """Result container for batch operations."""

    items: List[T]
    succeeded: List[PlaceID]
    failed: List[PlaceID]
    errors: Dict[PlaceID, str] = Field(default_factory=dict)
    total_requested: int = 0

    def success_rate(self) -> float:
        """Calculate success rate."""
        total = len(self.succeeded) + len(self.failed)
        return len(self.succeeded) / total if total > 0 else 0.0

    def get_failed_items(self) -> List[Tuple[PlaceID, str]]:
        """Get failed items with error messages."""
        return [(id, self.errors.get(id, "Unknown error")) for id in self.failed]

    def is_complete(self) -> bool:
        """Check if all requested items succeeded."""
        return len(self.failed) == 0

    def is_partial(self) -> bool:
        """Check if some items failed."""
        return len(self.failed) > 0 and len(self.succeeded) > 0

    def is_failure(self) -> bool:
        """Check if all items failed."""
        return len(self.succeeded) == 0 and len(self.failed) > 0


class CursorResult(BaseModel, Generic[T]):
    """Result from cursor-based fetching."""

    items: List[T]
    cursor_state: CursorState
    cursor_position: Optional[str] = None
    has_next: bool = False
    fetch_count: int = 0
    total_fetched: int = 0
    error_message: Optional[str] = None

    def is_exhausted(self) -> bool:
        """Check if cursor is exhausted."""
        return self.cursor_state == "exhausted" or not self.has_next

    def is_error(self) -> bool:
        """Check if cursor encountered error."""
        return self.cursor_state == "error"

    def is_ready(self) -> bool:
        """Check if cursor is ready for fetching."""
        return self.cursor_state == "ready"

    def is_fetching(self) -> bool:
        """Check if cursor is currently fetching."""
        return self.cursor_state == "fetching"

    def has_items(self) -> bool:
        """Check if cursor has items."""
        return len(self.items) > 0


class AggregateResult(BaseModel):
    """Result from aggregation queries."""

    aggregations: Dict[str, Any]
    group_by: Optional[List[str]] = None
    metrics: Dict[str, float] = Field(default_factory=dict)
    total_count: int = 0

    def get_top_n(self, field: str, n: int = 10) -> List[Tuple[Any, int]]:
        """Get top N values for field."""
        if field not in self.aggregations:
            return []

        data = self.aggregations[field]
        if isinstance(data, dict):
            sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)
            return sorted_items[:n]
        return []

    def get_bottom_n(self, field: str, n: int = 10) -> List[Tuple[Any, int]]:
        """Get bottom N values for field."""
        if field not in self.aggregations:
            return []

        data = self.aggregations[field]
        if isinstance(data, dict):
            sorted_items = sorted(data.items(), key=lambda x: x[1])
            return sorted_items[:n]
        return []

    def get_metric(self, metric_name: str) -> Optional[float]:
        """Get specific metric value."""
        return self.metrics.get(metric_name)

    def get_group_count(self, field: str) -> int:
        """Get number of unique groups for field."""
        if field in self.aggregations and isinstance(self.aggregations[field], dict):
            return len(self.aggregations[field])
        return 0


class SpatialResult(BaseModel):
    """Result from spatial queries."""

    places: List[Any]  # Will be WOFPlace
    bbox: Optional[List[float]] = None
    centroid: Optional[List[float]] = None
    total_area_m2: Optional[float] = None
    density: Optional[Dict[str, Any]] = None
    spatial_index: Optional[Dict[str, Any]] = None

    def get_bounds(self) -> Optional[List[float]]:
        """Get bounding box of results."""
        return self.bbox

    def get_center(self) -> Optional[List[float]]:
        """Get center point of results."""
        return self.centroid

    def get_area_km2(self) -> Optional[float]:
        """Get total area in square kilometers."""
        return self.total_area_m2 / 1_000_000 if self.total_area_m2 else None

    def has_spatial_data(self) -> bool:
        """Check if result has spatial data."""
        return self.bbox is not None or self.centroid is not None

    def get_density_info(self) -> Dict[str, Any]:
        """Get density information."""
        return self.density or {}


class ValidationResult(BaseModel):
    """Result from data validation."""

    valid: bool = True
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    field_errors: Dict[str, List[str]] = Field(default_factory=dict)
    validated_count: int = 0
    failed_count: int = 0

    def add_error(self, message: str, field: Optional[str] = None):
        """Add validation error."""
        self.valid = False
        self.errors.append(message)
        self.failed_count += 1
        if field:
            if field not in self.field_errors:
                self.field_errors[field] = []
            self.field_errors[field].append(message)

    def add_warning(self, message: str):
        """Add validation warning."""
        self.warnings.append(message)

    def merge(self, other: "ValidationResult"):
        """Merge another validation result."""
        self.valid = self.valid and other.valid
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.validated_count += other.validated_count
        self.failed_count += other.failed_count
        for field, errors in other.field_errors.items():
            if field not in self.field_errors:
                self.field_errors[field] = []
            self.field_errors[field].extend(errors)

    def has_errors(self) -> bool:
        """Check if validation has errors."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if validation has warnings."""
        return len(self.warnings) > 0

    def get_error_summary(self) -> str:
        """Get summary of errors."""
        if not self.has_errors():
            return "No errors"
        return f"{len(self.errors)} errors in {len(self.field_errors)} fields"

    def success_rate(self) -> float:
        """Calculate validation success rate."""
        total = self.validated_count
        return (total - self.failed_count) / total if total > 0 else 0.0


class ExportResult(BaseModel):
    """Result from export operations."""

    format: str
    size_bytes: int
    record_count: int
    file_path: Optional[str] = None
    content: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    export_time_ms: Optional[float] = None

    def get_size_mb(self) -> float:
        """Get size in megabytes."""
        return self.size_bytes / (1024 * 1024)

    def get_size_kb(self) -> float:
        """Get size in kilobytes."""
        return self.size_bytes / 1024

    def is_file_export(self) -> bool:
        """Check if exported to file."""
        return self.file_path is not None

    def is_content_export(self) -> bool:
        """Check if exported to string."""
        return self.content is not None

    def get_format_info(self) -> Dict[str, Any]:
        """Get format-specific information."""
        return {
            "format": self.format,
            "size_mb": self.get_size_mb(),
            "records": self.record_count,
            "type": "file" if self.is_file_export() else "content",
            **self.metadata,
        }


class ComparisonResult(BaseModel):
    """Result from comparing two datasets."""

    added: List[PlaceID] = Field(default_factory=list)
    removed: List[PlaceID] = Field(default_factory=list)
    modified: List[PlaceID] = Field(default_factory=list)
    unchanged: List[PlaceID] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_summary(self) -> Dict[str, int]:
        """Get summary of changes."""
        return {
            "added": len(self.added),
            "removed": len(self.removed),
            "modified": len(self.modified),
            "unchanged": len(self.unchanged),
            "total_changes": len(self.added) + len(self.removed) + len(self.modified),
        }

    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return len(self.added) > 0 or len(self.removed) > 0 or len(self.modified) > 0

    def change_rate(self) -> float:
        """Calculate rate of change."""
        total = (
            len(self.added)
            + len(self.removed)
            + len(self.modified)
            + len(self.unchanged)
        )
        changed = len(self.added) + len(self.removed) + len(self.modified)
        return changed / total if total > 0 else 0.0


class AnalysisResult(BaseModel):
    """Result from data analysis operations."""

    analysis_type: str
    results: Dict[str, Any]
    statistics: Dict[str, float] = Field(default_factory=dict)
    visualizations: Dict[str, Any] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)
    confidence: float = Field(1.0, ge=0.0, le=1.0)

    def get_key_findings(self) -> List[str]:
        """Get key findings from analysis."""
        findings = []
        if "key_findings" in self.results:
            findings = self.results["key_findings"]
        elif "summary" in self.results:
            findings = [self.results["summary"]]
        return findings

    def has_visualizations(self) -> bool:
        """Check if analysis has visualizations."""
        return len(self.visualizations) > 0

    def get_statistic(self, stat_name: str) -> Optional[float]:
        """Get specific statistic."""
        return self.statistics.get(stat_name)

    def is_high_confidence(self) -> bool:
        """Check if analysis has high confidence."""
        return self.confidence >= 0.8


# Export all public items
__all__ = [
    "WOFSearchResult",
    "BatchResult",
    "CursorResult",
    "AggregateResult",
    "SpatialResult",
    "ValidationResult",
    "ExportResult",
    "ComparisonResult",
    "AnalysisResult",
]
