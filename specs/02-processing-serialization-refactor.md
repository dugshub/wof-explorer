# Processing & Serialization Refactor Specification

## Work Stream 2: Data Processing and Output Format Modularization

### Current State Analysis

The processing layer has 1,242 lines in `collections.py` containing:
- Collection operations (filtering, grouping, sampling)
- Data analysis (coverage, density, quality)
- All serialization formats (GeoJSON, CSV, WKT)
- Browsing and visualization logic
- Summary and reporting functions

Additionally, `cursors.py` (690 lines) contains:
- Result iteration patterns
- Cursor-based data fetching
- Some serialization logic

### Target Architecture

```
processing/
├── __init__.py              # Public exports
├── collections.py           # Core collection operations (300 lines)
├── cursors.py              # [EXISTING] Cursor patterns
├── analysis.py             # Data analysis and statistics (250 lines)
├── browser.py              # Browsing and navigation (200 lines)
└── serializers/            # Output format handlers
    ├── __init__.py         # Serializer registry
    ├── base.py             # Abstract serializer
    ├── geojson.py          # GeoJSON format (200 lines)
    ├── csv.py              # CSV format (150 lines)
    ├── wkt.py              # WKT format (100 lines)
    └── summary.py          # Summary reports (150 lines)
```

### Detailed Migration Plan

#### Phase 1: Create Serializer Base Infrastructure
**File**: `processing/serializers/base.py`

```python
"""
Base serializer infrastructure for WOF data export.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, IO
from pathlib import Path
from wof_explorer.models.places import WOFPlace, WOFPlaceWithGeometry

class SerializerBase(ABC):
    """Abstract base class for all serializers."""

    @abstractmethod
    def serialize(self, places: List[WOFPlace], **options) -> str:
        """Serialize places to string format."""
        pass

    @abstractmethod
    def serialize_to_dict(self, places: List[WOFPlace], **options) -> Dict[str, Any]:
        """Serialize places to dictionary/object format."""
        pass

    @abstractmethod
    def write(self, places: List[WOFPlace], file: IO, **options) -> None:
        """Write serialized data to file handle."""
        pass

    @abstractmethod
    def save(self, places: List[WOFPlace], path: Path, **options) -> None:
        """Save serialized data to file path."""
        pass

    def validate_options(self, **options) -> Dict[str, Any]:
        """Validate and normalize serializer options."""
        return options

class SerializerRegistry:
    """Registry for output format serializers."""

    _serializers: Dict[str, SerializerBase] = {}

    @classmethod
    def register(cls, format: str, serializer: SerializerBase):
        """Register a serializer for a format."""
        cls._serializers[format] = serializer

    @classmethod
    def get(cls, format: str) -> SerializerBase:
        """Get serializer for format."""
        if format not in cls._serializers:
            raise ValueError(f"Unknown format: {format}")
        return cls._serializers[format]

    @classmethod
    def formats(cls) -> List[str]:
        """List available formats."""
        return list(cls._serializers.keys())
```

#### Phase 2: Extract GeoJSON Serialization
**File**: `processing/serializers/geojson.py`

```python
"""
GeoJSON serializer for WOF places.
Handles Feature and FeatureCollection generation.
"""

from typing import List, Dict, Any, Optional
import json
from wof_explorer.models.places import WOFPlace, WOFPlaceWithGeometry
from .base import SerializerBase

class GeoJSONSerializer(SerializerBase):
    """Serializes WOF places to GeoJSON format."""

    def __init__(self):
        self.default_properties = [
            'id', 'name', 'placetype', 'is_current',
            'country', 'repo', 'population', 'area_m2'
        ]

    def serialize_to_dict(self, places: List[WOFPlace], **options) -> Dict[str, Any]:
        """Create GeoJSON FeatureCollection."""
        # Move lines 635-749 from collections.py

        features = []
        for place in places:
            feature = self._place_to_feature(place, **options)
            if feature:
                features.append(feature)

        return {
            "type": "FeatureCollection",
            "features": features,
            "properties": self._collection_properties(places, **options)
        }

    def _place_to_feature(self, place: WOFPlace, **options) -> Optional[Dict[str, Any]]:
        """Convert WOFPlace to GeoJSON Feature."""
        # Extract from to_geojson method

        if not isinstance(place, WOFPlaceWithGeometry) or not place.geometry:
            if options.get('require_geometry', True):
                return None

        properties = self._extract_properties(place, **options)
        geometry = self._extract_geometry(place)

        return {
            "type": "Feature",
            "id": place.id,
            "properties": properties,
            "geometry": geometry
        }

    def _extract_properties(self, place: WOFPlace, **options) -> Dict[str, Any]:
        """Extract properties for GeoJSON feature."""
        # Move property extraction logic

        include_props = options.get('properties', self.default_properties)
        exclude_props = options.get('exclude_properties', [])

        properties = {}
        for prop in include_props:
            if prop not in exclude_props and hasattr(place, prop):
                value = getattr(place, prop)
                if value is not None:
                    properties[prop] = value

        return properties

    def _extract_geometry(self, place: WOFPlaceWithGeometry) -> Optional[Dict[str, Any]]:
        """Extract and validate geometry."""
        # Move geometry handling

        if not place.geometry:
            return None

        # Handle nested Feature geometry
        if isinstance(place.geometry, dict):
            if place.geometry.get('type') == 'Feature':
                return place.geometry.get('geometry')
            return place.geometry

        return None

    def _collection_properties(self, places: List[WOFPlace], **options) -> Dict[str, Any]:
        """Generate collection-level properties."""
        return {
            "count": len(places),
            "placetypes": list(set(p.placetype for p in places)),
            "bounds": self._calculate_bounds(places)
        }

    def _calculate_bounds(self, places: List[WOFPlace]) -> Optional[List[float]]:
        """Calculate bounding box for all places."""
        # New method for bounds calculation
        pass

    def serialize(self, places: List[WOFPlace], **options) -> str:
        """Serialize to JSON string."""
        data = self.serialize_to_dict(places, **options)
        indent = options.get('indent', 2 if options.get('pretty', True) else None)
        return json.dumps(data, indent=indent)
```

**Migration from `collections.py`**:
- Move lines 635-749 (to_geojson) → GeoJSONSerializer
- Move lines 750-780 (to_geojson_string) → serialize method
- Move lines 1198-1226 (save_geojson) → save method

#### Phase 3: Extract CSV Serialization
**File**: `processing/serializers/csv.py`

```python
"""
CSV serializer for WOF places.
Exports tabular data with configurable columns.
"""

import csv
from io import StringIO
from typing import List, Dict, Any
from wof_explorer.models.places import WOFPlace
from .base import SerializerBase

class CSVSerializer(SerializerBase):
    """Serializes WOF places to CSV format."""

    def __init__(self):
        self.default_columns = [
            'id', 'name', 'placetype', 'is_current',
            'country', 'region', 'county', 'locality',
            'lat', 'lon', 'min_lat', 'min_lon', 'max_lat', 'max_lon',
            'population', 'area_m2', 'source', 'lastmodified'
        ]

    def serialize_to_dict(self, places: List[WOFPlace], **options) -> List[Dict[str, Any]]:
        """Convert places to list of row dictionaries."""
        # Move lines 781-819 from collections.py

        columns = options.get('columns', self.default_columns)
        rows = []

        for place in places:
            row = self._place_to_row(place, columns)
            rows.append(row)

        return rows

    def _place_to_row(self, place: WOFPlace, columns: List[str]) -> Dict[str, Any]:
        """Convert single place to CSV row."""
        row = {}

        for col in columns:
            if hasattr(place, col):
                value = getattr(place, col)
                row[col] = self._format_value(value)
            elif col in ['lat', 'lon'] and place.centroid:
                row['lat'] = place.centroid[1]
                row['lon'] = place.centroid[0]
            elif col in ['min_lat', 'min_lon', 'max_lat', 'max_lon'] and place.bbox:
                row['min_lon'] = place.bbox[0]
                row['min_lat'] = place.bbox[1]
                row['max_lon'] = place.bbox[2]
                row['max_lat'] = place.bbox[3]
            else:
                row[col] = None

        return row

    def _format_value(self, value: Any) -> Any:
        """Format value for CSV output."""
        if value is None:
            return ''
        elif isinstance(value, (list, dict)):
            return str(value)
        return value

    def serialize(self, places: List[WOFPlace], **options) -> str:
        """Serialize to CSV string."""
        rows = self.serialize_to_dict(places, **options)

        if not rows:
            return ''

        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

        return output.getvalue()

    def write(self, places: List[WOFPlace], file: Any, **options) -> None:
        """Write CSV directly to file handle."""
        rows = self.serialize_to_dict(places, **options)

        if not rows:
            return

        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
```

**Migration from `collections.py`**:
- Move lines 781-819 (to_csv_rows) → CSVSerializer
- Move lines 1227-1241 (save_csv) → save method
- Extract CSV formatting logic

#### Phase 4: Extract WKT Serialization
**File**: `processing/serializers/wkt.py`

```python
"""
WKT (Well-Known Text) serializer for WOF places.
Exports geometric data in WKT format.
"""

from typing import List, Dict, Any
from wof_explorer.models.places import WOFPlace, WOFPlaceWithGeometry
from .base import SerializerBase

class WKTSerializer(SerializerBase):
    """Serializes WOF places to WKT format."""

    def serialize_to_dict(self, places: List[WOFPlace], **options) -> List[Dict[str, Any]]:
        """Convert places to WKT records."""
        # Move lines 820-856 from collections.py

        records = []
        for place in places:
            if isinstance(place, WOFPlaceWithGeometry) and place.geometry:
                record = {
                    'id': place.id,
                    'name': place.name,
                    'wkt': self._geometry_to_wkt(place.geometry)
                }
                records.append(record)

        return records

    def _geometry_to_wkt(self, geometry: Dict[str, Any]) -> str:
        """Convert GeoJSON geometry to WKT."""
        # Implement GeoJSON to WKT conversion

        geom_type = geometry.get('type', '').upper()
        coords = geometry.get('coordinates', [])

        if geom_type == 'POINT':
            return f"POINT({coords[0]} {coords[1]})"
        elif geom_type == 'POLYGON':
            return self._polygon_to_wkt(coords)
        elif geom_type == 'MULTIPOLYGON':
            return self._multipolygon_to_wkt(coords)
        else:
            return f"{geom_type} EMPTY"

    def _polygon_to_wkt(self, coords: List) -> str:
        """Convert polygon coordinates to WKT."""
        rings = []
        for ring in coords:
            points = [f"{x} {y}" for x, y in ring]
            rings.append(f"({','.join(points)})")
        return f"POLYGON({','.join(rings)})"

    def _multipolygon_to_wkt(self, coords: List) -> str:
        """Convert multipolygon coordinates to WKT."""
        polygons = []
        for polygon in coords:
            rings = []
            for ring in polygon:
                points = [f"{x} {y}" for x, y in ring]
                rings.append(f"({','.join(points)})")
            polygons.append(f"({','.join(rings)})")
        return f"MULTIPOLYGON({','.join(polygons)})"

    def serialize(self, places: List[WOFPlace], **options) -> str:
        """Serialize to WKT text format."""
        records = self.serialize_to_dict(places, **options)
        lines = []
        for record in records:
            lines.append(f"{record['id']}\t{record['name']}\t{record['wkt']}")
        return '\n'.join(lines)
```

**Migration from `collections.py`**:
- Move lines 820-856 (to_wkt_list) → WKTSerializer
- Add proper WKT conversion methods

#### Phase 5: Extract Analysis Functions
**File**: `processing/analysis.py`

```python
"""
Data analysis and statistics for WOF place collections.
"""

from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
from wof_explorer.models.places import WOFPlace

class PlaceAnalyzer:
    """Analyzes WOF place collections for patterns and statistics."""

    def __init__(self, places: List[WOFPlace]):
        self.places = places

    def calculate_summary(self) -> Dict[str, Any]:
        """Generate comprehensive summary statistics."""
        # Move lines 206-246 from collections.py

        return {
            'count': len(self.places),
            'placetypes': self._placetype_distribution(),
            'status': self._status_distribution(),
            'countries': self._country_distribution(),
            'quality': self._quality_metrics(),
            'spatial': self._spatial_statistics()
        }

    def _placetype_distribution(self) -> Dict[str, int]:
        """Count places by type."""
        # Move from summary method
        return Counter(p.placetype for p in self.places)

    def _status_distribution(self) -> Dict[str, int]:
        """Count current vs deprecated places."""
        return {
            'current': sum(1 for p in self.places if p.is_current),
            'deprecated': sum(1 for p in self.places if p.deprecated),
            'ceased': sum(1 for p in self.places if p.cessation)
        }

    def _country_distribution(self) -> Dict[str, int]:
        """Count places by country."""
        return Counter(p.country for p in self.places if p.country)

    def _quality_metrics(self) -> Dict[str, Any]:
        """Calculate data quality metrics."""
        # Move lines 587-634 from collections.py

        return {
            'with_geometry': sum(1 for p in self.places
                               if hasattr(p, 'geometry') and p.geometry),
            'with_population': sum(1 for p in self.places if p.population),
            'with_area': sum(1 for p in self.places if p.area_m2),
            'completeness': self._calculate_completeness()
        }

    def _spatial_statistics(self) -> Dict[str, Any]:
        """Calculate spatial statistics."""
        # Move lines 361-407 from collections.py

        return {
            'bbox': self._calculate_overall_bbox(),
            'centroid': self._calculate_centroid(),
            'density_centers': self._calculate_density_centers()
        }

    def _calculate_overall_bbox(self) -> Optional[List[float]]:
        """Calculate bounding box covering all places."""
        # Extract from coverage_map method

        min_lon = min_lat = float('inf')
        max_lon = max_lat = float('-inf')

        for place in self.places:
            if place.bbox:
                min_lon = min(min_lon, place.bbox[0])
                min_lat = min(min_lat, place.bbox[1])
                max_lon = max(max_lon, place.bbox[2])
                max_lat = max(max_lat, place.bbox[3])

        if min_lon == float('inf'):
            return None

        return [min_lon, min_lat, max_lon, max_lat]

    def _calculate_centroid(self) -> Optional[Tuple[float, float]]:
        """Calculate average centroid."""
        centroids = [p.centroid for p in self.places if p.centroid]
        if not centroids:
            return None

        avg_lon = sum(c[0] for c in centroids) / len(centroids)
        avg_lat = sum(c[1] for c in centroids) / len(centroids)
        return (avg_lon, avg_lat)

    def _calculate_density_centers(self, grid_size: int = 5) -> List[Dict[str, Any]]:
        """Find density centers in spatial distribution."""
        # Move lines 408-464 from collections.py
        pass

    def _calculate_completeness(self) -> float:
        """Calculate data completeness score."""
        # New method for quality assessment

        total_fields = 10  # Define key fields
        scores = []

        for place in self.places:
            filled = sum(1 for field in ['name', 'placetype', 'country',
                                        'bbox', 'centroid', 'population']
                        if getattr(place, field, None))
            scores.append(filled / total_fields)

        return sum(scores) / len(scores) if scores else 0.0

    def analyze_coverage(self, requested: List[Any], found: List[Any]) -> Dict[str, Any]:
        """Analyze coverage of requested vs found items."""
        # Move lines 1162-1197 from collections.py

        return {
            'requested': len(requested),
            'found': len(found),
            'missing': list(set(requested) - set(found)),
            'coverage_percent': (len(found) / len(requested) * 100) if requested else 0
        }
```

**Migration from `collections.py`**:
- Move lines 206-246 (summary) → calculate_summary
- Move lines 361-407 (coverage_map) → spatial_statistics
- Move lines 408-464 (_calculate_density_centers) → _calculate_density_centers
- Move lines 587-634 (_browse_quality) → quality_metrics
- Move lines 1162-1197 (_get_coverage_report) → analyze_coverage

#### Phase 6: Extract Browser Functions
**File**: `processing/browser.py`

```python
"""
Browsing and navigation utilities for WOF place collections.
"""

from typing import List, Dict, Any
from wof_explorer.models.places import WOFPlace

class PlaceBrowser:
    """Provides different browsing views of place collections."""

    def __init__(self, places: List[WOFPlace]):
        self.places = places

    def browse(self, style: str = 'hierarchical') -> Dict[str, Any]:
        """Browse places in specified style."""
        # Move lines 465-488 from collections.py

        browsers = {
            'hierarchical': self._browse_hierarchical,
            'alphabetical': self._browse_alphabetical,
            'geographic': self._browse_geographic,
            'quality': self._browse_quality
        }

        if style not in browsers:
            raise ValueError(f"Unknown browse style: {style}")

        return browsers[style]()

    def _browse_hierarchical(self) -> Dict[str, Any]:
        """Hierarchical browsing by placetype."""
        # Move lines 489-517 from collections.py

        hierarchy = {}
        for place in self.places:
            placetype = place.placetype
            if placetype not in hierarchy:
                hierarchy[placetype] = []
            hierarchy[placetype].append({
                'id': place.id,
                'name': place.name,
                'parent': place.parent_id
            })

        return {
            'style': 'hierarchical',
            'data': hierarchy,
            'stats': {
                'total': len(self.places),
                'types': len(hierarchy)
            }
        }

    def _browse_alphabetical(self) -> Dict[str, Any]:
        """Alphabetical browsing by name."""
        # Move lines 518-542 from collections.py

        by_letter = {}
        for place in sorted(self.places, key=lambda p: p.name):
            letter = place.name[0].upper() if place.name else '#'
            if letter not in by_letter:
                by_letter[letter] = []
            by_letter[letter].append({
                'id': place.id,
                'name': place.name,
                'type': place.placetype
            })

        return {
            'style': 'alphabetical',
            'data': by_letter,
            'index': list(by_letter.keys())
        }

    def _browse_geographic(self) -> Dict[str, Any]:
        """Geographic browsing by country/region."""
        # Move lines 543-586 from collections.py

        by_country = {}
        for place in self.places:
            country = place.country or 'Unknown'
            if country not in by_country:
                by_country[country] = {
                    'regions': {},
                    'places': []
                }

            if place.region:
                region = place.region
                if region not in by_country[country]['regions']:
                    by_country[country]['regions'][region] = []
                by_country[country]['regions'][region].append({
                    'id': place.id,
                    'name': place.name,
                    'type': place.placetype
                })
            else:
                by_country[country]['places'].append({
                    'id': place.id,
                    'name': place.name,
                    'type': place.placetype
                })

        return {
            'style': 'geographic',
            'data': by_country,
            'countries': list(by_country.keys())
        }

    def _browse_quality(self) -> Dict[str, Any]:
        """Browse by data quality tiers."""
        # Move lines 587-634 from collections.py

        tiers = {
            'complete': [],
            'good': [],
            'basic': [],
            'minimal': []
        }

        for place in self.places:
            score = self._calculate_quality_score(place)
            if score >= 0.9:
                tier = 'complete'
            elif score >= 0.7:
                tier = 'good'
            elif score >= 0.5:
                tier = 'basic'
            else:
                tier = 'minimal'

            tiers[tier].append({
                'id': place.id,
                'name': place.name,
                'score': score
            })

        return {
            'style': 'quality',
            'data': tiers,
            'distribution': {k: len(v) for k, v in tiers.items()}
        }

    def _calculate_quality_score(self, place: WOFPlace) -> float:
        """Calculate quality score for a place."""
        score = 0.0
        checks = [
            (place.name, 0.2),
            (place.bbox, 0.2),
            (place.centroid, 0.1),
            (place.population, 0.15),
            (place.area_m2, 0.15),
            (hasattr(place, 'geometry') and place.geometry, 0.2)
        ]

        for check, weight in checks:
            if check:
                score += weight

        return score
```

**Migration from `collections.py`**:
- Move lines 465-488 (browse) → browse method
- Move lines 489-517 (_browse_hierarchical) → _browse_hierarchical
- Move lines 518-542 (_browse_alphabetical) → _browse_alphabetical
- Move lines 543-586 (_browse_geographic) → _browse_geographic
- Move lines 587-634 (_browse_quality) → _browse_quality

#### Phase 7: Refactor PlaceCollection
**File**: `processing/collections.py` (refactored)

```python
"""
Core collection operations for WOF places.
Handles filtering, grouping, and basic operations.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from wof_explorer.models.places import WOFPlace
from .serializers import SerializerRegistry
from .analysis import PlaceAnalyzer
from .browser import PlaceBrowser

class PlaceCollection(BaseModel):
    """Collection of WOF places with operations."""

    places: List[WOFPlace]
    metadata: Dict[str, Any] = {}
    _ancestors: Optional[Dict[int, WOFPlace]] = None

    def __len__(self) -> int:
        return len(self.places)

    def __iter__(self):
        return iter(self.places)

    def __getitem__(self, index):
        return self.places[index]

    # Core collection operations
    def filter(self, predicate) -> 'PlaceCollection':
        """Filter places by predicate function."""
        filtered = [p for p in self.places if predicate(p)]
        return PlaceCollection(places=filtered, metadata=self.metadata)

    def group_by(self, attribute: str) -> Dict[Any, List[WOFPlace]]:
        """Group places by attribute."""
        groups = {}
        for place in self.places:
            key = getattr(place, attribute, None)
            if key not in groups:
                groups[key] = []
            groups[key].append(place)
        return groups

    def unique_values(self, attribute: str) -> List[Any]:
        """Get unique values for attribute."""
        values = set()
        for place in self.places:
            value = getattr(place, attribute, None)
            if value is not None:
                values.add(value)
        return sorted(list(values))

    def find(self, name: str, exact: bool = True) -> List[WOFPlace]:
        """Find places by name."""
        if exact:
            return [p for p in self.places if p.name == name]
        else:
            name_lower = name.lower()
            return [p for p in self.places if name_lower in p.name.lower()]

    def find_one(self, name: str, exact: bool = True) -> Optional[WOFPlace]:
        """Find single place by name."""
        matches = self.find(name, exact)
        return matches[0] if matches else None

    def sample(self, n: int = 10, by: Optional[str] = None) -> 'PlaceCollection':
        """Sample places from collection."""
        import random
        if by:
            # Stratified sampling
            groups = self.group_by(by)
            sampled = []
            per_group = max(1, n // len(groups))
            for group_places in groups.values():
                sampled.extend(random.sample(
                    group_places,
                    min(per_group, len(group_places))
                ))
            return PlaceCollection(places=sampled[:n])
        else:
            # Simple random sampling
            sampled = random.sample(self.places, min(n, len(self.places)))
            return PlaceCollection(places=sampled)

    # Analysis delegation
    def get_summary(self, **options) -> Dict[str, Any]:
        """Get collection summary."""
        analyzer = PlaceAnalyzer(self.places)
        return analyzer.calculate_summary()

    def analyze_coverage(self, requested: List[Any], found: List[Any]) -> Dict[str, Any]:
        """Analyze coverage metrics."""
        analyzer = PlaceAnalyzer(self.places)
        return analyzer.analyze_coverage(requested, found)

    # Browsing delegation
    def browse(self, style: str = 'hierarchical') -> Dict[str, Any]:
        """Browse collection in different styles."""
        browser = PlaceBrowser(self.places)
        return browser.browse(style)

    # Serialization delegation
    def to_geojson(self, **options) -> Dict[str, Any]:
        """Export to GeoJSON."""
        serializer = SerializerRegistry.get('geojson')
        return serializer.serialize_to_dict(self.places, **options)

    def to_geojson_string(self, **options) -> str:
        """Export to GeoJSON string."""
        serializer = SerializerRegistry.get('geojson')
        return serializer.serialize(self.places, **options)

    def to_csv(self, **options) -> str:
        """Export to CSV."""
        serializer = SerializerRegistry.get('csv')
        return serializer.serialize(self.places, **options)

    def to_wkt(self, **options) -> str:
        """Export to WKT."""
        serializer = SerializerRegistry.get('wkt')
        return serializer.serialize(self.places, **options)

    def save(self, path: str, format: str = 'geojson', **options):
        """Save to file in specified format."""
        serializer = SerializerRegistry.get(format)
        serializer.save(self.places, Path(path), **options)

    # Ancestor enrichment
    async def enrich_with_ancestors(self, connector):
        """Enrich collection with ancestor data."""
        # Keep this method as it requires async connector
        ancestor_ids = set()
        for place in self.places:
            if place.parent_id:
                ancestor_ids.add(place.parent_id)

        if ancestor_ids:
            ancestors = await connector.get_places_by_ids(list(ancestor_ids))
            self._ancestors = {a.id: a for a in ancestors}

    # Convenience filters
    def filter_by_type(self, placetype: str) -> 'PlaceCollection':
        """Filter by placetype."""
        return self.filter(lambda p: p.placetype == placetype)

    def filter_by_status(self, is_current: bool = True) -> 'PlaceCollection':
        """Filter by current status."""
        return self.filter(lambda p: p.is_current == is_current)

    def group_by_type(self) -> Dict[str, 'PlaceCollection']:
        """Group into collections by type."""
        groups = self.group_by('placetype')
        return {
            ptype: PlaceCollection(places=places)
            for ptype, places in groups.items()
        }
```

### Testing Requirements

1. **Unit Tests** for each new module:
   - `test_serializers_geojson.py`: GeoJSON output validation
   - `test_serializers_csv.py`: CSV formatting
   - `test_serializers_wkt.py`: WKT conversion
   - `test_analysis.py`: Statistics calculations
   - `test_browser.py`: Browsing views

2. **Integration Tests**:
   - Serializer registry functionality
   - Collection delegation to components
   - Format conversion accuracy

3. **Performance Tests**:
   - Large collection serialization
   - Memory usage during export
   - Streaming capabilities

### Success Criteria

1. **Code Organization**:
   - Collections.py reduced to ~300 lines
   - Each serializer under 200 lines
   - Clear separation of concerns

2. **Extensibility**:
   - Easy to add new output formats
   - New analysis methods pluggable
   - Browser styles configurable

3. **Performance**:
   - No performance regression
   - Memory-efficient serialization
   - Streaming support for large datasets

4. **Compatibility**:
   - All existing methods work
   - Same output formats produced
   - No API changes

### Implementation Order

1. Create serializer base infrastructure
2. Extract GeoJSON serializer (most complex)
3. Extract CSV serializer
4. Extract WKT serializer
5. Extract analysis functions
6. Extract browser functions
7. Refactor PlaceCollection
8. Update imports and tests

### Risk Mitigation

- Test each serializer independently
- Validate output format compliance
- Compare outputs before/after
- Gradual migration with fallbacks
- Extensive integration testing

### Estimated Effort

- Serializer Infrastructure: 2 hours
- GeoJSON Serializer: 3 hours
- CSV Serializer: 2 hours
- WKT Serializer: 1 hour
- Analysis Module: 2 hours
- Browser Module: 2 hours
- Collection Refactor: 2 hours
- Testing & Integration: 3 hours
- **Total: 17 hours**