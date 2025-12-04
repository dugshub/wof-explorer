# Display Module Documentation

Beautiful terminal output utilities for WOF Explorer.

## Overview

The display module provides consistent, beautiful formatting for terminal output including:
- **Tree displays** for hierarchies
- **Tables** for structured data
- **Progress indicators** for long operations
- **Formatters** for consistent data presentation
- **Themes** for customizable styling

## Quick Start

```python
from wof_explorer.display import print_wof_hierarchy, print_table, format_number

# Display hierarchy as tree
ancestors = await hierarchy.fetch_ancestors()
print_wof_hierarchy(ancestors)

# Display results as table
print_table(places, columns=['name', 'type', 'population'])

# Format numbers consistently
print(f"Found {format_number(1234567)} places")
```

## Tree Display

### Basic Usage

```python
from wof_explorer.display.tree import TreeDisplay, print_ancestors_tree

# Method 1: Using TreeDisplay directly
tree = TreeDisplay()
tree.add_node("United States")
tree.add_child("California", parent="United States")
tree.add_child("San Francisco", parent="California")
print(tree.render())

# Method 2: Using convenience function for ancestors
print_ancestors_tree(ancestors)
```

### Output Styles

```python
from wof_explorer.display.tree import TreeStyle

# Unicode (default) - Modern terminals
print_wof_hierarchy(places, style=TreeStyle.UNICODE)
# └── California
#     └── San Francisco

# ASCII - Universal compatibility
print_wof_hierarchy(places, style=TreeStyle.ASCII)
# \-- California
#     \-- San Francisco

# Simple - Minimal
print_wof_hierarchy(places, style=TreeStyle.SIMPLE)
# - California
#   - San Francisco

# With Icons
tree.config.show_icons = True
# 🌍 United States
# └── 📍 California
#     └── 🏙️ San Francisco
```

### WOF-Specific Functions

```python
# Display hierarchy with appropriate icons
print_wof_hierarchy(ancestors)

# Display ancestors (from child to root)
print_ancestors_tree(ancestors, reverse=True)

# Display descendants grouped by type
print_descendants_tree("San Francisco", descendants, group_by='placetype')
```

## Table Display

### Basic Tables

```python
from wof_explorer.display.table import print_table, TableStyle

data = [
    {'name': 'SF', 'population': 873965},
    {'name': 'LA', 'population': 3898747}
]

# Simple table (default)
print_table(data)

# With specific columns
print_table(data, columns=['name', 'population'])

# Different styles
print_table(data, style=TableStyle.ASCII)    # +---+---+
print_table(data, style=TableStyle.UNICODE)  # ┌───┬───┐
print_table(data, style=TableStyle.MARKDOWN) # | col |
```

### Summary Tables

```python
from wof_explorer.display.table import print_summary

stats = {
    'Total Places': 1234,
    'Countries': 3,
    'Coverage': '95%'
}

print_summary("Database Summary", stats)
# Database Summary
# ----------------
# Total Places  1234
# Countries     3
# Coverage      95%
```

### Comparison Tables

```python
from wof_explorer.display.table import print_comparison

before = {'count': 100, 'size': '10MB'}
after = {'count': 150, 'size': '15MB'}

print_comparison(before, after)
# Metric  Before  After  Change
# count   100     150    +50
# size    10MB    15MB   +5MB
```

## Progress Indicators

### Progress Bar

```python
from wof_explorer.display.progress import ProgressDisplay

progress = ProgressDisplay(total=100, description="Loading")
for i in range(100):
    progress.update(i)
    # do work
progress.finish()
# Loading [=========>    ] 75%
```

### Status Display

```python
from wof_explorer.display.progress import StatusDisplay

status = StatusDisplay()

status.start("Connecting to database")
# do work
status.success()  # ✓ Connecting to database: Done

status.start("Loading data")
# do work
status.error("Failed")  # ✗ Loading data: Failed

status.summary()
# Shows summary of all operations
```

## Formatters

### Number Formatting

```python
from wof_explorer.display.formatter import (
    format_number, format_size, format_duration, format_percentage
)

# Numbers with thousands separator
format_number(1234567)  # "1,234,567"
format_number(1234.567, decimals=2)  # "1,234.57"

# File sizes
format_size(1234567890)  # "1.15 GB"

# Durations
format_duration(90)  # "1 minute 30 seconds"
format_duration(3661, short=True)  # "1h1m1s"

# Percentages
format_percentage(750, 1000)  # "75.0%"
```

### WOF-Specific Formatting

```python
from wof_explorer.display.formatter import (
    format_place, format_hierarchy_path, format_status
)

# Format place for display
format_place(place)  # "San Francisco (locality)"
format_place(place, include_id=True)  # "San Francisco (locality) #85922583"

# Format hierarchy as path
format_hierarchy_path(ancestors)  # "United States → California → San Francisco"

# Format status indicators
format_status(place)  # "✓ Current"
```

## Themes

### Using Themes

```python
from wof_explorer.display.styles import set_theme, get_theme

# Set predefined theme
set_theme('minimal')  # Simple ASCII characters
set_theme('ascii')    # Universal compatibility
set_theme('colorful') # Extra colors

# Custom theme
from wof_explorer.display.styles import DisplayTheme

custom_theme = DisplayTheme(
    icon_success='✅',
    icon_error='❌',
    tree_branch='├─ ',
    tree_last='└─ '
)
set_theme(custom_theme)
```

### Styled Messages

```python
from wof_explorer.display.styles import success, error, warning, info

print(success("Operation completed"))  # ✓ Operation completed (green)
print(error("Operation failed"))       # ✗ Operation failed (red)
print(warning("Check results"))        # ⚠ Check results (yellow)
print(info("Processing..."))          # ℹ Processing... (blue)
```

## Complete Example

```python
import asyncio
from wof_explorer import WOFConnector, WOFSearchFilters
from wof_explorer.processing.cursors import WOFHierarchyCursor
from wof_explorer.display import (
    print_wof_hierarchy,
    print_table,
    print_summary,
    format_count,
    success, error, info
)

async def display_demo():
    # Connect
    connector = WOFConnector('database.db')
    await connector.connect()
    print(success("Connected"))

    # Search and display as table
    cursor = await connector.search(WOFSearchFilters(
        placetype="neighbourhood",
        ancestor_name="San Francisco"
    ))

    print(info(f"\nFound {format_count(len(cursor.places), 'neighborhood')}"))
    print_table(
        [{'name': p.name, 'current': '✓' if p.is_current else '✗'}
         for p in cursor.places[:10]],
        columns=['name', 'current']
    )

    # Display hierarchy as tree
    sf = cursor.places[0]
    hierarchy = WOFHierarchyCursor(sf, connector)
    ancestors = await hierarchy.fetch_ancestors()

    print(info("\nHierarchy:"))
    print_wof_hierarchy(ancestors + [sf])

    # Summary
    stats = {
        'Total': len(cursor.places),
        'Current': len([p for p in cursor.places if p.is_current]),
        'Coverage': f"{len(cursor.places) / 50 * 100:.1f}%"
    }
    print_summary("Neighborhood Statistics", stats)

asyncio.run(display_demo())
```

## Best Practices

1. **Use appropriate display for data type**:
   - Trees for hierarchies
   - Tables for structured data
   - Progress for long operations

2. **Be consistent with formatting**:
   - Always use formatters for numbers, sizes, etc.
   - Use the same theme throughout

3. **Consider terminal width**:
   - Tables auto-truncate long values
   - Trees can be limited with `max_depth`

4. **Provide feedback**:
   - Use progress indicators for operations > 1 second
   - Use status displays for multi-step processes

5. **Handle edge cases**:
   - Empty data sets
   - Very long strings
   - Missing values

## Integration with Notebooks

The display utilities work great in Jupyter notebooks:

```python
# In a notebook cell
from wof_explorer.display import print_wof_hierarchy

ancestors = await hierarchy.fetch_ancestors()
print_wof_hierarchy(ancestors)
# Beautiful tree display in notebook output
```

## Performance

The display utilities are designed to be lightweight:
- No external dependencies (pure Python)
- Minimal memory usage
- Efficient string building
- Optional colors can be disabled

## Customization

Everything is customizable:
- Tree symbols and indentation
- Table borders and alignment
- Progress bar width and style
- Number formatting (separators, precision)
- Colors and icons

Create your own theme or modify individual components as needed!