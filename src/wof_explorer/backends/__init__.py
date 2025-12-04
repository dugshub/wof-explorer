"""
WOF connector backend implementations.

This package contains backend-specific implementations of the WOF connector interface.
Each backend provides a concrete implementation of WOFConnectorBase.

Available backends:
- sqlite: SQLite database backend with ATTACH support for multi-database queries
- memory: In-memory backend for testing (future)
- postgis: PostGIS backend for production (future)
- api: Remote API backend for cloud deployment (future)
"""

__all__ = []
