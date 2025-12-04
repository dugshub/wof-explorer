"""
Table display utilities for structured data.

Provides flexible table formatting for search results, summaries,
and comparisons.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class TableStyle(Enum):
    """Available table display styles."""

    SIMPLE = "simple"  # No borders
    ASCII = "ascii"  # ASCII borders: +--+
    UNICODE = "unicode"  # Unicode borders: ┌──┐
    MARKDOWN = "markdown"  # Markdown format: | col |
    MINIMAL = "minimal"  # Minimal separators


@dataclass
class TableConfig:
    """Configuration for table display."""

    style: TableStyle = TableStyle.SIMPLE
    max_width: Optional[int] = None
    show_headers: bool = True
    show_index: bool = False
    align: Optional[Dict[str, str]] = None  # left, right, center
    truncate: int = 50
    color_enabled: bool = True


class TableDisplay:
    """
    Flexible table display for structured data.

    Example:
        >>> table = TableDisplay(["Name", "Type", "Population"])
        >>> table.add_row(["San Francisco", "locality", "873,965"])
        >>> table.add_row(["Oakland", "locality", "433,031"])
        >>> print(table.render())
        Name           Type      Population
        San Francisco  locality  873,965
        Oakland        locality  433,031
    """

    STYLES = {
        TableStyle.SIMPLE: {
            "top": "",
            "bottom": "",
            "header": "-",
            "row": " ",
            "left": "",
            "right": "",
            "cross": " ",
        },
        TableStyle.ASCII: {
            "top": "-",
            "bottom": "-",
            "header": "-",
            "row": "|",
            "left": "|",
            "right": "|",
            "cross": "+",
        },
        TableStyle.UNICODE: {
            "top": "─",
            "bottom": "─",
            "header": "─",
            "row": "│",
            "left": "│",
            "right": "│",
            "cross": "┼",
        },
        TableStyle.MARKDOWN: {
            "top": "",
            "bottom": "",
            "header": "-",
            "row": "|",
            "left": "|",
            "right": "|",
            "cross": "|",
        },
        TableStyle.MINIMAL: {
            "top": "",
            "bottom": "",
            "header": "",
            "row": "  ",
            "left": "",
            "right": "",
            "cross": "  ",
        },
    }

    def __init__(self, headers: List[str], config: Optional[TableConfig] = None):
        """Initialize table with headers."""
        self.headers = headers
        self.config = config or TableConfig()
        self.rows: list[list[str]] = []
        self.column_widths = [len(h) for h in headers]

    def add_row(self, row: List[Any]) -> None:
        """Add a row to the table."""
        str_row = [str(v) if v is not None else "" for v in row]
        self.rows.append(str_row)

        # Update column widths
        for i, val in enumerate(str_row):
            if i < len(self.column_widths):
                self.column_widths[i] = max(self.column_widths[i], len(val))

    def add_rows(self, rows: List[List[Any]]) -> None:
        """Add multiple rows."""
        for row in rows:
            self.add_row(row)

    def render(self) -> str:
        """Render the table to string."""
        style = self.STYLES[self.config.style]
        lines = []

        # Top border
        if style["top"]:
            lines.append(self._make_border(style["top"], style["cross"]))

        # Headers
        if self.config.show_headers:
            lines.append(self._make_row(self.headers, style))

            # Header separator
            if style["header"]:
                lines.append(self._make_border(style["header"], style["cross"]))

        # Rows
        for i, row in enumerate(self.rows):
            if self.config.show_index:
                row = [str(i)] + row
            lines.append(self._make_row(row, style))

        # Bottom border
        if style["bottom"]:
            lines.append(self._make_border(style["bottom"], style["cross"]))

        return "\n".join(lines)

    def _make_row(self, row: List[str], style: Dict[str, str]) -> str:
        """Create a formatted row."""
        parts = []

        if style["left"]:
            parts.append(style["left"])

        for i, (val, width) in enumerate(zip(row, self.column_widths)):
            # Truncate if needed
            if self.config.truncate and len(val) > self.config.truncate:
                val = val[: self.config.truncate - 3] + "..."

            # Apply alignment
            align = "left"
            if self.config.align and i < len(self.headers):
                align = self.config.align.get(self.headers[i], "left")

            if align == "right":
                formatted = val.rjust(width)
            elif align == "center":
                formatted = val.center(width)
            else:
                formatted = val.ljust(width)

            parts.append(formatted)

            if i < len(row) - 1:
                parts.append(style["row"])

        if style["right"]:
            parts.append(style["right"])

        return "".join(parts)

    def _make_border(self, char: str, cross: str) -> str:
        """Create a border line."""
        parts = []

        if self.STYLES[self.config.style]["left"]:
            parts.append(cross)

        for i, width in enumerate(self.column_widths):
            parts.append(char * width)
            if i < len(self.column_widths) - 1:
                parts.append(cross)

        if self.STYLES[self.config.style]["right"]:
            parts.append(cross)

        return "".join(parts)


def print_table(
    data: List[Dict[str, Any]],
    columns: Optional[List[str]] = None,
    style: TableStyle = TableStyle.SIMPLE,
    **kwargs,
) -> None:
    """
    Print list of dictionaries as a table.

    Args:
        data: List of dictionaries to display
        columns: Column names to display (default: all keys)
        style: Table display style
        **kwargs: Additional TableConfig options

    Example:
        >>> places = [
        ...     {'name': 'SF', 'type': 'city', 'pop': 873965},
        ...     {'name': 'LA', 'type': 'city', 'pop': 3898747}
        ... ]
        >>> print_table(places, columns=['name', 'pop'])
        name  pop
        SF    873965
        LA    3898747
    """
    if not data:
        print("No data to display")
        return

    # Determine columns
    if columns is None:
        columns = list(data[0].keys())

    config = TableConfig(style=style, **kwargs)
    table = TableDisplay(columns, config)

    # Add rows
    for item in data:
        row = [item.get(col, "") for col in columns]
        table.add_row(row)

    print(table.render())


def print_summary(
    title: str, stats: Dict[str, Any], style: TableStyle = TableStyle.SIMPLE
) -> None:
    """
    Print a summary table with key-value pairs.

    Args:
        title: Summary title
        stats: Dictionary of statistics
        style: Table display style

    Example:
        >>> stats = {
        ...     'Total Places': 1234,
        ...     'Countries': 3,
        ...     'Regions': 50
        ... }
        >>> print_summary("Database Summary", stats)
        Database Summary
        ----------------
        Total Places  1234
        Countries     3
        Regions       50
    """
    print(title)
    print("-" * len(title))

    config = TableConfig(style=style, show_headers=False)
    table = TableDisplay(["Key", "Value"], config)

    for key, value in stats.items():
        table.add_row([key, value])

    print(table.render())


def print_comparison(
    left_data: Dict[str, Any],
    right_data: Dict[str, Any],
    left_label: str = "Before",
    right_label: str = "After",
    show_diff: bool = True,
) -> None:
    """
    Print side-by-side comparison table.

    Args:
        left_data: First dataset
        right_data: Second dataset
        left_label: Label for left column
        right_label: Label for right column
        show_diff: Show difference column

    Example:
        >>> before = {'count': 100, 'size': '10MB'}
        >>> after = {'count': 150, 'size': '15MB'}
        >>> print_comparison(before, after)
        Metric  Before  After  Change
        count   100     150    +50
        size    10MB    15MB   +5MB
    """
    # Get all keys
    all_keys = set(left_data.keys()) | set(right_data.keys())

    headers = ["Metric", left_label, right_label]
    if show_diff:
        headers.append("Change")

    table = TableDisplay(headers)

    for key in sorted(all_keys):
        left_val = left_data.get(key, "")
        right_val = right_data.get(key, "")

        row = [key, left_val, right_val]

        if show_diff:
            # Try to calculate difference
            diff = _calculate_diff(left_val, right_val)
            row.append(diff)

        table.add_row(row)

    print(table.render())


def _calculate_diff(left: Any, right: Any) -> str:
    """Calculate difference between two values."""
    try:
        # Try numeric comparison
        left_num = float(str(left).replace(",", "").replace("MB", "").replace("KB", ""))
        right_num = float(
            str(right).replace(",", "").replace("MB", "").replace("KB", "")
        )
        diff = right_num - left_num

        if diff > 0:
            return f"+{diff:g}"
        elif diff < 0:
            return f"{diff:g}"
        else:
            return "="
    except Exception:
        # Non-numeric comparison
        if left == right:
            return "="
        else:
            return "changed"


def print_places_table(
    places: List[Any], columns: Optional[List[str]] = None, max_rows: int = 20
) -> None:
    """
    Print WOF places in table format.

    Args:
        places: List of WOF place objects
        columns: Columns to display (default: sensible subset)
        max_rows: Maximum rows to display

    Example:
        >>> print_places_table(cursor.places)
        ID        Name           Type          Country  Current
        85922583  San Francisco  locality      US       ✓
        85688637  Oakland        locality      US       ✓
    """
    if not places:
        print("No places to display")
        return

    # Default columns if not specified
    if columns is None:
        columns = ["id", "name", "placetype", "country", "is_current"]

    # Convert places to dictionaries
    data = []
    for place in places[:max_rows]:
        row = {}
        for col in columns:
            val = getattr(place, col, None)

            # Format special values
            if col == "is_current" and val:
                val = "✓" if val else "✗"
            elif col == "placetype" and val is not None and hasattr(val, "value"):
                val = val.value

            row[col] = val

        data.append(row)

    # Print table
    print_table(data, columns=columns)

    if len(places) > max_rows:
        print(f"\n... and {len(places) - max_rows} more rows")
