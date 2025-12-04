"""
SQLAlchemy table definitions for WhosOnFirst SQLite database.
These are reflected from the existing database schema.
"""

from typing import Dict
from sqlalchemy import MetaData, Table, Engine

metadata = MetaData()


def get_tables(engine: Engine) -> Dict[str, Table]:
    """
    Reflect tables from the WOF SQLite database.

    Args:
        engine: SQLAlchemy engine connected to the WOF database

    Returns:
        Dict of table name -> Table object

    Raises:
        ValueError: If required tables are not found in the database
    """
    # Reflect all tables from the database
    metadata.reflect(bind=engine)

    # Get tables and ensure they exist
    tables = {}
    required_tables = ["spr", "ancestors", "names", "geojson", "concordances"]

    for table_name in required_tables:
        table = metadata.tables.get(table_name)
        if table is None:
            raise ValueError(f"Required table '{table_name}' not found in database")
        tables[table_name] = table

    return tables


# Table structure documentation for reference
# (actual tables are reflected at runtime)

"""
SPR (Standard Place Response) Table:
    - id: INTEGER PRIMARY KEY
    - parent_id: INTEGER
    - name: TEXT
    - placetype: TEXT
    - country: TEXT
    - repo: TEXT
    - latitude: REAL
    - longitude: REAL
    - min_latitude: REAL
    - min_longitude: REAL
    - max_latitude: REAL
    - max_longitude: REAL
    - is_current: INTEGER (-1, 0, 1)
    - is_deprecated: INTEGER (0, 1)
    - is_ceased: INTEGER (0, 1)
    - is_superseded: INTEGER
    - is_superseding: INTEGER
    - superseded_by: TEXT
    - supersedes: TEXT
    - lastmodified: INTEGER

Ancestors Table:
    - id: INTEGER (place id)
    - ancestor_id: INTEGER
    - ancestor_placetype: TEXT
    - lastmodified: INTEGER

Names Table:
    - id: INTEGER (place id)
    - placetype: TEXT
    - country: TEXT
    - language: TEXT
    - extlang: TEXT
    - script: TEXT
    - region: TEXT
    - variant: TEXT
    - extension: TEXT
    - privateuse: TEXT (preferred, colloquial, variant)
    - name: TEXT
    - lastmodified: INTEGER

GeoJSON Table:
    - id: INTEGER (place id)
    - body: TEXT (JSON geometry)
    - source: TEXT
    - alt_label: TEXT
    - is_alt: BOOLEAN
    - lastmodified: INTEGER

Concordances Table:
    - id: INTEGER (place id)
    - other_id: TEXT
    - other_source: TEXT
    - lastmodified: INTEGER
"""
