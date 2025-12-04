#!/usr/bin/env python3
"""
Spatial queries example for WOF Explorer.

Demonstrates bounding box searches and spatial filtering.
"""

import asyncio
from wof_explorer import WOFConnector, WOFSearchFilters


class BBox:
    """Simple bounding box class for examples."""

    def __init__(self, min_lat, max_lat, min_lon, max_lon):
        self.min_lat = min_lat
        self.max_lat = max_lat
        self.min_lon = min_lon
        self.max_lon = max_lon


async def spatial_example():
    """Demonstrate spatial queries."""

    connector = WOFConnector("whosonfirst-data-admin-us-latest.db")
    await connector.connect()

    # 1. Bounding box search (San Francisco Bay Area)
    print("Searching Bay Area with bounding box...")

    # Bay Area approximate bounds
    bay_area_bbox = BBox(min_lat=37.4, max_lat=37.9, min_lon=-122.6, max_lon=-122.0)

    cursor = await connector.search(
        WOFSearchFilters(placetype="locality", bbox=bay_area_bbox, is_current=True)
    )

    print(f"Found {len(cursor.places)} cities in Bay Area:")
    for place in cursor.places[:10]:  # Show first 10
        print(f"  - {place.name}")

    # 2. Fetch with geometry to analyze areas
    print("\nFetching geometry data...")
    places_with_geom = await cursor.fetch_all(include_geometry=True)

    # 3. Analyze the spatial data
    total_area = 0
    largest_city = None
    largest_area = 0

    for place in places_with_geom:
        if hasattr(place, "area_sqkm") and place.area_sqkm:
            area = float(place.area_sqkm)
            total_area += area

            if area > largest_area:
                largest_area = area
                largest_city = place

    print("\nSpatial Analysis:")
    print(f"  Total area covered: {total_area:.1f} sq km")
    if largest_city:
        print(f"  Largest city: {largest_city.name} ({largest_area:.1f} sq km)")

    # 4. Search by proximity (places near a point)
    print("\nSearching places near San Francisco center...")
    sf_center_lat, sf_center_lon = 37.7749, -122.4194

    # Create a small bounding box around the point
    proximity_bbox = BBox(
        min_lat=sf_center_lat - 0.1,
        max_lat=sf_center_lat + 0.1,
        min_lon=sf_center_lon - 0.1,
        max_lon=sf_center_lon + 0.1,
    )

    nearby_cursor = await connector.search(
        WOFSearchFilters(
            placetype="neighbourhood", bbox=proximity_bbox, is_current=True, limit=5
        )
    )

    print(f"Found {len(nearby_cursor.places)} neighborhoods near SF center:")
    for place in nearby_cursor.places:
        print(f"  - {place.name}")

    await connector.disconnect()
    print("\n✓ Spatial queries complete!")


if __name__ == "__main__":
    asyncio.run(spatial_example())
