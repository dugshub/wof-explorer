"""
Internal data models for SQLite backend.

These models are used internally for data passing between components
and are NOT part of the public API. They provide flexibility for
internal operations while maintaining strict contracts at boundaries.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from sqlalchemy.engine import Row
from wof_explorer.models.places import WOFPlace

if TYPE_CHECKING:
    from wof_explorer.models.results import WOFSearchResult


@dataclass
class DBSearchResult:
    """
    Raw search results directly from database.

    This is what we READ from the database before any transformation.
    Used internally by operations layer only.
    """

    rows: List[Row]  # Raw SQLAlchemy rows
    total_count: int
    query_executed: Optional[str] = None  # For debugging
    execution_time_ms: Optional[float] = None
    source_db: Optional[str] = None  # Which database it came from

    def is_empty(self) -> bool:
        """Check if result is empty."""
        return self.total_count == 0 or len(self.rows) == 0


@dataclass
class InternalSearchResult:
    """
    Internal representation after transformation.

    This is the intermediate representation used by operations
    and cursor. It contains transformed domain models but is
    not exposed to the public API.
    """

    places: List[WOFPlace]  # Transformed to domain models
    total_count: int
    returned_count: int
    query_filters: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None  # Flexible internal metadata

    @property
    def has_results(self) -> bool:
        """Check if there are any results."""
        return self.returned_count > 0

    @property
    def is_complete(self) -> bool:
        """Check if all results were returned."""
        return self.returned_count == self.total_count

    def to_public_result(
        self,
        offset: int = 0,
        limit: Optional[int] = None,
        query_time_ms: Optional[float] = None,
    ) -> "WOFSearchResult":
        """
        Convert to public API model.

        This enforces the contract for what we PASS to the domain layer.
        """
        from wof_explorer.models.results import WOFSearchResult

        has_more = False
        if limit and self.returned_count > limit:
            has_more = True
        elif offset + self.returned_count < self.total_count:
            has_more = True

        return WOFSearchResult(
            total_count=self.total_count,
            returned_count=self.returned_count,
            offset=offset,
            limit=limit,
            has_more=has_more,
            query_time_ms=query_time_ms,
            filters_applied=self.query_filters,
        )


@dataclass
class DBBatchResult:
    """
    Raw batch query results from database.

    Used for batch operations like get_places().
    """

    rows: List[Row]
    requested_ids: List[int]
    found_ids: List[int]
    missing_ids: List[int]
    source_db: Optional[str] = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if not self.requested_ids:
            return 0.0
        return len(self.found_ids) / len(self.requested_ids)


@dataclass
class InternalBatchResult:
    """
    Internal representation of batch results.

    After transformation to domain models.
    """

    places: List[WOFPlace]
    requested_ids: List[int]
    found_ids: List[int]
    missing_ids: List[int]
    metadata: Optional[Dict[str, Any]] = None

    def is_complete(self) -> bool:
        """Check if all requested places were found."""
        return len(self.missing_ids) == 0


@dataclass
class DBHierarchyResult:
    """
    Raw hierarchy query results.

    For ancestor/descendant queries.
    """

    ancestor_rows: List[Row]  # From ancestors table
    place_rows: List[Row]  # From spr table
    root_place_id: int
    direction: str  # 'ancestors', 'descendants', 'children'


@dataclass
class InternalHierarchyResult:
    """
    Internal hierarchy representation.

    After transformation and ordering.
    """

    places: List[WOFPlace]  # Ordered list
    root_place_id: int
    direction: str
    levels: Optional[Dict[int, str]] = None  # Place ID to hierarchy level mapping

    @property
    def depth(self) -> int:
        """Get hierarchy depth."""
        return len(self.places)
