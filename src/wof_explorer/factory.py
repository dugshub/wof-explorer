"""
Factory for creating WOF connector instances.

Part of the Infrastructure Subsystems Pattern - handles backend selection
and dependency injection based on configuration.
"""

import logging
import os
from typing import Optional, Union, List, TYPE_CHECKING
from pathlib import Path

from wof_explorer.base import WOFConnectorBase
from wof_explorer.config import get_config

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    # Optional backend imports for type checking only
    pass  # type: ignore[import-not-found]


# Global instance for singleton pattern (optional)
_connector_instance: Optional[WOFConnectorBase] = None


def get_wof_connector(
    db_paths: Optional[Union[str, Path, List[Union[str, Path]]]] = None,
    backend: Optional[str] = None,
    reset: bool = False,
    **kwargs,
) -> WOFConnectorBase:
    """
    Factory function to get a WOF connector instance.

    This is the main entry point for creating WOF connectors. It handles:
    - Backend selection based on configuration or explicit parameter
    - Singleton pattern for reusing connections (optional)
    - Auto-discovery of databases
    - Backward compatibility with existing code

    Args:
        db_paths: Path(s) to database file(s) or connection string(s).
                 If None, uses auto-discovery based on configuration.
        backend: Explicit backend to use (currently only 'sqlite' is supported).
                If None, uses configured default or auto-detects.
        reset: Whether to reset the singleton instance.
        **kwargs: Additional backend-specific parameters.

    Returns:
        WOFConnectorBase: Connector instance for the selected backend.

    Examples:
        # Auto-discovery (uses environment configuration)
        connector = get_wof_connector()

        # Single SQLite database
        connector = get_wof_connector("path/to/database.db")

        # Multiple databases
        connector = get_wof_connector(["usa.db", "canada.db"])

        # Explicit backend selection
        connector = get_wof_connector(backend="sqlite")

        # Reset singleton
        connector = get_wof_connector(reset=True)
    """
    global _connector_instance

    # Reset if requested
    if reset:
        reset_connector()

    # Return existing instance if available (singleton pattern)
    # Disabled by default for backward compatibility
    use_singleton = os.environ.get("WOF_USE_SINGLETON", "false").lower() == "true"
    if use_singleton and _connector_instance is not None:
        return _connector_instance

    # Get configuration
    config = get_config()

    # Determine backend
    if backend is None:
        backend = config.backend  # From environment or default

    # Auto-discovery if no paths provided
    if db_paths is None and backend == "sqlite":
        discovered = config.get_configured_databases()
        if not discovered:
            # Try to be helpful with error message
            data_dir = config.data_dir
            raise FileNotFoundError(
                f"No WOF databases found in {data_dir}. "
                f"Please set WOF_DATA_DIR environment variable or provide explicit paths."
            )
        # Use first discovered database for single-database connector
        db_paths = discovered[0]

    # Select backend implementation
    connector = _create_backend(backend, db_paths, **kwargs)

    # Store as singleton if configured
    if use_singleton:
        _connector_instance = connector

    return connector


def _create_backend(
    backend: str, db_paths: Optional[Union[str, Path, List[Union[str, Path]]]], **kwargs
) -> WOFConnectorBase:
    """
    Create a specific backend instance.

    Args:
        backend: Backend type (currently only 'sqlite' is supported)
        db_paths: Path(s) to data source(s)
        **kwargs: Backend-specific parameters

    Returns:
        WOFConnectorBase: Backend instance

    Raises:
        ValueError: If backend is not supported
    """
    backend = backend.lower()

    if backend == "sqlite":
        # Use the new SQLite backend implementation
        from wof_explorer.backends.sqlite import SQLiteWOFConnector

        # Ensure single path for SQLite connector (not a list)
        if isinstance(db_paths, list):
            db_paths = db_paths[0] if db_paths else None
        return SQLiteWOFConnector(db_paths, **kwargs)

    else:
        raise ValueError(
            f"Unsupported backend: {backend}. "
            f"Currently only 'sqlite' backend is supported."
        )


def reset_connector() -> None:
    """
    Reset the global connector instance.

    This is mainly useful for testing or when switching backends.
    It will attempt to disconnect the existing connector before resetting.
    """
    global _connector_instance

    if _connector_instance is not None:
        # Try to disconnect gracefully
        if _connector_instance.is_connected:
            try:
                # Synchronous disconnect if available
                if hasattr(_connector_instance, "disconnect_sync"):
                    _connector_instance.disconnect_sync()
                else:
                    # Async disconnect - best effort
                    import asyncio

                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # Can't run async in running loop
                            pass
                        else:
                            loop.run_until_complete(_connector_instance.disconnect())
                    except Exception as e:
                        logger.debug(f"Error during connector cleanup: {e}")
            except Exception as e:
                logger.debug(f"Error during connector cleanup: {e}")

    _connector_instance = None


def get_current_connector() -> Optional[WOFConnectorBase]:
    """
    Get the current singleton connector instance if it exists.

    Returns:
        Optional[WOFConnectorBase]: Current connector or None
    """
    return _connector_instance


def create_connector(backend: str, *args, **kwargs) -> WOFConnectorBase:
    """
    Create a new connector instance without singleton pattern.

    This is useful when you need multiple independent connectors.

    Args:
        backend: Backend type to create
        *args: Positional arguments for the backend
        **kwargs: Keyword arguments for the backend

    Returns:
        WOFConnectorBase: New connector instance

    Examples:
        # Create independent SQLite connector
        connector1 = create_connector("sqlite", "usa.db")
        connector2 = create_connector("sqlite", "canada.db")
    """
    # Convert first arg to db_paths if provided
    db_paths = args[0] if args else None

    return _create_backend(backend, db_paths, **kwargs)


# ============= BACKWARD COMPATIBILITY =============


def WOFConnector(
    db_paths: Optional[Union[str, Path, List[Union[str, Path]]]] = None, **kwargs
) -> WOFConnectorBase:
    """
    Backward compatibility wrapper.

    This maintains the original WOFConnector() API for existing code.
    New code should use get_wof_connector() instead.

    Args:
        db_paths: Path(s) to database file(s)
        **kwargs: Additional parameters

    Returns:
        WOFConnectorBase: Connector instance (SQLite backend by default)

    Examples:
        # These all continue to work:
        connector = WOFConnector("database.db")
        connector = WOFConnector(["usa.db", "canada.db"])
        connector = WOFConnector()  # Auto-discovery
    """
    # Use SQLite backend by default for backward compatibility
    return get_wof_connector(db_paths, backend="sqlite", **kwargs)


__all__ = [
    "get_wof_connector",
    "reset_connector",
    "get_current_connector",
    "create_connector",
    "WOFConnector",  # For backward compatibility
]
