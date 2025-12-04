"""
Display classes for different object types.

Provides specialized display implementations for cursors, collections,
and other WOF objects.
"""

from typing import Optional, List, Any
from abc import ABC, abstractmethod


class BaseDisplay(ABC):
    """Base display wrapper providing multiple output formats."""

    def __init__(self, obj):
        """
        Initialize display with the object to display.

        Args:
            obj: The object to create displays for
        """
        self.obj = obj

    # Quick access properties (no params)
    @property
    def tree(self) -> str:
        """Quick tree representation."""
        return self.as_tree()

    @property
    def table(self) -> str:
        """Quick table representation."""
        return self.as_table()

    @property
    def summary(self) -> str:
        """Quick summary representation."""
        return self.as_summary()

    # Configurable methods
    def as_tree(
        self,
        style: str = "unicode",
        max_depth: Optional[int] = None,
        show_count: bool = True,
        **kwargs,
    ) -> str:
        """
        Generate tree representation with options.

        Args:
            style: Tree style ('unicode', 'ascii', 'simple')
            max_depth: Maximum depth to display
            show_count: Whether to show counts
            **kwargs: Additional options

        Returns:
            Tree representation as string
        """
        return self._render_tree(
            style=style, max_depth=max_depth, show_count=show_count, **kwargs
        )

    def as_table(
        self,
        columns: Optional[List[str]] = None,
        max_rows: int = 20,
        style: str = "simple",
        **kwargs,
    ) -> str:
        """
        Generate table representation with options.

        Args:
            columns: Columns to display
            max_rows: Maximum rows to show
            style: Table style
            **kwargs: Additional options

        Returns:
            Table representation as string
        """
        return self._render_table(
            columns=columns, max_rows=max_rows, style=style, **kwargs
        )

    def as_summary(self, **kwargs) -> str:
        """
        Generate summary representation.

        Args:
            **kwargs: Additional options

        Returns:
            Summary as string
        """
        return self._render_summary(**kwargs)

    # Convenience methods
    def print(self, format: str = "auto", **kwargs):
        """
        Print immediately with smart format selection.

        Args:
            format: Output format ('auto', 'tree', 'table', 'summary')
            **kwargs: Format-specific options
        """
        output = self._get_format(format, **kwargs)
        print(output)

    def __str__(self):
        """Default string representation."""
        return self._auto_format()

    # Protected methods to override in subclasses
    @abstractmethod
    def _render_tree(self, **kwargs) -> str:
        """Render as tree (must be implemented by subclasses)."""
        pass

    @abstractmethod
    def _render_table(self, **kwargs) -> str:
        """Render as table (must be implemented by subclasses)."""
        pass

    @abstractmethod
    def _render_summary(self, **kwargs) -> str:
        """Render as summary (must be implemented by subclasses)."""
        pass

    def _auto_format(self) -> str:
        """
        Smart format selection based on content.

        Override in subclasses for custom logic.
        """
        # Default logic
        if hasattr(self.obj, "__len__"):
            count = len(self.obj)
            if count > 20:
                return self.table
            elif count > 0:
                return self.tree
        return self.summary

    def _get_format(self, format: str, **kwargs) -> str:
        """
        Get specified format or auto-select.

        Args:
            format: Desired format
            **kwargs: Format-specific options

        Returns:
            Formatted string
        """
        if format == "auto":
            return self._auto_format()
        elif format == "tree":
            return self.as_tree(**kwargs)
        elif format == "table":
            return self.as_table(**kwargs)
        elif format == "summary":
            return self.as_summary(**kwargs)
        else:
            raise ValueError(f"Unknown format: {format}")


class CursorDisplay(BaseDisplay):
    """Display for search/batch cursors."""

    def _render_tree(
        self,
        style: str = "unicode",
        max_depth: Optional[int] = None,
        show_count: bool = True,
        **kwargs,
    ) -> str:
        """Render cursor as tree."""
        from .tree import TreeDisplay, TreeStyle

        tree = TreeDisplay()
        tree.config.style = TreeStyle[style.upper()]
        tree.config.show_count = show_count
        tree.config.max_depth = max_depth

        # Build cursor tree
        total = len(self.obj.places) if hasattr(self.obj, "places") else 0
        tree.add_node(f"Search Results ({total} total)")

        if hasattr(self.obj, "places") and self.obj.places:
            # Group by placetype
            by_type: dict[str, list[Any]] = {}
            for place in self.obj.places:
                ptype = str(getattr(place, "placetype", "unknown"))
                if ptype not in by_type:
                    by_type[ptype] = []
                by_type[ptype].append(place)

            for ptype, places in by_type.items():
                type_node = f"{ptype} ({len(places)})"
                tree.add_child(type_node, parent=f"Search Results ({total} total)")

                # Show first few of each type
                for place in places[:3]:
                    name = getattr(place, "name", str(place))
                    tree.add_child(name, parent=type_node)
                if len(places) > 3:
                    tree.add_child(f"... {len(places) - 3} more", parent=type_node)

        return tree.render()

    def _render_table(
        self, columns: Optional[List[str]] = None, max_rows: int = 20, **kwargs
    ) -> str:
        """Render cursor as table."""
        if not hasattr(self.obj, "places") or not self.obj.places:
            return "No results to display"

        from .table import TableDisplay

        # Default columns
        if columns is None:
            columns = ["id", "name", "placetype", "country", "is_current"]

        # Filter columns to those that exist
        first_place = self.obj.places[0]
        valid_columns = [col for col in columns if hasattr(first_place, col)]

        table = TableDisplay(valid_columns)

        # Add rows
        for i, place in enumerate(self.obj.places):
            if i >= max_rows:
                break

            row = []
            for col in valid_columns:
                val = getattr(place, col, "")
                # Format special values
                if col == "is_current" and val:
                    val = "✓" if val else "✗"
                elif hasattr(val, "value"):  # Enum
                    val = val.value
                row.append(val)

            table.add_row(row)

        result = table.render()

        if len(self.obj.places) > max_rows:
            result += f"\n... and {len(self.obj.places) - max_rows} more rows"

        return result

    def _render_summary(self, **kwargs) -> str:
        """Render cursor summary."""
        lines = ["Search Results Summary", "=" * 30]

        if hasattr(self.obj, "places"):
            total = len(self.obj.places)
            lines.append(f"Total Results: {total}")

            if total > 0:
                # Count by placetype
                by_type: dict[str, int] = {}
                for place in self.obj.places:
                    ptype = str(getattr(place, "placetype", "unknown"))
                    by_type[ptype] = by_type.get(ptype, 0) + 1

                lines.append(f"Place Types: {len(by_type)}")

                # Count current places
                current = sum(
                    1 for p in self.obj.places if getattr(p, "is_current", False)
                )
                lines.append(f"Current Places: {current}")

        # Add query filters if available
        if hasattr(self.obj, "query_filters"):
            filters = self.obj.query_filters
            if filters:
                lines.append(f"Filters Applied: {len(filters)}")

        return "\n".join(lines)


class HierarchyDisplay(BaseDisplay):
    """Display for hierarchy cursors."""

    def _render_tree(
        self, style: str = "unicode", show_icons: bool = False, **kwargs
    ) -> str:
        """Render hierarchy as tree."""
        lines = []

        # Get root place name
        root_name = "Unknown"
        if hasattr(self.obj, "_root"):
            root_name = getattr(self.obj._root, "name", str(self.obj._root))

        lines.append(f"Hierarchy: {root_name}")

        # Check for cached ancestors
        if hasattr(self.obj, "_ancestors_cache") and self.obj._ancestors_cache:
            # Build tree representation
            style_chars = {
                "unicode": ("└──", "├──", "│  "),
                "ascii": ("\\--", "+--", "|  "),
                "simple": ("- ", "- ", "  "),
            }

            chars = style_chars.get(style.lower(), style_chars["unicode"])

            for i, ancestor in enumerate(self.obj._ancestors_cache):
                indent = "  " * (i + 1)
                name = getattr(ancestor, "name", str(ancestor))
                ptype = getattr(ancestor, "placetype", "")
                lines.append(f"{indent}{chars[0]} {name} ({ptype})")

            # Add the root at the end
            indent = "  " * (len(self.obj._ancestors_cache) + 1)
            lines.append(f"{indent}{chars[0]} {root_name} (current)")
        else:
            lines.append("  (call fetch_ancestors() to load hierarchy)")

        return "\n".join(lines)

    def _render_table(self, **kwargs) -> str:
        """Hierarchies don't make good tables, show tree instead."""
        return self._render_tree(**kwargs)

    def _render_summary(self, **kwargs) -> str:
        """Render hierarchy summary."""
        lines = ["Hierarchy Summary", "=" * 30]

        if hasattr(self.obj, "_root"):
            root = self.obj._root
            lines.append(f"Root: {getattr(root, 'name', 'Unknown')}")
            lines.append(f"Type: {getattr(root, 'placetype', 'Unknown')}")
            lines.append(f"ID: {getattr(root, 'id', 'Unknown')}")

        if hasattr(self.obj, "_ancestors_cache") and self.obj._ancestors_cache:
            lines.append(f"Ancestors: {len(self.obj._ancestors_cache)}")
        else:
            lines.append("Ancestors: Not loaded")

        return "\n".join(lines)

    def _auto_format(self) -> str:
        """Hierarchies always show as trees."""
        return self.tree


class CollectionDisplay(BaseDisplay):
    """Display for PlaceCollections."""

    def _render_tree(
        self, group_by: str = "placetype", max_items: int = 5, **kwargs
    ) -> str:
        """Render collection as tree."""
        from .tree import TreeDisplay

        tree = TreeDisplay()

        total = len(self.obj.places) if hasattr(self.obj, "places") else 0
        tree.add_node(f"Collection ({total} places)")

        if hasattr(self.obj, "places") and self.obj.places and group_by:
            # Try to group places
            groups: dict[str, list[Any]] = {}
            for place in self.obj.places:
                if hasattr(place, group_by):
                    key = str(getattr(place, group_by))
                else:
                    key = "other"
                if key not in groups:
                    groups[key] = []
                groups[key].append(place)

            for group, places in groups.items():
                group_node = f"{group} ({len(places)})"
                tree.add_child(group_node, parent=f"Collection ({total} places)")
                for place in places[:max_items]:
                    name = getattr(place, "name", str(place))
                    tree.add_child(name, parent=group_node)
                if len(places) > max_items:
                    tree.add_child(
                        f"... {len(places) - max_items} more", parent=group_node
                    )
        elif hasattr(self.obj, "places"):
            # Flat list
            for place in self.obj.places[:10]:
                name = getattr(place, "name", str(place))
                ptype = getattr(place, "placetype", "")
                tree.add_child(
                    f"{name} ({ptype})", parent=f"Collection ({total} places)"
                )
            if total > 10:
                tree.add_child(
                    f"... {total - 10} more", parent=f"Collection ({total} places)"
                )

        return tree.render()

    def _render_table(
        self, columns: Optional[List[str]] = None, max_rows: int = 20, **kwargs
    ) -> str:
        """Render collection as table."""
        if not hasattr(self.obj, "places") or not self.obj.places:
            return "Empty collection"

        # Use cursor display's table method
        cursor_display = CursorDisplay(self.obj)
        return cursor_display._render_table(
            columns=columns, max_rows=max_rows, **kwargs
        )

    def _render_summary(self, **kwargs) -> str:
        """Render collection summary."""
        # Use existing get_summary if available
        if hasattr(self.obj, "get_summary"):
            try:
                summary_dict = self.obj.get_summary()
                lines = ["Collection Summary", "=" * 30]
                for key, value in summary_dict.items():
                    if isinstance(value, dict):
                        lines.append(f"\n{key}:")
                        for k, v in value.items():
                            lines.append(f"  {k}: {v}")
                    else:
                        lines.append(f"{key}: {value}")
                return "\n".join(lines)
            except Exception:
                pass

        # Fallback summary
        lines = ["Collection Summary", "=" * 30]
        if hasattr(self.obj, "places"):
            lines.append(f"Total Places: {len(self.obj.places)}")
        if hasattr(self.obj, "metadata"):
            lines.append("Has Metadata: Yes")

        return "\n".join(lines)


class BatchDisplay(CursorDisplay):
    """Display for batch cursors (similar to search cursors)."""

    def _render_summary(self, **kwargs) -> str:
        """Render batch summary."""
        lines = ["Batch Cursor Summary", "=" * 30]

        if hasattr(self.obj, "place_ids"):
            lines.append(f"Place IDs: {len(self.obj.place_ids)}")
        if hasattr(self.obj, "count"):
            lines.append(f"Count: {self.obj.count}")

        return "\n".join(lines)


class GenericDisplay(BaseDisplay):
    """Generic display for unknown object types."""

    def _render_tree(self, **kwargs) -> str:
        """Generic tree representation."""
        return f"Tree view not available for {type(self.obj).__name__}"

    def _render_table(self, **kwargs) -> str:
        """Generic table representation."""
        return f"Table view not available for {type(self.obj).__name__}"

    def _render_summary(self, **kwargs) -> str:
        """Generic summary."""
        lines = [f"{type(self.obj).__name__} Summary", "=" * 30]

        # Try to extract some info
        if hasattr(self.obj, "__len__"):
            lines.append(f"Length: {len(self.obj)}")
        if hasattr(self.obj, "__dict__"):
            attrs = [k for k in self.obj.__dict__ if not k.startswith("_")]
            lines.append(f"Attributes: {', '.join(attrs[:5])}")
            if len(attrs) > 5:
                lines.append(f"  ... and {len(attrs) - 5} more")

        return "\n".join(lines)
