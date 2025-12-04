# Processing & Serialization Refactor (Work Stream 2)

This refactor modularizes the processing layer into focused modules and pluggable serializers.

## New Layout
- `wof_explorer/processing/collections.py`: Core collection ops (filter, group, sample, describe) + thin delegators.
- `wof_explorer/processing/cursors.py`: Existing cursor patterns for lazy fetching.
- `wof_explorer/processing/analysis.py`: `PlaceAnalyzer` with summary and simple spatial stats.
- `wof_explorer/processing/browser.py`: `PlaceBrowser` for hierarchical/alphabetical/geographic/quality views.
- `wof_explorer/processing/serializers/`: Format handlers and registry.
  - `base.py`: `SerializerBase`, `SerializerRegistry`.
  - `geojson.py`, `csv.py`, `wkt.py`: Concrete serializers (self-registered).

## Usage Examples
- Serialize via registry
  - `collection.serialize('geojson', pretty=True)`
  - `collection.serialize_to('out.csv', 'csv')`
- Legacy helpers (delegated)
  - `collection.to_geojson()` → GeoJSON dict
  - `collection.to_geojson_string()` → JSON string
  - `collection.to_csv_rows()` → list[dict]
  - `collection.to_wkt_list()` → list[dict]
- Analysis/Browsing
  - `collection.analysis_summary()` → dict
  - `collection.browse_view('hierarchical')` → dict

## Notes
- GeoJSON Feature geometry is unwrapped if a Feature object is provided.
- CSV includes latitude/longitude and bbox columns by default.
- WKT supports Point/LineString/Polygon/Multi*; returns `id`, `name`, `wkt` (plus `placetype` for compatibility in `to_wkt_list`).
- Backwards compatibility is preserved for existing collection methods; internals now delegate to serializers.

## Next Steps
- Expand serializer options (column selection, property maps, strict mode).
- Add tests around serializers and analysis stats.
- Document custom serializer registration for extensions.
