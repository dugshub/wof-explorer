"""
Display themes and styling configuration.

Provides consistent theming across all display utilities.
"""

from dataclasses import dataclass
from typing import Union, Optional
from enum import Enum


class ColorScheme(Enum):
    """Available color schemes."""

    DEFAULT = "default"
    MINIMAL = "minimal"
    COLORFUL = "colorful"
    MONOCHROME = "monochrome"


@dataclass
class DisplayTheme:
    """
    Theme configuration for display utilities.

    Controls colors, symbols, and formatting across all display modules.
    """

    # Color scheme
    color_scheme: ColorScheme = ColorScheme.DEFAULT

    # Tree display
    tree_branch: str = "├── "
    tree_last: str = "└── "
    tree_vertical: str = "│   "
    tree_empty: str = "    "

    # Icons
    icon_country: str = "🌍"
    icon_region: str = "📍"
    icon_county: str = "🏛️"
    icon_locality: str = "🏙️"
    icon_neighbourhood: str = "🏘️"
    icon_building: str = "🏢"
    icon_success: str = "✓"
    icon_error: str = "✗"
    icon_warning: str = "⚠"
    icon_info: str = "ℹ"
    icon_folder: str = "📁"
    icon_file: str = "📄"

    # Progress indicators
    progress_bar_fill: str = "="
    progress_bar_empty: str = " "
    progress_bar_head: str = ">"
    spinner_frames: Optional[list[str]] = None

    # Table borders
    table_horizontal: str = "─"
    table_vertical: str = "│"
    table_corner_tl: str = "┌"
    table_corner_tr: str = "┐"
    table_corner_bl: str = "└"
    table_corner_br: str = "┘"
    table_cross: str = "┼"

    # Colors (ANSI codes)
    color_header: str = "\033[1m"  # Bold
    color_success: str = "\033[32m"  # Green
    color_error: str = "\033[31m"  # Red
    color_warning: str = "\033[33m"  # Yellow
    color_info: str = "\033[34m"  # Blue
    color_muted: str = "\033[90m"  # Gray
    color_reset: str = "\033[0m"  # Reset

    def __post_init__(self):
        """Initialize spinner frames if not provided."""
        if self.spinner_frames is None:
            self.spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


# Predefined themes
THEMES = {
    "default": DisplayTheme(),
    "minimal": DisplayTheme(
        color_scheme=ColorScheme.MINIMAL,
        tree_branch="- ",
        tree_last="- ",
        tree_vertical="  ",
        tree_empty="  ",
        icon_country="[C]",
        icon_region="[R]",
        icon_locality="[L]",
        icon_neighbourhood="[N]",
        icon_success="[OK]",
        icon_error="[ERR]",
        icon_warning="[!]",
        table_horizontal="-",
        table_vertical="|",
        table_corner_tl="+",
        table_corner_tr="+",
        table_corner_bl="+",
        table_corner_br="+",
        table_cross="+",
    ),
    "ascii": DisplayTheme(
        color_scheme=ColorScheme.MONOCHROME,
        tree_branch="+-- ",
        tree_last="\\-- ",
        tree_vertical="|   ",
        tree_empty="    ",
        icon_country="[COUNTRY]",
        icon_region="[REGION]",
        icon_locality="[CITY]",
        icon_neighbourhood="[AREA]",
        icon_success="[✓]",
        icon_error="[X]",
        icon_warning="[!]",
        table_horizontal="-",
        table_vertical="|",
        table_corner_tl="+",
        table_corner_tr="+",
        table_corner_bl="+",
        table_corner_br="+",
        table_cross="+",
        spinner_frames=["-", "\\", "|", "/"],
    ),
    "colorful": DisplayTheme(
        color_scheme=ColorScheme.COLORFUL,
        # Uses default symbols but with more colors
        color_header="\033[1;35m",  # Bold Magenta
        color_success="\033[1;32m",  # Bold Green
        color_error="\033[1;31m",  # Bold Red
        color_warning="\033[1;33m",  # Bold Yellow
        color_info="\033[1;36m",  # Bold Cyan
        color_muted="\033[2;37m",  # Dim White
    ),
}

# Global theme
_current_theme = THEMES["default"]


def get_theme() -> DisplayTheme:
    """Get the current display theme."""
    return _current_theme


def set_theme(theme: Union[str, DisplayTheme]) -> None:
    """
    Set the display theme.

    Args:
        theme: Theme name or DisplayTheme object

    Example:
        >>> set_theme('minimal')
        >>> set_theme(DisplayTheme(icon_success='✅'))
    """
    global _current_theme

    if isinstance(theme, str):
        if theme not in THEMES:
            raise ValueError(
                f"Unknown theme: {theme}. Available: {list(THEMES.keys())}"
            )
        _current_theme = THEMES[theme]
    else:
        _current_theme = theme


def with_color(text: str, color: str) -> str:
    """
    Apply color to text if colors are enabled.

    Args:
        text: Text to color
        color: ANSI color code

    Returns:
        Colored text string
    """
    theme = get_theme()
    if theme.color_scheme == ColorScheme.MONOCHROME:
        return text
    return f"{color}{text}{theme.color_reset}"


def success(text: str) -> str:
    """Format text as success."""
    theme = get_theme()
    return with_color(f"{theme.icon_success} {text}", theme.color_success)


def error(text: str) -> str:
    """Format text as error."""
    theme = get_theme()
    return with_color(f"{theme.icon_error} {text}", theme.color_error)


def warning(text: str) -> str:
    """Format text as warning."""
    theme = get_theme()
    return with_color(f"{theme.icon_warning} {text}", theme.color_warning)


def info(text: str) -> str:
    """Format text as info."""
    theme = get_theme()
    return with_color(f"{theme.icon_info} {text}", theme.color_info)


def header(text: str) -> str:
    """Format text as header."""
    theme = get_theme()
    return with_color(text, theme.color_header)


def muted(text: str) -> str:
    """Format text as muted/secondary."""
    theme = get_theme()
    return with_color(text, theme.color_muted)
