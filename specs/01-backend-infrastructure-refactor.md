# Backend Infrastructure Refactor Specification

## Work Stream 1: SQLite Backend Modularization

### Current State Analysis

The SQLite backend is currently monolithic with 1,015 lines in `connector.py` containing:
- Database connection and session management
- SQL query construction
- Data operations (CRUD)
- Result transformation
- Multi-database federation logic
- View creation and management

### Target Architecture

```
backends/sqlite/
├── __init__.py           # Public exports
├── connector.py          # Thin orchestration layer (150 lines)
├── session.py            # Session and connection management (200 lines)
├── queries.py            # SQL query builders (300 lines)
├── operations.py         # Database operations (250 lines)
├── tables.py             # [EXISTING] Table definitions
└── federation.py         # Multi-database federation (100 lines)
```

### Detailed Migration Plan

#### Phase 1: Extract Session Management
**File**: `backends/sqlite/session.py`

```python
"""
SQLite session and connection management.
Handles engine lifecycle, connection pooling, and multi-database attachment.
"""

from typing import Optional, List, Dict, Any
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.engine import Engine

class SQLiteSessionManager:
    """Manages SQLite database sessions and connections."""

    def __init__(self, db_paths: List[Path]):
        self.db_paths = db_paths
        self.primary_db = db_paths[0] if db_paths else None
        self._sync_engine: Optional[Engine] = None
        self._async_engine: Optional[AsyncEngine] = None
        self._attached_databases: Dict[str, str] = {}

    async def connect(self) -> AsyncEngine:
        """Create and configure async engine with attached databases."""
        # Move lines 101-123 from connector.py

    def connect_sync(self) -> Engine:
        """Create synchronous engine for non-async operations."""
        # New method for sync operations

    async def attach_databases(self, engine: AsyncEngine) -> None:
        """Attach additional databases for federation."""
        # Move lines 124-133 from connector.py

    async def create_unified_views(self, engine: AsyncEngine) -> None:
        """Create unified views across attached databases."""
        # Move lines 134-155 from connector.py

    async def disconnect(self) -> None:
        """Clean up connections and detach databases."""
        # Move lines 251-258 from connector.py

    def get_database_aliases(self) -> Dict[str, str]:
        """Return mapping of database paths to aliases."""
        return self._attached_databases
```

**Migration from `connector.py`**:
- Move lines 89-92 (engine attributes) → SessionManager.__init__
- Move lines 101-123 (connect logic) → SessionManager.connect
- Move lines 124-133 (_attach_databases) → SessionManager.attach_databases
- Move lines 134-155 (_create_unified_views) → SessionManager.create_unified_views
- Move lines 251-258 (disconnect) → SessionManager.disconnect

#### Phase 2: Extract Query Builders
**File**: `backends/sqlite/queries.py`

```python
"""
SQL query builders for WOF SQLite backend.
Constructs SQLAlchemy queries for various search patterns.
"""

from typing import Optional, List, Dict, Any
from sqlalchemy import select, and_, or_, text
from wof_explorer.models.filters import WOFSearchFilters, WOFFilters

class SQLiteQueryBuilder:
    """Builds SQL queries for WOF data access."""

    def __init__(self, tables: Dict[str, Any]):
        self.tables = tables

    def build_search_query(self, filters: WOFSearchFilters):
        """Build search query with filters."""
        # Move lines 287-575 from connector.py

    def build_hierarchy_query(self, place_id: int, direction: str):
        """Build ancestor/descendant queries."""
        # Move lines 638-764 from connector.py

    def build_batch_query(self, ids: List[int], include_geometry: bool):
        """Build batch retrieval query."""
        # Move lines 808-875 from connector.py

    def apply_filters(self, query, table, filters: WOFFilters):
        """Apply WOF filters to a query."""
        # Move lines 919-955 from connector.py

    def build_spatial_query(self, bbox=None, proximity=None):
        """Build spatial queries (bbox, proximity)."""
        # Extract spatial logic from search query

    def build_text_search_query(self, text: str, fields: List[str]):
        """Build full-text search queries."""
        # New capability for text search
```

**Migration from `connector.py`**:
- Move search query construction (lines 287-575) → build_search_query
- Move hierarchy queries (lines 638-764) → build_hierarchy_query
- Move batch queries (lines 808-875) → build_batch_query
- Move filter application (lines 919-955) → apply_filters

#### Phase 3: Extract Database Operations
**File**: `backends/sqlite/operations.py`

```python
"""
Database operations for WOF SQLite backend.
Executes queries and transforms results.
"""

from typing import Optional, List, Dict, Any
from wof_explorer.models.places import WOFPlace, WOFPlaceWithGeometry
from .queries import SQLiteQueryBuilder
from .session import SQLiteSessionManager

class SQLiteOperations:
    """Executes database operations and transforms results."""

    def __init__(self, session_manager: SQLiteSessionManager,
                 query_builder: SQLiteQueryBuilder):
        self.session = session_manager
        self.queries = query_builder

    async def execute_search(self, filters) -> List[WOFPlace]:
        """Execute search query and return places."""
        # Refactored from connector.search

    async def execute_get_place(self, place_id: int) -> Optional[WOFPlace]:
        """Get single place by ID."""
        # Move lines 576-637 from connector.py

    async def execute_hierarchy_query(self, place_id: int,
                                     direction: str) -> List[WOFPlace]:
        """Execute ancestor/descendant queries."""
        # Refactored from get_ancestors/get_descendants

    async def execute_batch_retrieval(self, ids: List[int]) -> List[WOFPlace]:
        """Retrieve multiple places by IDs."""
        # Refactored from get_places_by_ids

    def transform_row_to_place(self, row) -> WOFPlace:
        """Transform database row to WOFPlace."""
        # Move lines 956-996 from connector.py

    def transform_row_to_geometry(self, row) -> WOFPlaceWithGeometry:
        """Transform row with geometry data."""
        # Extract geometry handling
```

**Migration from `connector.py`**:
- Move get_place logic (lines 576-637) → execute_get_place
- Move row transformation (lines 956-996) → transform_row_to_place
- Refactor search execution from search method
- Refactor hierarchy execution from get_ancestors/descendants

#### Phase 4: Extract Federation Logic
**File**: `backends/sqlite/federation.py`

```python
"""
Multi-database federation for WOF SQLite backend.
Manages database discovery, attachment, and unified views.
"""

from typing import List, Dict, Any
from pathlib import Path
from wof_explorer.config import WOFConfig

class SQLiteFederation:
    """Manages multi-database federation."""

    def __init__(self, config: WOFConfig):
        self.config = config

    def discover_databases(self) -> List[Path]:
        """Auto-discover WOF databases."""
        # Move from config.py

    def create_attach_statements(self, databases: List[Path]) -> List[str]:
        """Generate ATTACH statements for databases."""
        # Extract from session.py

    def create_unified_view_ddl(self, table_name: str,
                               databases: Dict[str, str]) -> str:
        """Generate DDL for unified views."""
        # Extract from session.py

    def validate_schema_compatibility(self, databases: List[Path]) -> bool:
        """Ensure all databases have compatible schemas."""
        # New validation logic
```

#### Phase 5: Refactor Connector as Orchestrator
**File**: `backends/sqlite/connector.py` (refactored)

```python
"""
SQLite backend connector for WhosOnFirst.
Orchestrates session, queries, and operations.
"""

from wof_explorer.base import WOFConnectorBase
from .session import SQLiteSessionManager
from .queries import SQLiteQueryBuilder
from .operations import SQLiteOperations
from .federation import SQLiteFederation

class SQLiteWOFConnector(WOFConnectorBase):
    """Thin orchestration layer for SQLite backend."""

    def __init__(self, db_paths=None):
        super().__init__(db_paths)
        self.session_manager = SQLiteSessionManager(self.db_paths)
        self.query_builder = None  # Initialized after connect
        self.operations = None     # Initialized after connect
        self.federation = SQLiteFederation(self.config)

    async def connect(self):
        """Initialize connection and components."""
        engine = await self.session_manager.connect()
        tables = await self._get_tables(engine)
        self.query_builder = SQLiteQueryBuilder(tables)
        self.operations = SQLiteOperations(
            self.session_manager,
            self.query_builder
        )

    async def search(self, filters):
        """Delegate to operations."""
        return await self.operations.execute_search(filters)

    # Delegate all other methods to appropriate components
```

### Testing Requirements

1. **Unit Tests** for each new module:
   - `test_session.py`: Connection lifecycle, attachment
   - `test_queries.py`: Query construction correctness
   - `test_operations.py`: Data transformation
   - `test_federation.py`: Multi-database logic

2. **Integration Tests**:
   - Ensure refactored connector maintains same API
   - Test multi-database queries still work
   - Verify performance hasn't degraded

3. **Regression Tests**:
   - Run existing test suite without changes
   - All tests should pass with refactored backend

### Success Criteria

1. **Code Organization**:
   - No file exceeds 300 lines
   - Each module has single responsibility
   - Clear separation between concerns

2. **Maintainability**:
   - New backends can reuse query builders
   - Session management is isolated
   - Operations are testable in isolation

3. **Performance**:
   - No performance regression
   - Query execution time unchanged
   - Memory usage stable

4. **Compatibility**:
   - Public API unchanged
   - All existing tests pass
   - No breaking changes

### Implementation Order

1. Create new files with empty classes
2. Move session management (lowest risk)
3. Extract query builders (medium risk)
4. Extract operations (medium risk)
5. Add federation module (enhancement)
6. Refactor connector (highest risk)
7. Run full test suite
8. Remove old code

### Risk Mitigation

- Keep old code during migration
- Add feature flags for gradual rollout
- Extensive testing at each phase
- Code review after each module
- Performance benchmarking

### Estimated Effort

- Session Management: 2 hours
- Query Builders: 3 hours
- Operations: 3 hours
- Federation: 2 hours
- Connector Refactor: 2 hours
- Testing: 3 hours
- **Total: 15 hours**