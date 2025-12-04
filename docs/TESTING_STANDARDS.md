# WOF Explorer Testing Standards

This document defines the testing philosophy, patterns, and requirements for the wof-explorer package.

## Core Philosophy

### 1. Contract-Based Testing
Tests verify **behavioral contracts**, not implementation details. This allows:
- Backend swapping without test rewrites
- Clear documentation of expected behavior
- Interface compliance verification

### 2. Three-Tier Test Architecture

```
┌─────────────────────────────────────────┐
│  Backend-Specific Tests                 │  ← SQLite-only features
│  (TestSQLiteSpecific)                   │
├─────────────────────────────────────────┤
│  Backend Implementation Tests           │  ← Inherit from contracts
│  (TestSQLiteWOFConnectorContract)       │
├─────────────────────────────────────────┤
│  Base Contract Tests                    │  ← Define the interface
│  (BaseWOFConnectorContract)             │
└─────────────────────────────────────────┘
```

### 3. Test Categories

| Category | Purpose | Marker |
|----------|---------|--------|
| **Contract** | Verify interface compliance | `@pytest.mark.contract` |
| **Unit** | Test isolated components | `@pytest.mark.unit` |
| **Integration** | Test component interaction | `@pytest.mark.integration` |
| **Performance** | Verify speed requirements | `@pytest.mark.benchmark` |

---

## Test Structure

### File Organization
```
tests/
├── conftest.py                    # Shared fixtures (if needed)
├── atoms/
│   └── connectors/
│       └── wof/
│           └── backends/
│               └── test_sqlite.py # Backend tests
├── discovery/
│   └── test_explorer.py           # Explorer tests
├── processing/
│   ├── test_collections.py        # Collection tests
│   ├── test_cursors.py            # Cursor tests
│   └── test_spatial.py            # Spatial operation tests
├── models/
│   ├── test_filters.py            # Filter model tests
│   ├── test_places.py             # Place model tests
│   └── test_geometry.py           # Geometry model tests
└── test_examples.py               # Example validation
```

### Naming Conventions

**Files**: `test_<module>.py`
**Classes**: `Test<Component><Category>` (e.g., `TestExplorerContract`)
**Methods**: `test_<operation>_<scenario>` (e.g., `test_search_with_empty_results`)

---

## Fixture Patterns

### 1. Database Fixture (Session-Scoped)
```python
@pytest.fixture(scope="session")
def test_db_path() -> Path:
    """
    Provides path to Barbados test database.
    Downloads automatically if not present.
    """
    # Use Barbados - small dataset, real hierarchy, fast tests
    ...
```

### 2. Connector Fixture (Async with Cleanup)
```python
@pytest_asyncio.fixture
async def connector(test_db_path):
    """Provides connected WOF connector with automatic cleanup."""
    connector = WOFConnector(str(test_db_path))
    await connector.connect()
    yield connector
    await connector.disconnect()
```

### 3. Test Data Fixture
```python
@pytest.fixture
def test_data() -> TestData:
    """Provides known test IDs from Barbados database."""
    return TestData(
        country_id=85632491,        # Barbados
        locality_id=1326720241,     # Moore Hill
        region_id=85670295,         # Saint Michael
    )
```

### 4. Collection Fixtures
```python
@pytest_asyncio.fixture
async def sample_collection(connector) -> PlaceCollection:
    """Provides a PlaceCollection with real data for testing."""
    cursor = await connector.search(WOFSearchFilters(limit=10))
    return await cursor.fetch_all()
```

---

## Test Patterns

### Pattern 1: Happy Path
Test the expected successful behavior.

```python
@pytest.mark.asyncio
async def test_search_by_name_returns_matching_places(self, connector):
    """Search by name should return places matching the query."""
    cursor = await connector.search(WOFSearchFilters(name="Bridgetown"))

    assert cursor.total_count > 0
    places = await cursor.fetch_all()
    assert any("Bridgetown" in p.name for p in places)
```

### Pattern 2: Edge Cases
Test boundary conditions and empty states.

```python
@pytest.mark.asyncio
async def test_search_with_no_matches_returns_empty(self, connector):
    """Search with impossible filters should return empty results."""
    cursor = await connector.search(
        WOFSearchFilters(name="ThisPlaceDoesNotExist12345")
    )

    assert cursor.total_count == 0
    assert cursor.has_results is False
    places = await cursor.fetch_all()
    assert len(places) == 0
```

### Pattern 3: Error Handling
Test that errors are raised appropriately.

```python
@pytest.mark.asyncio
async def test_search_without_connection_raises_error(self, test_db_path):
    """Operations on disconnected connector should raise."""
    connector = WOFConnector(str(test_db_path))
    # NOT connected

    with pytest.raises(RuntimeError) as exc_info:
        await connector.search(WOFSearchFilters())

    assert "connect" in str(exc_info.value).lower()
```

### Pattern 4: Type Verification
Verify return types match contracts.

```python
@pytest.mark.asyncio
async def test_fetch_all_returns_place_collection(self, connector):
    """fetch_all() must return PlaceCollection type."""
    cursor = await connector.search(WOFSearchFilters(limit=5))
    result = await cursor.fetch_all()

    assert isinstance(result, PlaceCollection)
    assert all(isinstance(p, WOFPlace) for p in result)
```

### Pattern 5: State Verification
Verify object state after operations.

```python
@pytest.mark.asyncio
async def test_cursor_preserves_filters(self, connector):
    """Cursor should preserve the filters used to create it."""
    filters = WOFSearchFilters(placetype="locality", limit=10)
    cursor = await connector.search(filters)

    assert cursor.query_filters.get("placetype") == "locality"
    assert cursor.query_filters.get("limit") == 10
```

### Pattern 6: Concurrent Operations
Test thread-safety and concurrent access.

```python
@pytest.mark.asyncio
async def test_concurrent_searches_are_independent(self, connector):
    """Multiple concurrent searches should not interfere."""
    results = await asyncio.gather(
        connector.search(WOFSearchFilters(placetype="locality")),
        connector.search(WOFSearchFilters(placetype="region")),
    )

    assert results[0].query_filters["placetype"] == "locality"
    assert results[1].query_filters["placetype"] == "region"
```

---

## Assertion Guidelines

### Do Use
```python
# Type assertions
assert isinstance(result, PlaceCollection)

# Property assertions
assert cursor.total_count >= 0
assert place.name is not None

# Collection assertions
assert all(p.placetype == "locality" for p in places)
assert any("Bridge" in p.name for p in places)

# Length assertions
assert len(results) <= limit
assert len(results) > 0
```

### Don't Use
```python
# Don't test exact counts (data may change)
assert cursor.total_count == 47  # BAD - brittle

# Don't test exact values unless testing specific IDs
assert place.name == "Bridgetown"  # BAD unless using known test ID

# Don't use assertTrue/assertFalse (pytest prefers plain assert)
self.assertTrue(result)  # BAD
assert result  # GOOD
```

---

## Test Data Strategy

### Barbados Test Database
We use the Barbados (BB) WhosOnFirst database because:
- **Small**: ~5MB, fast downloads
- **Complete**: Has real hierarchy (country → regions → localities)
- **Stable**: Unlikely to change significantly

### Known Test IDs (Barbados)
```python
BARBADOS_COUNTRY_ID = 85632491
SAINT_MICHAEL_REGION_ID = 85670295
BRIDGETOWN_LOCALITY_ID = 102027145
MOORE_HILL_LOCALITY_ID = 1326720241
```

### Test Data Principles
1. **Use real data**: Barbados database has actual geographic relationships
2. **Use known IDs**: Reference specific places by ID for deterministic tests
3. **Don't depend on counts**: Exact record counts may vary
4. **Test relationships**: Verify hierarchy relationships, not specific values

---

## Coverage Requirements

### Minimum Coverage by Module Type

| Module Type | Minimum | Target |
|-------------|---------|--------|
| Core (connector, operations) | 85% | 95% |
| Processing (cursors, collections) | 70% | 85% |
| Models | 75% | 90% |
| Discovery | 60% | 80% |
| Display/Formatting | 30% | 50% |

### What Must Be Tested
1. All public API methods
2. All error conditions that raise exceptions
3. All code paths that affect return values
4. Edge cases (empty, null, boundary values)

### What Can Have Lower Coverage
1. Display/formatting code (visual output)
2. Debug/logging code paths
3. Deprecated methods (marked for removal)

---

## Writing New Tests Checklist

- [ ] Test file follows naming convention: `test_<module>.py`
- [ ] Test class inherits from appropriate contract (if applicable)
- [ ] Tests use async fixtures with proper cleanup
- [ ] Tests use known Barbados test data IDs
- [ ] Tests verify types, not just values
- [ ] Tests include happy path, edge cases, and error cases
- [ ] Tests are independent (no order dependency)
- [ ] Tests use appropriate pytest markers
- [ ] Tests have clear, descriptive names
- [ ] Tests have docstrings explaining intent

---

## Running Tests

```bash
# All tests
make test-wof

# With coverage
cd wof-explorer && uv run pytest tests/ --cov=wof_explorer --cov-report=term-missing

# Specific markers
cd wof-explorer && uv run pytest tests/ -m "contract" -v

# Single file
cd wof-explorer && uv run pytest tests/processing/test_collections.py -v

# Single test
cd wof-explorer && uv run pytest tests/test_file.py::TestClass::test_method -v
```
