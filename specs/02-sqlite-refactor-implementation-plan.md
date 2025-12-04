# SQLite Backend Refactoring Implementation Plan

## Executive Summary

Based on analysis of the current 1,015-line `connector.py` file and the refactor specification, this plan details the step-by-step implementation to modularize the SQLite backend following the Infrastructure Subsystem Pattern.

## Current State Assessment

### File Analysis
- **connector.py**: 1,015 lines containing all functionality
- **tables.py**: 2,208 lines (already modularized - good!)
- **Single class**: `SQLiteWOFConnector` with 25 methods
- **Key responsibilities mixed**:
  - Connection/session management (lines 93-258)
  - Query building (lines 287-875)
  - Data operations & transformation (lines 956-996)
  - Multi-database federation (lines 124-155)
  - Discovery operations (lines 876-918)

### Dependencies
- Inherits from `WOFConnectorBase` (abstract base)
- Uses `WOFExplorer` via property pattern
- Returns cursor objects (`WOFSearchCursor`, etc.)
- Heavy SQLAlchemy usage (Core, not ORM)

## Target Architecture

```
wof-explorer/wof_explorer/backends/sqlite/
├── __init__.py           # Re-export main connector
├── connector.py          # Thin orchestration (~150 lines)
├── session.py            # Connection & database management (~200 lines)
├── queries.py            # SQL query builders (~300 lines)
├── operations.py         # Query execution & transformation (~250 lines)
├── federation.py         # Multi-database logic (~100 lines)
└── tables.py             # [EXISTING] Table definitions
```

## Implementation Phases

### Phase 1: Session Management Module (2 hours)

**File**: `session.py`

Extract from `connector.py`:
- Lines 40-92: Initialization logic
- Lines 93-123: `connect()` method
- Lines 124-133: `_attach_databases()`
- Lines 134-155: `_create_unified_views()`
- Lines 156-250: `_get_unified_tables()`
- Lines 251-258: `disconnect()`

**New Class Structure**:
```python
class SQLiteSessionManager:
    def __init__(self, db_paths: List[Path], config: WOFConfig)
    async def connect() -> AsyncEngine
    def connect_sync() -> Engine
    async def attach_databases(engine: AsyncEngine) -> None
    async def create_unified_views(engine: AsyncEngine) -> None
    async def get_unified_tables() -> Dict[str, Any]
    async def disconnect() -> None
    def get_database_aliases() -> Dict[str, str]
```

### Phase 2: Query Builders Module (3 hours)

**File**: `queries.py`

Extract from `connector.py`:
- Lines 287-575: Search query construction
- Lines 638-710: Hierarchy queries (children, descendants)
- Lines 710-764: Ancestor queries
- Lines 808-875: Batch/ID queries
- Lines 919-955: Filter application logic

**New Class Structure**:
```python
class SQLiteQueryBuilder:
    def __init__(self, tables: Dict[str, Any])
    def build_search_query(filters: WOFSearchFilters) -> Select
    def build_hierarchy_query(place_id: int, direction: str) -> Select
    def build_ancestors_query(place_id: int) -> Select
    def build_batch_query(ids: List[int], include_geo: bool) -> Select
    def apply_filters(query: Select, table: Table, filters: WOFFilters) -> Select
    def build_spatial_query(bbox: BBox = None) -> Select
```

### Phase 3: Operations Module (3 hours)

**File**: `operations.py`

Extract from `connector.py`:
- Lines 576-637: `get_place` execution
- Lines 956-996: Row transformation logic
- Execution logic from search/hierarchy methods

**New Class Structure**:
```python
class SQLiteOperations:
    def __init__(self, session_manager: SQLiteSessionManager,
                 query_builder: SQLiteQueryBuilder)
    async def execute_search(filters: WOFSearchFilters) -> WOFSearchCursor
    async def execute_get_place(place_id: int, include_geo: bool) -> Optional[WOFPlace]
    async def execute_hierarchy(place_id: int, direction: str) -> List[WOFPlace]
    async def execute_batch(ids: List[int], include_geo: bool) -> List[WOFPlace]
    def transform_row_to_place(row: Row) -> WOFPlace
    def transform_row_with_geometry(row: Row) -> WOFPlaceWithGeometry
```

### Phase 4: Federation Module (2 hours)

**File**: `federation.py`

New functionality extracted and enhanced:
- Database discovery logic
- Attachment SQL generation
- Unified view creation
- Schema validation

**New Class Structure**:
```python
class SQLiteFederation:
    def __init__(self, config: WOFConfig)
    def discover_databases() -> List[Path]
    def create_attach_statements(databases: List[Path]) -> List[str]
    def create_unified_view_ddl(table_name: str, dbs: Dict[str, str]) -> str
    def validate_schema_compatibility(databases: List[Path]) -> bool
    def get_database_for_source(source: str) -> Optional[str]
```

### Phase 5: Connector Refactor (2 hours)

**File**: `connector.py` (refactored)

Becomes thin orchestration layer:
```python
class SQLiteWOFConnector(WOFConnectorBase):
    def __init__(self, db_paths=None):
        super().__init__(db_paths)
        self.session_manager = SQLiteSessionManager(self.db_paths)
        self.query_builder = None
        self.operations = None
        self.federation = SQLiteFederation(self.config)

    async def connect(self):
        engine = await self.session_manager.connect()
        tables = await self.session_manager.get_unified_tables()
        self.query_builder = SQLiteQueryBuilder(tables)
        self.operations = SQLiteOperations(self.session_manager, self.query_builder)

    # Delegate all methods to appropriate components
    async def search(self, filters):
        return await self.operations.execute_search(filters)
```

## Migration Strategy

### Step-by-Step Process

1. **Create module structure** (30 min)
   - Create empty module files
   - Set up imports and class shells
   - Ensure imports work

2. **Extract session management** (2 hours)
   - Move connection logic
   - Test connection lifecycle
   - Verify multi-database attachment

3. **Extract query builders** (3 hours)
   - Move query construction
   - Keep queries testable
   - Ensure filter application works

4. **Extract operations** (3 hours)
   - Move execution logic
   - Move transformation logic
   - Test data flow

5. **Add federation module** (2 hours)
   - Implement discovery
   - Add schema validation
   - Test multi-database queries

6. **Refactor connector** (2 hours)
   - Convert to orchestrator
   - Delegate to components
   - Verify API compatibility

7. **Testing & validation** (3 hours)
   - Run existing test suite
   - Add module-specific tests
   - Performance benchmarking

## Testing Plan

### Unit Tests (New)
```
tests/atoms/connectors/wof/backends/sqlite/
├── test_session.py       # Connection, attachment tests
├── test_queries.py       # Query construction tests
├── test_operations.py    # Execution and transformation tests
└── test_federation.py    # Multi-database tests
```

### Integration Tests (Existing)
- `test_sqlite.py` - Should pass unchanged
- `test_contract.py` - Verify interface compliance
- `test_backward_compat.py` - Ensure no breaking changes

### Performance Tests
- Benchmark before/after refactor
- Query execution time
- Memory usage profile
- Multi-database query performance

## Risk Analysis & Mitigation

### Risks
1. **Breaking API changes** → Maintain exact interface
2. **Performance regression** → Benchmark at each phase
3. **Test failures** → Keep old code until tests pass
4. **Import cycles** → Careful dependency management
5. **Async/sync mismatch** → Clear separation of concerns

### Mitigation Strategies
- Feature flags for gradual rollout
- Parallel implementation (keep old code)
- Comprehensive test coverage
- Code review after each module
- Performance profiling

## Success Metrics

### Code Quality
- [ ] No file exceeds 300 lines
- [ ] Each module has single responsibility
- [ ] Clear separation of concerns
- [ ] No circular dependencies

### Functionality
- [ ] All existing tests pass
- [ ] No performance regression
- [ ] Multi-database queries work
- [ ] Explorer pattern maintained

### Maintainability
- [ ] New backends can reuse components
- [ ] Modules testable in isolation
- [ ] Clear documentation
- [ ] Consistent patterns

## Implementation Timeline

### Day 1 (8 hours)
- Hour 1-2: Session management extraction
- Hour 3-5: Query builder extraction
- Hour 6-8: Operations extraction

### Day 2 (7 hours)
- Hour 1-2: Federation module
- Hour 3-4: Connector refactor
- Hour 5-7: Testing and validation

**Total Estimated: 15 hours**

## Next Steps

1. Review this plan with team
2. Set up feature branch in worktree
3. Begin Phase 1 implementation
4. Daily progress updates
5. Code review after each phase

## Notes for Implementation

### Critical Path Items
- Session management is foundation - must be solid
- Query builders must maintain exact SQL generation
- Operations must preserve transformation logic
- Federation is enhancement - can be simplified if needed

### Watch Points
- Async engine management
- Table reference passing
- Cursor object creation
- Explorer property access

### Dependencies to Preserve
- WOFConnectorBase interface
- Cursor return types
- PlaceCollection compatibility
- Explorer via property pattern