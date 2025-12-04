"""
WhosOnFirst Configuration Module

Provides centralized configuration for WOF database paths and naming conventions.
Supports environment variables and auto-discovery of databases.
"""

import logging
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class WOFConfig:
    """Configuration for WhosOnFirst databases."""

    # Default paths
    DEFAULT_DATA_DIR: str = "wof-downloads"
    DEFAULT_PATTERN: str = "whosonfirst-data-admin-{country}-latest.db"

    # Environment variable names
    ENV_DATA_DIR: str = "WOF_DATA_DIR"
    ENV_COUNTRIES: str = "WOF_COUNTRIES"
    ENV_AUTO_DISCOVER: str = "WOF_AUTO_DISCOVER"
    ENV_BACKEND: str = "WOF_BACKEND"

    # Configuration values
    data_dir: Path = field(
        default_factory=lambda: Path(os.getenv("WOF_DATA_DIR", "wof-downloads"))
    )
    countries: Optional[List[str]] = None
    auto_discover: bool = field(
        default_factory=lambda: os.getenv("WOF_AUTO_DISCOVER", "true").lower() == "true"
    )
    backend: str = field(default_factory=lambda: os.getenv("WOF_BACKEND", "sqlite"))

    def __post_init__(self):
        """Initialize configuration from environment."""
        # Parse countries from environment if not provided
        if self.countries is None and os.getenv(self.ENV_COUNTRIES):
            self.countries = [
                c.strip() for c in os.getenv(self.ENV_COUNTRIES, "").split(",")
            ]

        # Ensure data directory is Path object
        if not isinstance(self.data_dir, Path):
            self.data_dir = Path(self.data_dir)

    def get_database_path(self, country_code: str) -> Path:
        """
        Get the database path for a specific country.

        Args:
            country_code: Two-letter country code (e.g., 'us', 'ca')

        Returns:
            Path to the database file
        """
        filename = self.DEFAULT_PATTERN.format(country=country_code.lower())
        return self.data_dir / filename

    def get_simple_database_path(self, country_code: str) -> Path:
        """
        Get simplified database path (e.g., usa.db, canada.db).

        Args:
            country_code: Two-letter country code or country name

        Returns:
            Path to the simplified database file
        """
        # Map common country codes to names
        country_map = {
            "us": "usa",
            "ca": "canada",
            "mx": "mexico",
            "gb": "uk",
            "fr": "france",
            "de": "germany",
            "es": "spain",
            "it": "italy",
            "au": "australia",
            "nz": "new-zealand",
            "jp": "japan",
            "cn": "china",
            "kr": "korea",
            "in": "india",
            "br": "brazil",
            "ar": "argentina",
        }

        name = country_map.get(country_code.lower(), country_code.lower())
        return self.data_dir / f"{name}.db"

    def discover_databases(self) -> List[Path]:
        """
        Auto-discover all WOF databases in the data directory.

        Returns:
            List of paths to discovered database files
        """
        if not self.data_dir.exists():
            return []

        databases: list[Path] = []

        # Look for both naming patterns
        patterns = [
            "whosonfirst-data-admin-*.db",  # Full WOF pattern
            "*.db",  # Simplified pattern (usa.db, canada.db)
        ]

        for pattern in patterns:
            databases.extend(self.data_dir.glob(pattern))

        # Remove duplicates and sort
        databases = sorted(set(databases))

        # Filter out temporary or backup files
        databases = [
            db
            for db in databases
            if not db.name.endswith(".bz2")
            and not db.name.endswith(".tmp")
            and not db.name.startswith(".")
        ]

        return databases

    def get_configured_databases(self) -> List[Path]:
        """
        Get list of databases based on configuration.

        Returns:
            List of database paths to use
        """
        if self.auto_discover:
            # Auto-discover all databases
            databases = self.discover_databases()
        elif self.countries:
            # Use specified countries
            databases = []
            for country in self.countries:
                # Try both naming patterns
                simple_path = self.get_simple_database_path(country)
                full_path = self.get_database_path(country)

                if simple_path.exists():
                    databases.append(simple_path)
                elif full_path.exists():
                    databases.append(full_path)
                else:
                    # Warn but don't fail
                    logger.warning(f"Database not found for {country}")
        else:
            # Default: try common databases
            databases = []
            for country in ["us", "ca"]:
                for path in [
                    self.get_simple_database_path(country),
                    self.get_database_path(country),
                ]:
                    if path.exists():
                        databases.append(path)
                        break

        return databases

    def get_database_info(self, db_path: Path) -> Dict[str, Any]:
        """
        Extract information from a database path.

        Args:
            db_path: Path to database file

        Returns:
            Dictionary with database information
        """
        name = db_path.stem

        # Try to extract country code
        if name.startswith("whosonfirst-data-admin-"):
            # Full WOF pattern
            parts = name.replace("whosonfirst-data-admin-", "").replace("-latest", "")
            country_code = parts
        else:
            # Simple pattern
            country_code = name.replace(".db", "")

        return {
            "path": db_path,
            "name": name,
            "country_code": country_code,
            "source": country_code,  # For source tracking
            "size": db_path.stat().st_size if db_path.exists() else 0,
        }

    def to_env_template(self) -> str:
        """
        Generate environment variable template.

        Returns:
            Template string for .env file
        """
        return f"""# WhosOnFirst Configuration
# Directory containing WOF database files
{self.ENV_DATA_DIR}={self.data_dir}

# Comma-separated list of country codes to use (optional)
# If not set and auto-discover is true, all databases will be used
# {self.ENV_COUNTRIES}=us,ca,mx

# Auto-discover all databases in the data directory
{self.ENV_AUTO_DISCOVER}={str(self.auto_discover).lower()}
"""


# Global configuration instance
_config: Optional[WOFConfig] = None


def get_config() -> WOFConfig:
    """Get or create the global configuration instance."""
    global _config
    if _config is None:
        _config = WOFConfig()
    return _config


def set_config(config: WOFConfig) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config


def reset_config() -> None:
    """Reset configuration to defaults."""
    global _config
    _config = None
