#!/usr/bin/env -S uv run --python 3.13

"""
Quick Explore Demo

Generates GeoJSON files for:
  - US counties
  - Focus cities (localities)
  - Neighborhoods for those cities

Usage:
  uv run python wof-explorer/scripts/quick_explore_demo.py

Ensure WOF_DATA_DIR points at your local WOF dataset directory
containing one or more SQLite admin DBs.
"""

import asyncio
from pathlib import Path

from wof_explorer.factory import get_wof_connector
from wof_explorer.processing.quick_explore import quick_explore, DEFAULT_FOCUS_CITIES


async def main() -> None:
    connector = get_wof_connector()
    await connector.connect()

    selections = await quick_explore(connector, focus_cities=DEFAULT_FOCUS_CITIES)

    outdir = Path("wof-explorer/output")
    outdir.mkdir(parents=True, exist_ok=True)

    for key, collection in selections.items():
        path = outdir / f"{key}.geojson"
        geojson = collection.to_geojson_string(
            indent=2, use_polygons=True, require_geometry=False
        )
        path.write_text(geojson, encoding="utf-8")
        print(f"Wrote {key}: {path} ({len(collection)} features)")

    await connector.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
