"""
Tree display utilities for hierarchical data.

Provides multiple styles for displaying geographic hierarchies,
file structures, and nested relationships.
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class TreeStyle(Enum):
    """Available tree display styles."""

    ASCII = "ascii"  # Classic ASCII: +-- child
    UNICODE = "unicode"  # Modern Unicode: ├── child
    SIMPLE = "simple"  # Simple indents: - child
    ARROWS = "arrows"  # Arrow style: → child
    DOTS = "dots"  # Dotted lines: ... child
    EMOJI = "emoji"  # With emojis: 📁 parent


@dataclass
class TreeConfig:
    """Configuration for tree display."""

    style: TreeStyle = TreeStyle.UNICODE
    show_icons: bool = False
    max_depth: Optional[int] = None
    indent_size: int = 2
    show_count: bool = False
    color_enabled: bool = True
    compact: bool = False


class TreeDisplay:
    """
    Flexible tree display for hierarchical data.

    Examples:
        >>> tree = TreeDisplay(style=TreeStyle.UNICODE)
        >>> tree.add_node("United States")
        >>> tree.add_child("California")
        >>> tree.add_child("San Francisco", parent="California")
        >>> print(tree.render())
        United States
        └── California
            └── San Francisco
    """

    # Style definitions
    STYLES = {
        TreeStyle.ASCII: {
            "branch": "+-- ",
            "last": "\\-- ",
            "vertical": "|   ",
            "empty": "    ",
        },
        TreeStyle.UNICODE: {
            "branch": "├── ",
            "last": "└── ",
            "vertical": "│   ",
            "empty": "    ",
        },
        TreeStyle.SIMPLE: {
            "branch": "- ",
            "last": "- ",
            "vertical": "  ",
            "empty": "  ",
        },
        TreeStyle.ARROWS: {
            "branch": "→ ",
            "last": "→ ",
            "vertical": "  ",
            "empty": "  ",
        },
        TreeStyle.DOTS: {
            "branch": "... ",
            "last": "... ",
            "vertical": "    ",
            "empty": "    ",
        },
        TreeStyle.EMOJI: {
            "branch": "├─ ",
            "last": "└─ ",
            "vertical": "│  ",
            "empty": "   ",
        },
    }

    # Icon mappings for different types
    ICONS = {
        "country": "🌍",
        "region": "📍",
        "county": "🏛️",
        "locality": "🏙️",
        "neighbourhood": "🏘️",
        "building": "🏢",
        "folder": "📁",
        "file": "📄",
        "default": "•",
    }

    def __init__(self, config: Optional[TreeConfig] = None):
        """Initialize tree display with configuration."""
        self.config = config or TreeConfig()
        self.root: Optional[Dict[str, Any]] = None
        self.nodes: dict[str, dict[str, Any]] = {}

    def add_node(self, name: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Add root node."""
        self.root = {"name": name, "data": data or {}, "children": []}
        self.nodes[name] = self.root

    def add_child(
        self,
        name: str,
        parent: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add child node to parent."""
        parent_node = self.nodes.get(parent, self.root) if parent else self.root
        if not parent_node:
            raise ValueError("Parent node not found")

        child = {"name": name, "data": data or {}, "children": []}
        parent_node["children"].append(child)
        self.nodes[name] = child

    def render(self) -> str:
        """Render the tree to string."""
        if not self.root:
            return ""

        lines: List[str] = []
        self._render_node(self.root, lines, "", True, 0)
        return "\n".join(lines)

    def _render_node(
        self,
        node: Dict[str, Any],
        lines: List[str],
        prefix: str,
        is_last: bool,
        depth: int,
    ) -> None:
        """Recursively render node and its children."""
        if self.config.max_depth and depth > self.config.max_depth:
            return

        style = self.STYLES[self.config.style]

        # Build the line
        if depth == 0:
            # Root node
            icon = self._get_icon(node) if self.config.show_icons else ""
            count = f" ({len(node['children'])})" if self.config.show_count else ""
            lines.append(f"{icon}{node['name']}{count}")
        else:
            # Child node
            connector = style["last"] if is_last else style["branch"]
            icon = self._get_icon(node) if self.config.show_icons else ""
            count = f" ({len(node['children'])})" if self.config.show_count else ""
            lines.append(f"{prefix}{connector}{icon}{node['name']}{count}")

        # Render children
        if node["children"]:
            for i, child in enumerate(node["children"]):
                is_last_child = i == len(node["children"]) - 1
                if depth == 0:
                    child_prefix = ""
                else:
                    extension = style["empty"] if is_last else style["vertical"]
                    child_prefix = prefix + extension

                self._render_node(child, lines, child_prefix, is_last_child, depth + 1)

    def _get_icon(self, node: Dict[str, Any]) -> str:
        """Get icon for node based on type."""
        node_type = node["data"].get("type", "default")
        icon = self.ICONS.get(node_type, self.ICONS["default"])
        return f"{icon} " if icon else ""


def print_hierarchy(
    items: List[Dict[str, Any]],
    parent_key: str = "parent",
    name_key: str = "name",
    style: TreeStyle = TreeStyle.UNICODE,
    **kwargs,
) -> None:
    """
    Print items in hierarchical tree format.

    Args:
        items: List of items with parent relationships
        parent_key: Key that contains parent reference
        name_key: Key that contains item name
        style: Tree display style
        **kwargs: Additional TreeConfig options

    Example:
        >>> places = [
        ...     {'name': 'USA', 'parent': None},
        ...     {'name': 'California', 'parent': 'USA'},
        ...     {'name': 'San Francisco', 'parent': 'California'}
        ... ]
        >>> print_hierarchy(places)
        USA
        └── California
            └── San Francisco
    """
    config = TreeConfig(style=style, **kwargs)
    tree = TreeDisplay(config)

    # Build parent-child relationships
    by_parent: dict[Any, list[dict[str, Any]]] = {}
    roots = []

    for item in items:
        parent = item.get(parent_key)
        if parent is None:
            roots.append(item)
        else:
            if parent not in by_parent:
                by_parent[parent] = []
            by_parent[parent].append(item)

    # Build tree
    def add_children(parent_name: str, parent_item: Dict[str, Any]):
        children = by_parent.get(parent_item.get(name_key), [])
        for child in children:
            child_name = child.get(name_key)
            if child_name is not None:
                tree.add_child(str(child_name), parent=parent_name, data=child)
                add_children(str(child_name), child)

    # Add roots and their children
    for root in roots:
        root_name = root.get(name_key)
        if root_name is not None:
            tree.add_node(str(root_name), data=root)
            add_children(str(root_name), root)

    print(tree.render())


def print_tree(
    root_name: str,
    get_children: Callable[[str], List[str]],
    style: TreeStyle = TreeStyle.UNICODE,
    max_depth: Optional[int] = None,
    show_count: bool = True,
) -> None:
    """
    Print tree using a function to get children.

    Args:
        root_name: Name of root node
        get_children: Function that returns children for a node
        style: Tree display style
        max_depth: Maximum depth to display
        show_count: Show child count

    Example:
        >>> def get_children(name):
        ...     if name == "root":
        ...         return ["child1", "child2"]
        ...     return []
        >>> print_tree("root", get_children)
        root (2)
        ├── child1
        └── child2
    """
    config = TreeConfig(style=style, max_depth=max_depth, show_count=show_count)
    tree = TreeDisplay(config)

    def build_tree(name: str, parent: Optional[str] = None, depth: int = 0):
        if max_depth and depth > max_depth:
            return

        if parent is None:
            tree.add_node(name)
        else:
            tree.add_child(name, parent=parent)

        children = get_children(name)
        for child in children:
            build_tree(child, parent=name, depth=depth + 1)

    build_tree(root_name)
    print(tree.render())


# Convenience functions for WOF-specific displays


def print_wof_hierarchy(
    places: List[Any], style: TreeStyle = TreeStyle.UNICODE
) -> None:
    """
    Print WOF place hierarchy with appropriate icons.

    Example:
        >>> print_wof_hierarchy(ancestors)
        🌍 United States
        └── 📍 California
            └── 🏙️ San Francisco
                └── 🏘️ Mission District
    """
    config = TreeConfig(style=style, show_icons=True)
    tree = TreeDisplay(config)

    if not places:
        return

    # Assume places are ordered from root to leaf
    for i, place in enumerate(places):
        name = getattr(place, "name", str(place))
        placetype = getattr(place, "placetype", "default")

        data = {"type": str(placetype).lower()}

        if i == 0:
            tree.add_node(name, data=data)
            parent = name
        else:
            tree.add_child(name, parent=parent, data=data)
            parent = name

    print(tree.render())


def print_ancestors_tree(ancestors: List[Any], reverse: bool = False) -> None:
    """
    Print ancestor hierarchy in tree format.

    Args:
        ancestors: List of ancestor places
        reverse: If True, show from child to root

    Example:
        >>> print_ancestors_tree(ancestors)
        └─ San Francisco County (county)
          └─ California (region)
            └─ United States (country)
    """
    if reverse:
        ancestors = list(reversed(ancestors))

    for i, ancestor in enumerate(ancestors):
        indent = "  " * i
        connector = "└─" if i == 0 else "└─"
        name = getattr(ancestor, "name", str(ancestor))
        placetype = getattr(ancestor, "placetype", "")
        print(f"{indent}{connector} {name} ({placetype})")


def print_descendants_tree(
    root_name: str, descendants: List[Any], group_by: Optional[str] = "placetype"
) -> None:
    """
    Print descendants in tree format, optionally grouped.

    Args:
        root_name: Name of root place
        descendants: List of descendant places
        group_by: Optional grouping field

    Example:
        >>> print_descendants_tree("San Francisco", neighborhoods)
        San Francisco (48)
        ├── neighbourhood (45)
        │   ├── Mission District
        │   ├── Castro
        │   └── ...
        └── locality (3)
            ├── Treasure Island
            └── ...
    """
    config = TreeConfig(show_count=True)
    tree = TreeDisplay(config)

    tree.add_node(root_name)

    if group_by:
        # Group descendants
        groups: dict[str, list[Any]] = {}
        for desc in descendants:
            key = getattr(desc, group_by, "other")
            if key not in groups:
                groups[key] = []
            groups[key].append(desc)

        # Add groups to tree
        for group_name, items in groups.items():
            tree.add_child(f"{group_name} ({len(items)})", parent=root_name)
            for item in items[:3]:  # Show first 3
                name = getattr(item, "name", str(item))
                tree.add_child(name, parent=f"{group_name} ({len(items)})")
            if len(items) > 3:
                tree.add_child("...", parent=f"{group_name} ({len(items)})")
    else:
        # Add all descendants flat
        for desc in descendants:
            name = getattr(desc, "name", str(desc))
            tree.add_child(name, parent=root_name)

    print(tree.render())
