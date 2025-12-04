"""
SQLite session and connection management.

Handles engine lifecycle for a single database connection.
Part of the SQLite backend refactoring following Infrastructure Subsystem Pattern.
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path

from sqlalchemy import create_engine, Table
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class SQLiteSessionManager:
    """Manages SQLite database session and connection."""

    def __init__(self, db_path: Path, config: Any = None):
        """
        Initialize session manager for single database.

        Args:
            db_path: Database file path
            config: Optional WOF configuration object
        """
        self.db_path = db_path
        self.config = config

        # Connection state
        self._sync_engine: Optional[Engine] = None
        self._async_engine: Optional[AsyncEngine] = None
        self._connected = False
        self._tables: Optional[Dict[str, Table]] = None

    @property
    def is_connected(self) -> bool:
        """Check if session manager is connected."""
        return self._connected

    async def connect(self) -> AsyncEngine:
        """
        Create and configure async engine.

        Returns:
            AsyncEngine: Configured SQLAlchemy async engine
        """
        if self._connected and self._async_engine:
            return self._async_engine

        # Create connection URL for async SQLite
        url = f"sqlite+aiosqlite:///{self.db_path}"

        # Create async engine with optimized settings
        self._async_engine = create_async_engine(
            url,
            echo=False,
            pool_pre_ping=True,
            connect_args={
                "isolation_level": None,  # autocommit mode
                "check_same_thread": False,
            },
        )

        self._connected = True
        logger.info(f"Connected to database: {self.db_path.name}")

        return self._async_engine

    def connect_sync(self) -> Engine:
        """
        Create synchronous engine for non-async operations.

        Returns:
            Engine: Configured SQLAlchemy sync engine
        """
        if self._sync_engine:
            return self._sync_engine

        # Create connection URL for sync SQLite
        url = f"sqlite:///{self.db_path}"

        # Create sync engine
        self._sync_engine = create_engine(
            url,
            echo=False,
            pool_pre_ping=True,
            connect_args={
                "isolation_level": None,  # autocommit mode
                "check_same_thread": False,
            },
        )

        logger.debug(f"Created sync engine for '{self.db_path.name}'")
        return self._sync_engine

    async def get_tables(self) -> Dict[str, Table]:
        """
        Get table references.

        Returns:
            Dict mapping table names to SQLAlchemy table objects
        """
        if self._tables:
            return self._tables

        if not self._sync_engine:
            self.connect_sync()

        from .tables import get_tables

        if self._sync_engine is None:
            raise RuntimeError("Failed to create sync engine")

        self._tables = get_tables(self._sync_engine)
        return self._tables

    async def disconnect(self) -> None:
        """Close database connection and clean up resources."""
        if not self._connected:
            return

        # Dispose async engine
        if self._async_engine:
            await self._async_engine.dispose()
            self._async_engine = None
            logger.debug("Disposed async engine")

        # Dispose sync engine
        if self._sync_engine:
            self._sync_engine.dispose()
            self._sync_engine = None
            logger.debug("Disposed sync engine")

        self._connected = False
        self._tables = None
        logger.info("Disconnected from database")

    def get_async_engine(self) -> Optional[AsyncEngine]:
        """Get the async engine if connected."""
        return self._async_engine if self._connected else None

    def get_sync_engine(self) -> Optional[Engine]:
        """Get the sync engine if created."""
        return self._sync_engine
