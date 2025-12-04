# Spec: Types and Enums Consolidation

## Objective
Consolidate duplicate type definitions and enums into a single, authoritative source to eliminate redundancy and ensure consistency across the WOF Explorer codebase.

## Current State
- **Single PlaceType definition** lives in `wof_explorer/types.py` with utilities and type guards
- **Legacy module removed**: `wof_explorer/enums.py` is gone; all imports must point to `wof_explorer.types`
- **Inconsistent usage** persists in some models/filters using `str` for placetype instead of enum
- **Scattered type definitions**: Some types may be defined inline rather than centrally

## Target State
- Single source of truth for all types and enums in `wof_explorer/types.py`
- Consistent enum usage throughout models and backends
- Type-safe placetype handling with proper validation

## Implementation Tasks

### Phase 1: Consolidation (Priority 1)
1. **Ensure no references to removed module**
   - Search for `wof_explorer.enums`
   - Replace with `wof_explorer.types`

2. **Update all imports**
   - Find all references to `from wof_explorer.enums import`
   - Replace with `from wof_explorer.types import`
   - Update any `from ..enums` relative imports

3. **Fix broken test imports**
   - Update `tests/test_wof_connector.py` line 13
   - Fix any other test imports referencing old enums

### Phase 2: Type Migration (Priority 2)
1. **Update model definitions**
   ```python
   # Change in wof_explorer/models/places.py
   # From: placetype: str
   # To:   placetype: PlaceType
   ```

2. **Add type conversion in backends**
   ```python
   # In SQLite operations when creating WOFPlace
   placetype=PlaceType(row['placetype'])  # With validation
   ```

3. **Update filters to accept enum**
   ```python
   # In WOFSearchFilters
   placetype: Optional[Union[PlaceType, List[PlaceType]]]
   ```

### Phase 3: Validation (Priority 2)
1. **Add pydantic validators**
   ```python
   @field_validator('placetype')
   def validate_placetype(cls, v):
       if isinstance(v, str):
           return PlaceType(normalize_placetype(v))
       return v
   ```

2. **Add conversion utilities**
   - String to enum conversion with normalization
   - Backward compatibility for string inputs
   - Clear error messages for invalid types

### Phase 4: Testing (Priority 1)
1. **Test enum functionality**
   - Hierarchy level calculation
   - Type classification methods
   - Normalization functions

2. **Test backward compatibility**
   - String inputs still work
   - API contracts maintained
   - Serialization handles enums properly

## Success Criteria
- [ ] No duplicate type/enum definitions
- [ ] All imports resolve correctly
- [ ] Tests pass without import errors
- [ ] PlaceType enum used consistently
- [ ] Type validation working
- [ ] Backward compatibility maintained

## Migration Path
1. Create feature branch: `refactor/types-consolidation`
2. Run consolidation tasks
3. Run full test suite
4. Update documentation
5. Merge to main

## Risk Mitigation
- **Risk**: Breaking API compatibility
  - **Mitigation**: Keep string acceptance in filters, convert internally

- **Risk**: Serialization issues with enums
  - **Mitigation**: Ensure serializers handle enum.value properly

- **Risk**: Test failures from type changes
  - **Mitigation**: Update test fixtures gradually, maintain backward compat

## Estimated Effort
- Consolidation: 30 minutes
- Type migration: 1 hour
- Testing & validation: 1 hour
- Total: ~2.5 hours

## Notes
- The `types.py` version is more complete and should be the survivor
- Consider adding `__str__` and `__repr__` methods to enums for better debugging
- May want to add a deprecation warning for string placetype usage initially
- Ensure CSV/JSON serialization outputs string values, not enum objects
