"""
SQLite backend for WOF connector.

Provides SQLite-specific implementation with support for:
- Single database queries with optimized performance
- Auto-discovery of databases
- Efficient local file-based access
- Spatial and hierarchical queries
"""

from wof_explorer.backends.sqlite.connector import SQLiteWOFConnector

__all__ = ["SQLiteWOFConnector"]
