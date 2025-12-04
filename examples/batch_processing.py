#!/usr/bin/env python3
"""
Batch processing example for WOF Explorer.

Demonstrates efficient batch operations and cursor patterns.
"""

import asyncio
from wof_explorer import WOFConnector, WOFSearchFilters, WOFBatchCursor, PlaceCollection


async def batch_example():
    """Demonstrate batch processing patterns."""

    connector = WOFConnector("whosonfirst-data-admin-us-latest.db")
    await connector.connect()

    # 1. Batch processing with known IDs
    print("Batch processing with known place IDs...")

    # Some major US cities (these IDs may need to be updated for your dataset)
    city_ids = [85922583, 85688637, 85633793]  # SF, Oakland, San Jose (example IDs)

    batch_cursor = WOFBatchCursor(city_ids, connector)
    cities = await batch_cursor.fetch_all()

    print(f"Fetched {len(cities)} cities:")
    for city in cities:
        print(f"  - {city.name}")

    # 2. Processing large result sets in chunks
    print("\nProcessing neighborhoods in chunks...")

    cursor = await connector.search(
        WOFSearchFilters(
            placetype="neighbourhood",
            region="California",
            is_current=True,
            limit=100,  # Large result set
        )
    )

    print(f"Found {cursor.total_count} neighborhoods to process")

    # Fetch all places first
    all_neighborhoods = await cursor.fetch_all()

    # Process in chunks of 10
    chunk_size = 10
    processed = 0

    # Process the neighborhoods in chunks
    for i in range(0, len(all_neighborhoods), chunk_size):
        chunk = all_neighborhoods[i : i + chunk_size]
        processed += len(chunk)
        print(f"  Processed chunk: {len(chunk)} places (total: {processed})")

        # Simulate some processing work
        for place in chunk:
            # Example: validate place names
            if len(place.name) < 2:
                print(f"    Warning: Short name '{place.name}' for ID {place.id}")

    # 3. Efficient aggregation with PlaceCollection
    print("\nAggregating data across multiple searches...")

    all_places = []

    # Search multiple regions
    regions = ["California", "New York", "Texas"]

    for region in regions:
        print(f"  Searching {region}...")
        region_cursor = await connector.search(
            WOFSearchFilters(
                placetype="locality", region=region, is_current=True, limit=20
            )
        )

        all_places.extend(region_cursor.places)

    # 4. Analyze the aggregated collection
    collection = PlaceCollection(places=all_places)

    # Get intelligent summary
    await collection.enrich_with_ancestors(connector)
    summary = collection.get_summary()

    print("\nAggregated Results Summary:")
    print(f"  Total places: {summary['total_count']}")

    if "by_ancestor" in summary:
        print("  By region:")
        for region, stats in summary["by_ancestor"].items():
            print(f"    {region}: {stats['count']} places")

    # 5. Export aggregated data
    print("\nExporting aggregated data...")

    # Export to different formats
    geojson = collection.to_geojson_string()
    csv_data = collection.to_csv_string()

    print(f"  GeoJSON: {len(geojson):,} characters")
    print(f"  CSV: {len(csv_data):,} characters")

    await connector.disconnect()
    print("\n✓ Batch processing complete!")


if __name__ == "__main__":
    asyncio.run(batch_example())
