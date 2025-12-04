"""
Display utilities for beautiful terminal output.

This module provides consistent formatting for various data presentations
including trees, tables, progress indicators, and summaries.
"""

from .descriptor import DisplayDescriptor
from .displays import BaseDisplay
from .tree import TreeDisplay, print_hierarchy, print_tree
from .table import (
    TableDisplay,
    TableConfig,
    TableStyle,
    print_table,
    print_summary,
    print_comparison,
)
from .progress import ProgressDisplay, print_progress
from .styles import DisplayTheme, get_theme, set_theme
from .formatter import (
    format_place,
    format_count,
    format_size,
    format_duration,
    format_percentage,
)

__all__ = [
    # Core display APIs
    "DisplayDescriptor",
    "BaseDisplay",
    # Tree displays
    "TreeDisplay",
    "print_hierarchy",
    "print_tree",
    # Table displays
    "TableDisplay",
    "TableConfig",
    "TableStyle",
    "print_table",
    "print_summary",
    "print_comparison",
    # Progress displays
    "ProgressDisplay",
    "print_progress",
    # Theming
    "DisplayTheme",
    "get_theme",
    "set_theme",
    # Formatters
    "format_place",
    "format_count",
    "format_size",
    "format_duration",
    "format_percentage",
]
