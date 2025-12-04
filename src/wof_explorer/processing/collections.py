"""
Place collections with serialization capabilities.
Provides a clean way to work with groups of places and export them to various formats.
"""

from typing import ClassVar, List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
import random
from collections import Counter

from wof_explorer.models.places import WOFPlace
from wof_explorer.types import PlaceType, PlacetypeLike, coerce_placetype
from wof_explorer.display.descriptor import DisplayDescriptor


class PlaceCollection(BaseModel):
    """
    Collection of places with serialization methods.

    This provides a clean separation between data fetching (cursors)
    and data serialization (collections).
    """

    display: ClassVar[DisplayDescriptor] = DisplayDescriptor()

    places: List[WOFPlace]
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_places(cls, places: List[WOFPlace], **metadata) -> "PlaceCollection":
        """
        Create a collection from a list of places.

        Args:
            places: List of WOFPlace objects
            **metadata: Additional metadata to store with the collection

        Returns:
            New PlaceCollection instance
        """
        return cls(places=places, metadata=metadata)

    def __len__(self) -> int:
        """Return number of places in collection."""
        return len(self.places)

    def __iter__(self):
        """Iterate over places."""
        return iter(self.places)

    def __getitem__(self, index):
        """Get place by index."""
        return self.places[index]

    def __repr__(self) -> str:
        """Return a concise representation of the collection."""
        if self.is_empty:
            return "PlaceCollection(empty)"

        # Get basic stats
        summary = self.summary()
        total = summary["count"]

        # Get placetype breakdown (top 3)
        placetypes = summary.get("placetypes", {})
        if placetypes:
            top_types = sorted(placetypes.items(), key=lambda x: x[1], reverse=True)[:3]
            types_str = ", ".join([f"{t}:{c}" for t, c in top_types])
        else:
            types_str = "no types"

        # Check geometry availability and type
        if self.has_geometry:
            # We have actual geometry data loaded
            geom_types = set()
            for p in self.places:
                if hasattr(p, "geometry_type") and p.geometry_type:
                    geom_types.add(p.geometry_type)
            if geom_types:
                geom_str = f"with {'/'.join(sorted(geom_types))}"
            else:
                geom_str = "with geometry"
        else:
            # No geometry loaded, but check src_geom to understand what's available
            src_geoms = set()
            for p in self.places:
                if hasattr(p, "src_geom") and p.src_geom:
                    src_geoms.add(p.src_geom)

            if src_geoms:
                # We know these places have polygon sources available
                geom_str = "polygon sources available"
            else:
                geom_str = "no geometry loaded"

        return f"PlaceCollection({total} places: {types_str} | {geom_str})"

    @property
    def is_empty(self) -> bool:
        """Check if collection is empty."""
        return len(self.places) == 0

    @property
    def has_geometry(self) -> bool:
        """Check if any places have geometry."""
        return any(
            hasattr(p, "geometry") and p.geometry is not None for p in self.places
        )

    # ============= Collection Operations =============

    def find(self, name: str, exact: bool = True) -> List[WOFPlace]:
        """
        Find places by name.

        Args:
            name: Name to search for
            exact: If True, exact match. If False, case-insensitive partial match.

        Returns:
            List of matching places (can be empty or multiple since names aren't unique)
        """
        if exact:
            return [p for p in self.places if p.name == name]
        else:
            name_lower = name.lower()
            return [p for p in self.places if name_lower in p.name.lower()]

    def find_one(self, name: str, exact: bool = True) -> Optional[WOFPlace]:
        """
        Get first place matching name.

        Args:
            name: Name to search for
            exact: If True, exact match. If False, case-insensitive partial match.

        Returns:
            First matching place or None
        """
        matches = self.find(name, exact)
        return matches[0] if matches else None

    def filter(self, predicate) -> "PlaceCollection":
        """
        Filter places and return new collection.

        Args:
            predicate: Function that takes a place and returns bool

        Returns:
            New PlaceCollection with filtered places

        Examples:
            >>> active = collection.filter(lambda p: p.is_current == 1)
            >>> neighborhoods = collection.filter(lambda p: p.placetype == PlaceType.NEIGHBOURHOOD)
            >>> zetashapes = collection.filter(lambda p: p.repo == 'zetashapes')
        """
        filtered_places = [p for p in self.places if predicate(p)]
        return PlaceCollection.from_places(
            filtered_places,
            **self.metadata,  # Preserve metadata
        )

    def group_by(self, attribute: str) -> Dict[Any, List[WOFPlace]]:
        """
        Group places by an attribute.

        Args:
            attribute: Name of the attribute to group by

        Returns:
            Dictionary mapping attribute values to lists of places

        Examples:
            >>> by_type = collection.group_by('placetype')
            >>> by_repo = collection.group_by('repo')
            >>> by_status = collection.group_by('is_current')
        """
        groups: dict[Any, list[WOFPlace]] = {}
        for place in self.places:
            if hasattr(place, attribute):
                key = getattr(place, attribute)
                if key not in groups:
                    groups[key] = []
                groups[key].append(place)
        return groups

    def unique_values(self, attribute: str) -> List[Any]:
        """
        Get unique values for an attribute.

        Args:
            attribute: Name of the attribute

        Returns:
            List of unique values

        Examples:
            >>> placetypes = collection.unique_values('placetype')
            >>> repos = collection.unique_values('repo')
        """
        values = set()
        for place in self.places:
            if hasattr(place, attribute):
                values.add(getattr(place, attribute))
        return sorted(list(values))

    def summary(self) -> Dict[str, Any]:
        """
        Get a summary of the collection contents.

        Returns:
            Dictionary with collection statistics
        """
        if self.is_empty:
            return {"count": 0, "placetypes": {}, "repos": {}, "status": {}}

        placetype_counts: dict[str, int] = {}
        repo_counts: dict[str, int] = {}
        status_counts = {"current": 0, "deprecated": 0, "ceased": 0}

        for place in self.places:
            # Count placetypes
            if place.placetype:
                placetype_counts[place.placetype] = (
                    placetype_counts.get(place.placetype, 0) + 1
                )

            # Count repos
            if place.repo:
                repo_counts[place.repo] = repo_counts.get(place.repo, 0) + 1

            # Count status
            if place.is_current == 1:
                status_counts["current"] += 1
            if place.is_deprecated:
                status_counts["deprecated"] += 1
            if place.is_ceased:
                status_counts["ceased"] += 1

        return {
            "count": len(self.places),
            "placetypes": placetype_counts,
            "repos": repo_counts,
            "status": status_counts,
            "has_geometry": self.has_geometry,
        }

    # ============= Exploration Methods =============

    def sample(self, n: int = 10, by: Optional[str] = None) -> "PlaceCollection":
        """
        Get a representative sample of places.

        Args:
            n: Number of samples to get (per group if 'by' is specified)
            by: Optional attribute to group by before sampling

        Returns:
            New PlaceCollection with sampled places

        Examples:
            >>> sample = collection.sample(5)  # Random 5 places
            >>> by_type = collection.sample(2, by='placetype')  # 2 from each placetype
        """
        if self.is_empty:
            return PlaceCollection(places=[])

        if by:
            # Stratified sampling
            samples = []
            groups = self.group_by(by)
            for key, items in groups.items():
                sample_size = min(n, len(items))
                samples.extend(random.sample(items, sample_size))
            return PlaceCollection.from_places(samples, sample_type="stratified", by=by)
        else:
            # Random sampling
            sample_size = min(n, len(self.places))
            sampled = random.sample(self.places, sample_size)
            return PlaceCollection.from_places(sampled, sample_type="random", size=n)

    def top_names(self, n: int = 10) -> List[Tuple[str, int]]:
        """
        Get most common place names.

        Args:
            n: Number of top names to return

        Returns:
            List of (name, count) tuples

        Examples:
            >>> top = collection.top_names(5)
            >>> # [('Park', 12), ('North', 8), ('South', 8), ...]
        """
        if self.is_empty:
            return []

        name_counts = Counter(p.name for p in self.places)
        return name_counts.most_common(n)

    def describe(self, verbose: bool = False) -> str:
        """
        Get a human-readable description of the collection.

        Args:
            verbose: Include more detailed information

        Returns:
            Formatted description string
        """
        if self.is_empty:
            return "Empty collection"

        lines = []
        summary = self.summary()

        # Basic stats
        lines.append(f"Collection of {summary['count']} places")

        # Placetype breakdown
        if summary["placetypes"]:
            lines.append("\nBy type:")
            for ptype, count in sorted(
                summary["placetypes"].items(), key=lambda x: x[1], reverse=True
            ):
                pct = (count / summary["count"]) * 100
                lines.append(f"  • {ptype}: {count} ({pct:.1f}%)")

        # Geographic extent
        if self.places:
            lats = [p.latitude for p in self.places if p.latitude is not None]
            lons = [p.longitude for p in self.places if p.longitude is not None]
            if lats and lons:
                lines.append("\nGeographic extent:")
                lines.append(f"  • Latitude: {min(lats):.2f}° to {max(lats):.2f}°")
                lines.append(f"  • Longitude: {min(lons):.2f}° to {max(lons):.2f}°")

        # Data sources
        if summary["repos"]:
            lines.append("\nData sources:")
            for repo, count in sorted(
                summary["repos"].items(), key=lambda x: x[1], reverse=True
            ):
                pct = (count / summary["count"]) * 100
                lines.append(f"  • {repo}: {count} ({pct:.1f}%)")

        # Top names
        if verbose:
            top_names = self.top_names(5)
            if top_names:
                lines.append("\nMost common names:")
                for name, count in top_names:
                    lines.append(f"  • {name}: appears {count} times")

        # Status
        if summary["status"]["current"] > 0:
            lines.append("\nStatus:")
            lines.append(f"  • Current: {summary['status']['current']}")
            if summary["status"]["deprecated"] > 0:
                lines.append(f"  • Deprecated: {summary['status']['deprecated']}")
            if summary["status"]["ceased"] > 0:
                lines.append(f"  • Ceased: {summary['status']['ceased']}")

        return "\n".join(lines)

    def coverage_map(self) -> Dict[str, Any]:
        """
        Analyze geographic coverage without knowing place names.

        Returns:
            Dictionary with coverage analysis
        """
        if self.is_empty:
            return {
                "countries": {},
                "top_regions": [],
                "top_localities": [],
                "bounding_box": None,
                "density_centers": [],
            }

        # Country breakdown
        countries = Counter(p.country for p in self.places if p.country)

        # Find top regions and localities
        regions = Counter(
            p.name
            for p in self.places
            if coerce_placetype(p.placetype) == PlaceType.REGION
        )
        localities = Counter(
            p.name
            for p in self.places
            if coerce_placetype(p.placetype) == PlaceType.LOCALITY
        )

        # Calculate bounding box
        lats = [p.latitude for p in self.places if p.latitude is not None]
        lons = [p.longitude for p in self.places if p.longitude is not None]
        bbox: Dict[str, Any] = {}
        if lats and lons:
            min_lat, max_lat = min(lats), max(lats)
            min_lon, max_lon = min(lons), max(lons)
            bbox = {
                "min_lat": min_lat,
                "max_lat": max_lat,
                "min_lon": min_lon,
                "max_lon": max_lon,
                "center": ((min_lat + max_lat) / 2, (min_lon + max_lon) / 2),
            }

        # Find density centers (simple grid-based approach)
        density_centers = self._calculate_density_centers()

        result: Dict[str, Any] = {
            "countries": dict(countries),
            "top_regions": regions.most_common(10),
            "top_localities": localities.most_common(10),
            "bounding_box": bbox,
            "density_centers": density_centers,
        }

        if bbox and "max_lat" in bbox:
            result["total_area_sq_deg"] = (bbox["max_lat"] - bbox["min_lat"]) * (
                bbox["max_lon"] - bbox["min_lon"]
            )
        else:
            result["total_area_sq_deg"] = 0.0

        return result

    def _calculate_density_centers(self, grid_size: int = 5) -> List[Dict[str, Any]]:
        """Calculate density centers using a simple grid approach."""
        if self.is_empty:
            return []

        lats = [p.latitude for p in self.places if p.latitude is not None]
        lons = [p.longitude for p in self.places if p.longitude is not None]

        if not lats or not lons:
            return []

        lat_min, lat_max = min(lats), max(lats)
        lon_min, lon_max = min(lons), max(lons)

        lat_step = (lat_max - lat_min) / grid_size
        lon_step = (lon_max - lon_min) / grid_size

        if lat_step == 0 or lon_step == 0:
            # All places at same location
            return [
                {
                    "lat": lat_min,
                    "lon": lon_min,
                    "count": len(self.places),
                    "density": "single_point",
                }
            ]

        # Count places in each grid cell
        grid: dict[tuple[int, int], int] = {}
        for place in self.places:
            if place.latitude is None or place.longitude is None:
                continue
            lat_idx = min(int((place.latitude - lat_min) / lat_step), grid_size - 1)
            lon_idx = min(int((place.longitude - lon_min) / lon_step), grid_size - 1)
            key = (lat_idx, lon_idx)
            grid[key] = grid.get(key, 0) + 1

        # Find top density centers
        centers = []
        for (lat_idx, lon_idx), count in sorted(
            grid.items(), key=lambda x: x[1], reverse=True
        )[:5]:
            center_lat = lat_min + (lat_idx + 0.5) * lat_step
            center_lon = lon_min + (lon_idx + 0.5) * lon_step

            # Determine density level
            max_count = max(grid.values())
            if count > max_count * 0.7:
                density = "high"
            elif count > max_count * 0.3:
                density = "medium"
            else:
                density = "low"

            centers.append(
                {
                    "lat": round(center_lat, 4),
                    "lon": round(center_lon, 4),
                    "count": count,
                    "density": density,
                }
            )

        return centers

    def browse(self, style: str = "hierarchical") -> Dict[str, Any]:
        """
        Browse collection contents in different ways.

        Args:
            style: Browse style - 'hierarchical', 'alphabetical', 'geographic', or 'quality'

        Returns:
            Organized view of the collection
        """
        if self.is_empty:
            return {"style": style, "content": {}}

        if style == "hierarchical":
            return self._browse_hierarchical()
        elif style == "alphabetical":
            return self._browse_alphabetical()
        elif style == "geographic":
            return self._browse_geographic()
        elif style == "quality":
            return self._browse_quality()
        else:
            raise ValueError(f"Unknown browse style: {style}")

    def _browse_hierarchical(self) -> Dict[str, Any]:
        """Build hierarchical tree view."""
        tree = {}

        # Group by placetype hierarchy
        hierarchy: Dict[str, List[str]] = {
            "country": [],
            "region": [],
            "county": [],
            "locality": [],
            "neighbourhood": [],
            "other": [],
        }

        for place in self.places:
            if place.placetype in hierarchy:
                hierarchy[place.placetype].append(place.name)
            else:
                hierarchy["other"].append(f"{place.name} ({place.placetype})")

        # Remove empty levels
        tree = {k: list(set(v))[:20] for k, v in hierarchy.items() if v}

        return {
            "style": "hierarchical",
            "content": tree,
            "note": "Showing up to 20 unique names per level",
        }

    def _browse_alphabetical(self) -> Dict[str, Any]:
        """Build alphabetical index."""
        index: Dict[str, List[Dict[str, Any]]] = {}

        for place in self.places:
            first_letter = place.name[0].upper() if place.name else "#"
            if first_letter not in index:
                index[first_letter] = []
            index[first_letter].append(
                {"name": place.name, "type": place.placetype, "id": place.id}
            )

        # Sort and limit each letter group
        for letter in index:
            index[letter] = sorted(index[letter], key=lambda x: x["name"])[:10]

        return {
            "style": "alphabetical",
            "content": index,
            "letters": sorted(index.keys()),
            "note": "Showing up to 10 places per letter",
        }

    def _browse_geographic(self) -> Dict[str, Any]:
        """Browse by geographic quadrants."""
        if self.is_empty:
            return {"style": "geographic", "content": {}}

        lats = [p.latitude for p in self.places if p.latitude is not None]
        lons = [p.longitude for p in self.places if p.longitude is not None]
        if not lats or not lons:
            return {"style": "geographic", "content": {}}
        center_lat = (min(lats) + max(lats)) / 2
        center_lon = (min(lons) + max(lons)) / 2

        quadrants: Dict[str, List[WOFPlace]] = {
            "northeast": [],
            "northwest": [],
            "southeast": [],
            "southwest": [],
        }

        for place in self.places:
            if place.latitude is not None and place.longitude is not None:
                if place.latitude >= center_lat:
                    if place.longitude >= center_lon:
                        quadrants["northeast"].append(place)
                    else:
                        quadrants["northwest"].append(place)
                else:
                    if place.longitude >= center_lon:
                        quadrants["southeast"].append(place)
                    else:
                        quadrants["southwest"].append(place)

        result = {}
        for quad, places in quadrants.items():
            if places:
                result[quad] = {
                    "count": len(places),
                    "sample": [p.name for p in places[:5]],
                    "types": Counter(p.placetype for p in places).most_common(3),
                }

        return {
            "style": "geographic",
            "content": result,
            "center": {"lat": center_lat, "lon": center_lon},
        }

    def _browse_quality(self) -> Dict[str, Any]:
        """Browse by data quality indicators."""
        quality_groups: Dict[str, List[WOFPlace]] = {
            "with_geometry": [],
            "point_only": [],
            "current": [],
            "deprecated": [],
            "zetashapes": [],
            "other_sources": [],
        }

        for place in self.places:
            # Check geometry
            has_geom = hasattr(place, "geometry") and place.geometry is not None
            if has_geom:
                quality_groups["with_geometry"].append(place)
            else:
                quality_groups["point_only"].append(place)

            # Check status
            if place.is_current == 1:
                quality_groups["current"].append(place)
            elif place.is_deprecated:
                quality_groups["deprecated"].append(place)

            # Check source
            if place.repo == "zetashapes":
                quality_groups["zetashapes"].append(place)
            elif place.repo:
                quality_groups["other_sources"].append(place)

        result = {}
        for category, places in quality_groups.items():
            if places:
                result[category] = {
                    "count": len(places),
                    "percentage": round(len(places) / len(self.places) * 100, 1),
                    "sample": [p.name for p in places[:5]],
                }

        return {"style": "quality", "content": result, "total_places": len(self.places)}

    # ============= Serialization Methods =============

    def to_geojson(
        self,
        properties: Optional[List[str]] = None,
        use_polygons: bool = True,
        include_all_metadata: bool = False,
        require_geometry: bool = False,
    ) -> Dict[str, Any]:
        """Convert collection to GeoJSON FeatureCollection via GeoJSONSerializer."""
        from .serializers import SerializerRegistry

        serializer = SerializerRegistry.get("geojson")
        return serializer.serialize_to_dict(
            self.places,
            properties=properties,
            use_polygons=use_polygons,
            include_all_metadata=include_all_metadata,
            require_geometry=require_geometry,
        )

    def to_geojson_string(
        self,
        indent: int = 2,
        properties: Optional[List[str]] = None,
        use_polygons: bool = True,
        include_all_metadata: bool = False,
        require_geometry: bool = False,
    ) -> str:
        """
        Convert to GeoJSON string ready for pasting.

        Args:
            indent: JSON indentation level
            properties: List of place attributes to include in feature properties.
                       Pass None for default set, empty list [] for no properties,
                       or specific field names to include.
                       Special value 'all' includes all available fields.
            use_polygons: If True, use polygon/multipolygon geometry when available.
                         If False, always use point geometry (lat/lon only).
            include_all_metadata: If True, include all available place fields in properties.
                                 Overrides properties list if set.

        Returns:
            JSON string of GeoJSON FeatureCollection
        """
        return self.serialize(
            "geojson",
            indent=indent,
            pretty=True,
            properties=properties,
            use_polygons=use_polygons,
            include_all_metadata=include_all_metadata,
            require_geometry=require_geometry,
        )

    def to_csv_rows(self) -> List[Dict[str, Any]]:
        """
        Convert collection to CSV-friendly rows.

        Returns:
            List of dictionaries suitable for CSV export
        """
        from .serializers import SerializerRegistry

        serializer = SerializerRegistry.get("csv")
        return serializer.serialize_to_dict(self.places)

    def to_wkt_list(self) -> List[Dict[str, Any]]:
        """
        Convert to Well-Known Text format for GIS tools.

        Returns:
            List of places with WKT geometries
        """
        from .serializers import SerializerRegistry

        serializer = SerializerRegistry.get("wkt")
        records = serializer.serialize_to_dict(self.places)
        # Preserve placetype for backward compatibility if available
        recs = []
        for p, r in zip(self.places, records):
            rec = dict(r)
            rec.setdefault("placetype", getattr(p, "placetype", None))
            recs.append(rec)
        return recs

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.

        Returns:
            Dictionary with places and metadata
        """
        return {
            "places": [p.model_dump() for p in self.places],
            "metadata": self.metadata,
            "count": len(self.places),
        }

    # ============= New Serializer/Analysis Hooks =============

    def serialize(self, format: str, **options) -> str:
        """Serialize places using registered serializers (e.g., 'geojson', 'csv', 'wkt')."""
        from .serializers import SerializerRegistry

        serializer = SerializerRegistry.get(format)
        return serializer.serialize(self.places, **options)

    def serialize_to(self, path: str, format: str, **options) -> None:
        """Serialize and save output to path using a registered serializer."""
        from pathlib import Path
        from .serializers import SerializerRegistry

        serializer = SerializerRegistry.get(format)
        serializer.save(self.places, Path(path), **options)

    def analysis_summary(self) -> Dict[str, Any]:
        """Return analysis summary derived from PlaceAnalyzer."""
        from .analysis import PlaceAnalyzer

        return PlaceAnalyzer(self.places).calculate_summary()

    def browse_view(self, style: str = "hierarchical") -> Dict[str, Any]:
        """Return a browsable view using PlaceBrowser styles."""
        from .browser import PlaceBrowser

        return PlaceBrowser(self.places).browse(style)

    # ============= Filtering Methods =============

    def filter_by_type(self, placetype: PlacetypeLike) -> "PlaceCollection":
        """
        Filter places by type.

        Args:
            placetype: Place type to filter by

        Returns:
            New PlaceCollection with filtered places
        """
        target = coerce_placetype(placetype)
        filtered = [p for p in self.places if coerce_placetype(p.placetype) == target]
        return PlaceCollection(
            places=filtered,
            metadata={**self.metadata, "filter": f"placetype={target.value}"},
        )

    def filter_by_status(self, is_current: bool = True) -> "PlaceCollection":
        """
        Filter places by status.

        Args:
            is_current: Filter for current places

        Returns:
            New PlaceCollection with filtered places
        """
        filtered = [p for p in self.places if p.is_current == (1 if is_current else 0)]
        return PlaceCollection(
            places=filtered,
            metadata={**self.metadata, "filter": f"is_current={is_current}"},
        )

    def group_by_type(self) -> Dict[str, "PlaceCollection"]:
        """
        Group places by type.

        Returns:
            Dictionary mapping place types to PlaceCollections
        """
        groups: Dict[str, List[WOFPlace]] = {}
        for place in self.places:
            key = coerce_placetype(place.placetype).value
            if key not in groups:
                groups[key] = []
            groups[key].append(place)

        return {
            ptype: PlaceCollection(places=places, metadata={"placetype": ptype})
            for ptype, places in groups.items()
        }

    # ============= Utility Methods =============

    async def enrich_with_ancestors(self, connector) -> "PlaceCollection":
        """
        Enrich the collection with ancestor data for intelligent grouping.

        Args:
            connector: WOFConnector instance to fetch ancestor data

        Returns:
            Self for chaining
        """
        if not self.places:
            return self

        # Batch fetch ancestors for all places
        ancestor_data = {}
        for place in self.places:
            ancestors = await connector.get_ancestors(place.id)
            ancestor_data[place.id] = [
                {
                    "id": a.id,
                    "name": a.name,
                    "placetype": (
                        a.placetype.value
                        if hasattr(a.placetype, "value")
                        else str(a.placetype)
                    ),
                }
                for a in ancestors
            ]

        # Store in metadata
        if self.metadata is None:
            self.metadata = {}
        self.metadata["ancestor_data"] = ancestor_data
        return self

    async def enrich_with_geometry(self, connector) -> "PlaceCollection":
        """
        Enrich the collection with geometry data.

        Args:
            connector: WOFConnector instance to fetch geometry data

        Returns:
            Self for chaining
        """
        if not self.places:
            return self

        # Get place IDs
        place_ids = [p.id for p in self.places]

        # Batch fetch places with geometry

        places_with_geom = await connector.get_places(place_ids, include_geometry=True)

        # Create a mapping of ID to place with geometry
        geom_map = {p.id: p for p in places_with_geom if p}

        # Replace places with geometry-enriched versions
        enriched_places = []
        for place in self.places:
            if place.id in geom_map:
                enriched_places.append(geom_map[place.id])
            else:
                enriched_places.append(place)

        self.places = enriched_places
        return self

    def get_summary(self, enrich_ancestors: bool = True) -> Dict[str, Any]:
        """
        Get intelligent summary based on query filters.

        Automatically groups results based on the filters used in the query.
        For example, if you searched with multiple ancestor_names, results
        will be grouped by those ancestors.

        Args:
            enrich_ancestors: If True and ancestor filters were used,
                            fetch ancestor details for better grouping

        Returns:
            Dictionary with summary information including smart groupings
        """
        # Basic summary (always included)
        summary = {
            "total_count": len(self.places),
            "has_geometry": self.has_geometry,
            "metadata": self.metadata,
        }

        if self.is_empty:
            return summary

        # Get query filters if available
        filters = self.metadata.get("query_filters", {}) if self.metadata else {}

        # Always include basic type grouping
        summary["by_type"] = self._group_by_placetype()

        # Determine what dimensions to group by based on filters
        grouping_dims = self._determine_grouping_dimensions(filters)

        # Apply intelligent grouping based on detected dimensions
        if "ancestor" in grouping_dims and enrich_ancestors:
            ancestor_groups = self._group_by_ancestors(filters)
            if ancestor_groups:
                summary["by_ancestor"] = ancestor_groups

        if "parent" in grouping_dims and enrich_ancestors:
            parent_groups = self._group_by_parents(filters)
            if parent_groups:
                summary["by_parent"] = parent_groups

        if "country" in grouping_dims:
            summary["by_country"] = self._group_by_field("country")

        if "repo" in grouping_dims:
            summary["by_repo"] = self._group_by_field("repo")

        # Create nested groupings if multiple dimensions
        if len(grouping_dims) > 1:
            summary["nested_groups"] = self._create_nested_groups(
                grouping_dims, filters
            )

        # Add coverage report if filters had multiple values
        coverage = self._get_coverage_report(filters)
        if coverage:
            summary["coverage"] = coverage

        return summary

    def _determine_grouping_dimensions(self, filters: Dict[str, Any]) -> List[str]:
        """
        Determine which dimensions to group by based on the filters used.

        Returns:
            List of dimension names to group by
        """
        dimensions = []

        # Check for ancestor-based filters
        if filters.get("ancestor_name") or filters.get("ancestor_id"):
            # Always group by ancestors when they're used in the filter
            dimensions.append("ancestor")

        # Check for parent-based filters
        if filters.get("parent_name") or filters.get("parent_id"):
            if isinstance(filters.get("parent_name"), list) or isinstance(
                filters.get("parent_id"), list
            ):
                dimensions.append("parent")

        # Check for country filter with multiple values
        if isinstance(filters.get("country"), list) and len(filters["country"]) > 1:
            dimensions.append("country")

        # Check for repo filter with multiple values
        if isinstance(filters.get("repo"), list) and len(filters["repo"]) > 1:
            dimensions.append("repo")

        # Check for placetype with multiple values
        if isinstance(filters.get("placetype"), list) and len(filters["placetype"]) > 1:
            dimensions.append("placetype")

        return dimensions

    def _group_by_placetype(self) -> Dict[str, int]:
        """Group places by placetype."""
        groups: Dict[str, int] = {}
        for place in self.places:
            # Convert PlaceType enum to string for serialization
            pt = (
                place.placetype.value
                if hasattr(place.placetype, "value")
                else str(place.placetype)
            )
            groups[pt] = groups.get(pt, 0) + 1
        return groups

    def _group_by_field(self, field: str) -> Dict[str, int]:
        """Group places by a specific field."""
        groups: Dict[str, int] = {}
        for place in self.places:
            if hasattr(place, field):
                value = getattr(place, field)
                if value is not None:
                    groups[value] = groups.get(value, 0) + 1
        return groups

    def _group_by_ancestors(self, filters: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Group places by their ancestors, intelligently determining which ancestor level.

        For neighborhoods, groups by locality (city).
        For localities, groups by region (state).

        Note: This requires ancestor_data to be pre-fetched and stored in metadata.
        """
        # Check if we have pre-fetched ancestor data
        if not self.metadata or "ancestor_data" not in self.metadata:
            # Without ancestor data, we can't group properly
            # Return a simple message indicating enrichment is needed
            return {"_note": {"message": "Ancestor enrichment disabled or unavailable"}}

        ancestor_data = self.metadata["ancestor_data"]

        # Determine target ancestor level based on placetype
        placetypes = set()
        for place in self.places:
            # Convert enum to string for comparison
            pt = (
                place.placetype.value
                if hasattr(place.placetype, "value")
                else str(place.placetype)
            )
            placetypes.add(pt)

        # Determine the appropriate ancestor level to group by
        if (
            "neighbourhood" in placetypes
            or "borough" in placetypes
            or "macrohood" in placetypes
        ):
            target_level = "locality"
        elif "locality" in placetypes or "localadmin" in placetypes:
            target_level = "region"
        elif "region" in placetypes:
            target_level = "country"
        else:
            target_level = "parent"

        # Group by ancestors
        groups = {}
        for place in self.places:
            if place.id in ancestor_data:
                ancestors = ancestor_data[place.id]
                # Find the target level ancestor
                target_ancestor = None
                for ancestor in ancestors:
                    if ancestor.get("placetype") == target_level:
                        target_ancestor = ancestor
                        break

                if target_ancestor:
                    ancestor_name = target_ancestor["name"]
                    if ancestor_name not in groups:
                        groups[ancestor_name] = {
                            "count": 0,
                            "id": target_ancestor["id"],
                            "placetypes": {},
                        }
                    groups[ancestor_name]["count"] += 1
                    # Track placetype distribution (convert enum to string)
                    pt = (
                        place.placetype.value
                        if hasattr(place.placetype, "value")
                        else str(place.placetype)
                    )
                    groups[ancestor_name]["placetypes"][pt] = (
                        groups[ancestor_name]["placetypes"].get(pt, 0) + 1
                    )

        return groups

    def _group_by_parents(self, filters: Dict[str, Any]) -> Dict[str, int]:
        """Group places by their immediate parent."""
        # This would need parent name lookups, for now just group by parent_id
        groups: Dict[str, int] = {}
        for place in self.places:
            if place.parent_id:
                groups[str(place.parent_id)] = groups.get(str(place.parent_id), 0) + 1
        return groups

    def _create_nested_groups(
        self, dimensions: List[str], filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create nested groupings for multiple dimensions.
        """
        if not dimensions:
            return {}

        # For now, implement simple two-level nesting
        # This could be enhanced to support arbitrary nesting depth
        nested = {}

        # If we have ancestor and placetype dimensions
        if "ancestor" in dimensions and "placetype" in dimensions:
            # Group by ancestor first, then by placetype
            ancestor_groups = self._group_by_ancestors(filters)
            for ancestor_name, ancestor_data in ancestor_groups.items():
                if "placetypes" in ancestor_data:
                    nested[ancestor_name] = ancestor_data["placetypes"]

        # Add other combinations as needed

        return nested

    def _get_coverage_report(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a coverage report showing what was found vs what was requested.
        """
        report: Dict[str, Any] = {}

        # Check ancestor coverage
        if isinstance(filters.get("ancestor_name"), list):
            requested = filters["ancestor_name"]
            # This would need actual ancestor lookups to be fully accurate
            # For now, we can at least report the count
            report["ancestors_requested"] = len(requested)
            report["ancestors_query"] = requested

        # Check placetype coverage
        if isinstance(filters.get("placetype"), list):
            requested = set(filters["placetype"])
            found = set(self._group_by_placetype().keys())
            report["placetypes_requested"] = list(requested)
            report["placetypes_found"] = list(found)
            missing = requested - found
            if missing:
                report["placetypes_missing"] = list(missing)

        # Check country coverage
        if isinstance(filters.get("country"), list):
            requested = set(filters["country"])
            found = set(self._group_by_field("country").keys())
            report["countries_requested"] = list(requested)
            report["countries_found"] = list(found)
            missing = requested - found
            if missing:
                report["countries_missing"] = list(missing)

        return report

    def save_geojson(
        self,
        filepath: str,
        properties: Optional[List[str]] = None,
        use_polygons: bool = True,
        include_all_metadata: bool = False,
    ) -> None:
        """
        Save collection as GeoJSON file.

        Args:
            filepath: Path to save file
            properties: List of place attributes to include in feature properties.
                       Pass None for default set, empty list [] for no properties,
                       or specific field names to include.
                       Special value 'all' includes all available fields.
            use_polygons: If True, use polygon/multipolygon geometry when available.
                         If False, always use point geometry (lat/lon only).
            include_all_metadata: If True, include all available place fields in properties.
                                 Overrides properties list if set.
        """
        # Delegate to new serializer infrastructure
        from pathlib import Path
        from .serializers import SerializerRegistry

        serializer = SerializerRegistry.get("geojson")
        # Pass through options for forward compatibility
        options = {
            "properties": properties,
            "use_polygons": use_polygons,
            "include_all_metadata": include_all_metadata,
            "pretty": True,
            "indent": 2,
        }
        serializer.save(self.places, Path(filepath), **options)

    def save_csv(self, filepath: str) -> None:
        """
        Save collection as CSV file.

        Args:
            filepath: Path to save file
        """
        # Delegate to new serializer infrastructure
        from pathlib import Path
        from .serializers import SerializerRegistry

        serializer = SerializerRegistry.get("csv")
        serializer.save(self.places, Path(filepath))
