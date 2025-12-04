#!/usr/bin/env python3
"""
Hierarchical search example for WOF Explorer.

Demonstrates navigating geographic hierarchies using cursors.
"""

import asyncio
from wof_explorer import WOFConnector, WOFSearchFilters, WOFHierarchyCursor


async def hierarchical_example():
    """Demonstrate hierarchical navigation."""

    connector = WOFConnector("whosonfirst-data-admin-us-latest.db")
    await connector.connect()

    # 1. Find a starting place (San Francisco)
    print("Finding San Francisco...")
    sf_cursor = await connector.search(
        WOFSearchFilters(
            name="San Francisco", placetype="locality", region="California"
        )
    )

    if not sf_cursor.has_results:
        print("San Francisco not found!")
        return

    sf = sf_cursor.places[0]
    print(f"Found: {sf.name} (ID: {sf.id})")

    # 2. Create hierarchy cursor for navigation
    hierarchy = WOFHierarchyCursor(sf, connector)

    # 3. Navigate up the hierarchy (ancestors)
    print(f"\nAncestors of {sf.name}:")
    ancestors = await hierarchy.fetch_ancestors()

    for i, ancestor in enumerate(ancestors):
        indent = "  " * i
        print(f"{indent}- {ancestor.name} ({ancestor.placetype})")

    # 4. Navigate down the hierarchy (descendants)
    print(f"\nNeighborhoods in {sf.name}:")
    neighborhoods = await hierarchy.fetch_descendants(
        filters=WOFSearchFilters(placetype="neighbourhood", limit=10)
    )

    for neighborhood in neighborhoods:
        status = "current" if neighborhood.is_current else "deprecated"
        print(f"  - {neighborhood.name} ({status})")

    print(f"\nFound {len(neighborhoods)} neighborhoods total")

    # 5. Find siblings (other localities in same county)
    print(f"\nOther cities near {sf.name}:")
    if ancestors:
        county = next((a for a in ancestors if a.placetype == "county"), None)
        if county:
            siblings_cursor = await connector.search(
                WOFSearchFilters(placetype="locality", ancestor_id=county.id, limit=5)
            )

            for sibling in siblings_cursor.places:
                if sibling.id != sf.id:  # Don't include SF itself
                    print(f"  - {sibling.name}")

    await connector.disconnect()
    print("\n✓ Hierarchical navigation complete!")


if __name__ == "__main__":
    asyncio.run(hierarchical_example())
