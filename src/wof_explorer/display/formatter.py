"""
Formatting utilities for consistent data presentation.

Provides formatters for numbers, sizes, durations, and WOF-specific data.
"""

from typing import Any, Optional, Union
from datetime import timedelta


def format_number(
    num: Union[int, float], decimals: int = 0, thousands_sep: str = ","
) -> str:
    """
    Format number with thousands separator.

    Args:
        num: Number to format
        decimals: Number of decimal places
        thousands_sep: Thousands separator character

    Example:
        >>> format_number(1234567)
        '1,234,567'
        >>> format_number(1234.567, decimals=2)
        '1,234.57'
    """
    if num is None:
        return ""

    if decimals > 0:
        formatted = f"{num:,.{decimals}f}"
    else:
        formatted = f"{int(num):,}"

    if thousands_sep != ",":
        formatted = formatted.replace(",", thousands_sep)

    return formatted


def format_count(count: int, singular: str, plural: Optional[str] = None) -> str:
    """
    Format count with singular/plural label.

    Args:
        count: Number of items
        singular: Singular form of label
        plural: Plural form (default: adds 's')

    Example:
        >>> format_count(1, 'place')
        '1 place'
        >>> format_count(5, 'city', 'cities')
        '5 cities'
    """
    if plural is None:
        plural = f"{singular}s"

    label = singular if count == 1 else plural
    return f"{format_number(count)} {label}"


def format_size(bytes: Union[int, float], precision: int = 2) -> str:
    """
    Format byte size in human-readable form.

    Args:
        bytes: Size in bytes
        precision: Decimal precision

    Example:
        >>> format_size(1024)
        '1.00 KB'
        >>> format_size(1234567890)
        '1.15 GB'
    """
    if bytes is None:
        return ""

    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(bytes) < 1024.0:
            return f"{bytes:.{precision}f} {unit}"
        bytes /= 1024.0

    return f"{bytes:.{precision}f} PB"


def format_duration(seconds: Union[int, float], short: bool = False) -> str:
    """
    Format duration in human-readable form.

    Args:
        seconds: Duration in seconds
        short: Use short format (1h 30m vs 1 hour 30 minutes)

    Example:
        >>> format_duration(90)
        '1 minute 30 seconds'
        >>> format_duration(3661, short=True)
        '1h 1m 1s'
    """
    if seconds is None:
        return ""

    td = timedelta(seconds=int(seconds))
    days = td.days
    hours = td.seconds // 3600
    minutes = (td.seconds % 3600) // 60
    seconds = td.seconds % 60

    parts = []

    if days > 0:
        if short:
            parts.append(f"{days}d")
        else:
            parts.append(format_count(days, "day"))

    if hours > 0:
        if short:
            parts.append(f"{hours}h")
        else:
            parts.append(format_count(hours, "hour"))

    if minutes > 0:
        if short:
            parts.append(f"{minutes}m")
        else:
            parts.append(format_count(minutes, "minute"))

    if seconds > 0 or not parts:
        if short:
            parts.append(f"{seconds}s")
        else:
            parts.append(format_count(seconds, "second"))

    return " ".join(parts) if not short else "".join(parts)


def format_percentage(value: float, total: float, decimals: int = 1) -> str:
    """
    Format percentage.

    Args:
        value: Current value
        total: Total value
        decimals: Decimal places

    Example:
        >>> format_percentage(25, 100)
        '25.0%'
        >>> format_percentage(1, 3, decimals=2)
        '33.33%'
    """
    if total == 0:
        return "0%"

    percentage = (value / total) * 100
    return f"{percentage:.{decimals}f}%"


def format_place(
    place: Any, include_type: bool = True, include_id: bool = False
) -> str:
    """
    Format WOF place for display.

    Args:
        place: WOF place object
        include_type: Include placetype
        include_id: Include place ID

    Example:
        >>> format_place(place)
        'San Francisco (locality)'
        >>> format_place(place, include_id=True)
        'San Francisco (locality) #85922583'
    """
    if place is None:
        return ""

    parts = []

    # Name
    name = getattr(place, "name", str(place))
    parts.append(name)

    # Placetype
    if include_type and hasattr(place, "placetype"):
        placetype = place.placetype
        if hasattr(placetype, "value"):
            placetype = placetype.value
        parts.append(f"({placetype})")

    # ID
    if include_id and hasattr(place, "id"):
        parts.append(f"#{place.id}")

    return " ".join(parts)


def format_bbox(bbox: Union[list, tuple], precision: int = 4) -> str:
    """
    Format bounding box coordinates.

    Args:
        bbox: [min_lon, min_lat, max_lon, max_lat]
        precision: Decimal precision

    Example:
        >>> format_bbox([-122.5, 37.7, -122.4, 37.8])
        '[-122.5000, 37.7000, -122.4000, 37.8000]'
    """
    if not bbox or len(bbox) != 4:
        return ""

    formatted = [f"{coord:.{precision}f}" for coord in bbox]
    return f"[{', '.join(formatted)}]"


def format_coordinates(lat: float, lon: float, precision: int = 6) -> str:
    """
    Format latitude/longitude coordinates.

    Args:
        lat: Latitude
        lon: Longitude
        precision: Decimal precision

    Example:
        >>> format_coordinates(37.7749, -122.4194)
        '37.774900, -122.419400'
    """
    if lat is None or lon is None:
        return ""

    return f"{lat:.{precision}f}, {lon:.{precision}f}"


def format_hierarchy_path(places: list, separator: str = " → ") -> str:
    """
    Format hierarchy as path string.

    Args:
        places: List of places from root to leaf
        separator: Path separator

    Example:
        >>> format_hierarchy_path([usa, california, sf])
        'United States → California → San Francisco'
    """
    if not places:
        return ""

    names = [getattr(p, "name", str(p)) for p in places]
    return separator.join(names)


def format_list(items: list, max_items: int = 5, separator: str = ", ") -> str:
    """
    Format list with truncation.

    Args:
        items: List of items
        max_items: Maximum items to show
        separator: Item separator

    Example:
        >>> format_list(['a', 'b', 'c', 'd', 'e', 'f'], max_items=3)
        'a, b, c, ... (3 more)'
    """
    if not items:
        return ""

    if len(items) <= max_items:
        return separator.join(str(item) for item in items)

    shown = items[:max_items]
    remaining = len(items) - max_items

    formatted = separator.join(str(item) for item in shown)
    return f"{formatted}, ... ({remaining} more)"


def format_status(place: Any) -> str:
    """
    Format place status indicators.

    Args:
        place: WOF place object

    Returns:
        Status string with symbols

    Example:
        >>> format_status(place)
        '✓ Current'
    """
    if not hasattr(place, "is_current"):
        return ""

    statuses = []

    if getattr(place, "is_current", False):
        statuses.append("✓ Current")
    if getattr(place, "is_deprecated", False):
        statuses.append("⚠ Deprecated")
    if getattr(place, "is_ceased", False):
        statuses.append("✗ Ceased")
    if getattr(place, "is_superseded", False):
        statuses.append("↻ Superseded")

    return " | ".join(statuses) if statuses else "? Unknown"


def format_diff(old_value: Any, new_value: Any, show_sign: bool = True) -> str:
    """
    Format difference between two values.

    Args:
        old_value: Previous value
        new_value: Current value
        show_sign: Show + or - sign

    Example:
        >>> format_diff(100, 150)
        '+50 (+50.0%)'
        >>> format_diff('old', 'new')
        'old → new'
    """
    try:
        # Try numeric diff
        old_num = float(old_value)
        new_num = float(new_value)
        diff = new_num - old_num
        percent = (diff / old_num * 100) if old_num != 0 else 0

        if show_sign and diff > 0:
            return f"+{diff:g} (+{percent:.1f}%)"
        else:
            return f"{diff:g} ({percent:.1f}%)"
    except Exception:
        # Non-numeric diff
        if old_value == new_value:
            return "unchanged"
        else:
            return f"{old_value} → {new_value}"
