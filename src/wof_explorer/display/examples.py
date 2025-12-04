#!/usr/bin/env python3
"""
Examples demonstrating all display utilities.

Run this file to see all display formats in action:
    python -m wof_explorer.display.examples
"""

import asyncio
import time
from typing import List, Optional
from dataclasses import dataclass

from .tree import TreeDisplay, TreeStyle, print_wof_hierarchy, print_ancestors_tree
from .table import print_table, print_summary, print_comparison
from .progress import ProgressDisplay, StatusDisplay, ProgressStyle
from .styles import set_theme, success, error, warning, info, header
from .formatter import (
    format_number,
    format_size,
    format_duration,
    format_percentage,
    format_place,
    format_hierarchy_path,
)


# Sample data for demonstrations
@dataclass
class SamplePlace:
    id: int
    name: str
    placetype: str
    country: str = "US"
    is_current: bool = True
    population: Optional[int] = None


def demo_tree_displays():
    """Demonstrate various tree display styles."""
    print(header("\n=== Tree Display Examples ===\n"))

    # Sample hierarchy data
    ancestors = [
        SamplePlace(1, "United States", "country"),
        SamplePlace(2, "California", "region"),
        SamplePlace(3, "San Francisco County", "county"),
        SamplePlace(4, "San Francisco", "locality"),
    ]

    print("1. Unicode Style (default):")
    print_wof_hierarchy(ancestors)

    print("\n2. ASCII Style:")
    print_wof_hierarchy(ancestors, style=TreeStyle.ASCII)

    print("\n3. Simple Style:")
    print_wof_hierarchy(ancestors, style=TreeStyle.SIMPLE)

    print("\n4. With Icons:")
    tree = TreeDisplay()
    tree.config.show_icons = True
    tree.add_node("🌍 United States")
    tree.add_child("📍 California", parent="🌍 United States")
    tree.add_child("🏙️ San Francisco", parent="📍 California")
    tree.add_child("🏘️ Mission District", parent="🏙️ San Francisco")
    tree.add_child("🏘️ Castro", parent="🏙️ San Francisco")
    print(tree.render())

    print("\n5. Ancestors Tree:")
    print_ancestors_tree(ancestors)


def demo_table_displays():
    """Demonstrate table display styles."""
    print(header("\n=== Table Display Examples ===\n"))

    # Sample data
    places = [
        {
            "name": "San Francisco",
            "type": "locality",
            "population": 873965,
            "area_km2": 121.4,
        },
        {
            "name": "Oakland",
            "type": "locality",
            "population": 433031,
            "area_km2": 202.0,
        },
        {
            "name": "San Jose",
            "type": "locality",
            "population": 1021795,
            "area_km2": 466.1,
        },
        {
            "name": "Berkeley",
            "type": "locality",
            "population": 124321,
            "area_km2": 45.9,
        },
    ]

    print("1. Simple Table:")
    print_table(places, columns=["name", "population", "area_km2"])

    print("\n2. Summary Table:")
    stats = {
        "Total Cities": len(places),
        "Total Population": format_number(sum(p["population"] for p in places)),
        "Average Population": format_number(
            sum(p["population"] for p in places) / len(places)
        ),
        "Total Area (km²)": format_number(
            sum(p["area_km2"] for p in places), decimals=1
        ),
    }
    print_summary("Bay Area Statistics", stats)

    print("\n3. Comparison Table:")
    before = {
        "Places": 1000,
        "With Geometry": 750,
        "Current": 900,
        "Deprecated": 100,
    }
    after = {
        "Places": 1250,
        "With Geometry": 1100,
        "Current": 1150,
        "Deprecated": 100,
    }
    print_comparison(before, after, "Before Import", "After Import")


def demo_progress_displays():
    """Demonstrate progress indicators."""
    print(header("\n=== Progress Display Examples ===\n"))

    print("1. Progress Bar:")
    progress = ProgressDisplay(total=50, description="Loading places")
    for i in range(50):
        progress.update(i)
        time.sleep(0.02)
    progress.finish("✓ Completed")

    print("\n2. Spinner:")
    progress = ProgressDisplay(
        total=30,
        description="Processing",
        config=ProgressConfig(style=ProgressStyle.SPINNER),
    )
    for i in range(30):
        progress.update(i)
        time.sleep(0.05)
    progress.finish()

    print("\n3. Status Display:")
    status = StatusDisplay()

    status.start("Connecting to database")
    time.sleep(0.5)
    status.success()

    status.start("Loading configuration")
    time.sleep(0.3)
    status.success()

    status.start("Fetching places")
    time.sleep(0.4)
    status.warning("Partial data")

    status.start("Validating geometry")
    time.sleep(0.2)
    status.error("Invalid geometries found")

    status.start("Exporting results")
    time.sleep(0.3)
    status.skip("No changes")

    print()
    status.summary()


def demo_formatters():
    """Demonstrate formatting utilities."""
    print(header("\n=== Formatter Examples ===\n"))

    print("Numbers:")
    print(f"  {format_number(1234567)} places")
    print(f"  {format_number(1234.567, decimals=2)} km²")

    print("\nSizes:")
    print(f"  Database: {format_size(1234567890)}")
    print(f"  Cache: {format_size(45678)}")

    print("\nDurations:")
    print(f"  Query time: {format_duration(1.5)}")
    print(f"  Total time: {format_duration(3661)}")
    print(f"  Short form: {format_duration(3661, short=True)}")

    print("\nPercentages:")
    print(f"  Coverage: {format_percentage(750, 1000)}")
    print(f"  Success rate: {format_percentage(95, 100, decimals=2)}")

    print("\nPlaces:")
    place = SamplePlace(85922583, "San Francisco", "locality", population=873965)
    print(f"  Basic: {format_place(place)}")
    print(f"  With ID: {format_place(place, include_id=True)}")

    print("\nHierarchy:")
    hierarchy = [
        SamplePlace(1, "United States", "country"),
        SamplePlace(2, "California", "region"),
        SamplePlace(3, "San Francisco", "locality"),
    ]
    print(f"  Path: {format_hierarchy_path(hierarchy)}")


def demo_themes():
    """Demonstrate different themes."""
    print(header("\n=== Theme Examples ===\n"))

    themes = ["default", "minimal", "ascii"]

    for theme_name in themes:
        print(f"\n{theme_name.upper()} Theme:")
        set_theme(theme_name)

        print(success("Success message"))
        print(error("Error message"))
        print(warning("Warning message"))
        print(info("Info message"))

        # Tree sample
        tree = TreeDisplay()
        tree.add_node("Root")
        tree.add_child("Child 1", parent="Root")
        tree.add_child("Child 2", parent="Root")
        print(tree.render())

    # Reset to default
    set_theme("default")


async def demo_wof_integration():
    """Demonstrate integration with WOF connector."""
    print(header("\n=== WOF Integration Example ===\n"))

    try:
        from wof_explorer import WOFConnector, WOFSearchFilters

        # Verify imports work
        _ = WOFConnector, WOFSearchFilters

        # This would normally connect to a real database
        print("Connecting to database...")
        # connector = WOFConnector('database.db')
        # await connector.connect()

        # Simulated data
        print(success("Connected to WhosOnFirst database"))

        # Simulated search
        print("\nSearching for cities in California...")
        cities = [
            SamplePlace(1, "San Francisco", "locality", population=873965),
            SamplePlace(2, "Los Angeles", "locality", population=3898747),
            SamplePlace(3, "San Diego", "locality", population=1386932),
        ]

        # Display results in table
        data = [
            {"id": c.id, "name": c.name, "population": format_number(c.population)}
            for c in cities
        ]
        print_table(data)

        # Display hierarchy for one city
        print("\nHierarchy for San Francisco:")
        ancestors = [
            SamplePlace(1, "North America", "continent"),
            SamplePlace(2, "United States", "country"),
            SamplePlace(3, "California", "region"),
            SamplePlace(4, "San Francisco County", "county"),
            SamplePlace(5, "San Francisco", "locality"),
        ]
        print_wof_hierarchy(ancestors)

    except ImportError:
        print(warning("WOF connector not available for live demo"))
        print("Using simulated data instead")


def main():
    """Run all demonstrations."""
    print("=" * 60)
    print(header("WOF Explorer Display Utilities Demonstration"))
    print("=" * 60)

    demo_tree_displays()
    demo_table_displays()
    demo_progress_displays()
    demo_formatters()
    demo_themes()

    # Run async demo
    asyncio.run(demo_wof_integration())

    print(header("\n=== End of Demonstrations ==="))
    print(success("All display utilities demonstrated successfully!"))


# Also make importable for testing
def get_sample_hierarchy() -> List[SamplePlace]:
    """Get sample hierarchy for testing."""
    return [
        SamplePlace(1, "United States", "country"),
        SamplePlace(2, "California", "region"),
        SamplePlace(3, "San Francisco County", "county"),
        SamplePlace(4, "San Francisco", "locality"),
        SamplePlace(5, "Mission District", "neighbourhood"),
    ]


if __name__ == "__main__":
    # Fix import issue for ProgressConfig
    from .progress import ProgressConfig

    main()
