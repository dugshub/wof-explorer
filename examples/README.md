# WOF Explorer Examples

This directory contains examples demonstrating various features of the WOF Explorer package.

## Prerequisites

All examples require a WhosOnFirst SQLite database. You can download one from:
- [WhosOnFirst Data Downloads](https://data.whosonfirst.org/sqlite/)

Update the database path in each example to match your local file.

## Examples

### 1. `basic_usage.py`
**Getting started with WOF Explorer**
- Connecting to a database
- Basic search operations
- Exporting to GeoJSON
- Using PlaceCollection for summaries

```bash
python examples/basic_usage.py
```

### 2. `hierarchical_search.py`
**Navigating geographic hierarchies**
- Finding ancestors (country → region → county)
- Finding descendants (city → neighborhoods)
- Using WOFHierarchyCursor for efficient navigation
- Finding sibling places

```bash
python examples/hierarchical_search.py
```

### 3. `spatial_queries.py`
**Working with spatial data**
- Bounding box searches
- Proximity queries
- Analyzing geographic areas
- Spatial filtering

```bash
python examples/spatial_queries.py
```

### 4. `batch_processing.py`
**Efficient batch operations**
- Processing large result sets
- Chunked iteration for memory efficiency
- Aggregating data from multiple searches
- Using WOFBatchCursor

```bash
python examples/batch_processing.py
```

## Database Setup

To run these examples, you'll need a WhosOnFirst database file. Here's how to get started:

1. **Download a database**:
   ```bash
   # Download US admin data (example)
   curl -O https://data.whosonfirst.org/sqlite/whosonfirst-data-admin-us-latest.db
   ```

2. **Update the examples**:
   - Change the database path in each example file
   - Update place names/IDs to match your region

3. **Run an example**:
   ```bash
   cd wof-explorer
   python examples/basic_usage.py
   ```

## Common Patterns

### Async/Await
All WOF Explorer operations are asynchronous:
```python
async def my_function():
    connector = WOFConnector('database.db')
    await connector.connect()
    # ... do work
    await connector.disconnect()

asyncio.run(my_function())
```

### Error Handling
```python
try:
    cursor = await connector.search(filters)
    if cursor.has_results:
        places = await cursor.fetch_all()
    else:
        print("No results found")
except Exception as e:
    print(f"Search failed: {e}")
```

### Memory Efficiency
For large datasets, use cursors and chunked processing:
```python
# Don't fetch everything at once
cursor = await connector.search(filters)

# Process in chunks
async for chunk in cursor.process_in_chunks(chunk_size=100):
    # Process each chunk
    pass
```

## Need Help?

- Check the main [README](../README.md) for installation and setup
- Review the [API documentation](../docs/api.md)
- Open an issue if you find problems with these examples