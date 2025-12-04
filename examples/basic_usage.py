#!/usr/bin/env python3
"""
Basic usage example for WOF Explorer.

This demonstrates core functionality using only the public API.
Shows how to connect, search, and export geographic data.
"""

import asyncio
from wof_explorer import WOFConnector, WOFSearchFilters, PlaceCollection


async def basic_example():
    """Demonstrate basic WOF Explorer usage."""

    # 1. Connect to WhosOnFirst database
    print("Connecting to WhosOnFirst database...")
    connector = WOFConnector("whosonfirst-data-admin-us-latest.db")
    await connector.connect()
    print("✓ Connected!")

    # 2. Search for neighborhoods in Chicago
    print("\nSearching for neighborhoods in Chicago...")
    cursor = await connector.search(
        WOFSearchFilters(
            placetype="neighbourhood",
            ancestor_name="Chicago",
            is_current=True,
            limit=10,
        )
    )

    print(f"Found {cursor.total_count} neighborhoods")
    print(f"Showing first {len(cursor.places)} results:")

    # 3. Display basic information
    for place in cursor.places:
        print(f"  - {place.name} (ID: {place.id})")

    # 4. Fetch with geometry for export
    print("\nFetching detailed data with geometry...")
    places_with_geometry = await cursor.fetch_all(include_geometry=True)

    # 5. Create collection and export to GeoJSON
    collection = PlaceCollection(places=places_with_geometry)
    geojson = collection.to_geojson_string()

    print(f"Generated GeoJSON with {len(places_with_geometry)} features")
    print(f"GeoJSON size: {len(geojson):,} characters")

    # 6. Basic summary
    summary = collection.get_summary()
    print("\nSummary:")
    print(f"  Total places: {summary['total_count']}")
    print(f"  Place types: {list(summary['by_placetype'].keys())}")

    # 7. Cleanup
    await connector.disconnect()
    print("\n✓ Example complete!")


if __name__ == "__main__":
    asyncio.run(basic_example())
