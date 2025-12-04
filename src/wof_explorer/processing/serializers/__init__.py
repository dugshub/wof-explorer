"""
Serializer package and registry for output formats.

Provides a central registry to look up serializers by format name
(e.g., 'geojson', 'csv', 'wkt'). Concrete serializers register
themselves on import.
"""

from wof_explorer.processing.serializers.base import SerializerBase, SerializerRegistry

# Import concrete serializers to trigger self-registration
from wof_explorer.processing.serializers import geojson as _geojson  # noqa: F401
from wof_explorer.processing.serializers import csv as _csv  # noqa: F401
from wof_explorer.processing.serializers import wkt as _wkt  # noqa: F401

__all__ = [
    "SerializerBase",
    "SerializerRegistry",
]
