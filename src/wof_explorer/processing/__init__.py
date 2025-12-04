"""
Processing layer for WOF data.

This module provides cursors for lazy data loading and collections for
data manipulation and serialization.
"""

from wof_explorer.processing.cursors import (
    WOFSearchCursor,
    WOFHierarchyCursor,
    WOFBatchCursor,
)

from wof_explorer.processing.collections import PlaceCollection
from wof_explorer.processing.serializers import SerializerRegistry
from wof_explorer.processing.analysis import PlaceAnalyzer
from wof_explorer.processing.browser import PlaceBrowser

__all__ = [
    # Cursors
    "WOFSearchCursor",
    "WOFHierarchyCursor",
    "WOFBatchCursor",
    # Collections
    "PlaceCollection",
    # Serializers
    "SerializerRegistry",
    # Analysis & Browsing
    "PlaceAnalyzer",
    "PlaceBrowser",
]
