"""
Lightweight WOF database downloader.

Downloads WhosOnFirst SQLite databases and merges them into a single file.
Uses Rich for progress display if available, falls back to simple output.
"""

import bz2
import sqlite3
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import List, Optional, Tuple, Dict, Any

# Try to import Rich for nice progress bars
try:
    from rich.progress import (
        Progress,
        SpinnerColumn,
        TextColumn,
        BarColumn,
        DownloadColumn,
        TransferSpeedColumn,
        TaskID,
    )
    from rich.console import Console
    RICH_AVAILABLE = True
    _console = Console()
except ImportError:
    RICH_AVAILABLE = False
    _console = None

# Common country codes with short names for display
COUNTRIES = {
    "us": "United States",
    "ca": "Canada",
    "mx": "Mexico",
    "gb": "United Kingdom",
    "au": "Australia",
    "de": "Germany",
    "fr": "France",
    "it": "Italy",
    "es": "Spain",
    "nl": "Netherlands",
    "be": "Belgium",
    "ch": "Switzerland",
    "at": "Austria",
    "ie": "Ireland",
    "nz": "New Zealand",
    "jp": "Japan",
    "kr": "South Korea",
    "cn": "China",
    "in": "India",
    "br": "Brazil",
    "ar": "Argentina",
    "za": "South Africa",
    "se": "Sweden",
    "no": "Norway",
    "dk": "Denmark",
    "fi": "Finland",
    "pl": "Poland",
    "pt": "Portugal",
    "gr": "Greece",
    "cz": "Czechia",
    "hu": "Hungary",
    "ro": "Romania",
    "bg": "Bulgaria",
    "hr": "Croatia",
    "si": "Slovenia",
    "sk": "Slovakia",
    "ee": "Estonia",
    "lv": "Latvia",
    "lt": "Lithuania",
    "ua": "Ukraine",
    "ru": "Russia",
    "tr": "Turkey",
    "il": "Israel",
    "ae": "UAE",
    "sg": "Singapore",
    "my": "Malaysia",
    "th": "Thailand",
    "vn": "Vietnam",
    "ph": "Philippines",
    "id": "Indonesia",
    "tw": "Taiwan",
    "hk": "Hong Kong",
    "bb": "Barbados",
}

BASE_URL = "https://data.geocode.earth/wof/dist/sqlite"

# Thread-safe printing (fallback when Rich not available)
_print_lock = Lock()


def _print(msg: str):
    """Thread-safe print."""
    with _print_lock:
        print(msg, flush=True)


def get_url(country_code: str) -> str:
    """Get download URL for a country."""
    return f"{BASE_URL}/whosonfirst-data-admin-{country_code.lower()}-latest.db.bz2"


def get_db_path(output_dir: Path, country_code: str) -> Path:
    """Get the output database path."""
    return output_dir / f"whosonfirst-data-admin-{country_code.lower()}-latest.db"


def download_countries_rich(codes: List[str], output_dir: Path) -> List[Path]:
    """Download countries with Rich progress bars."""
    downloaded = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.fields[label]}"),
        BarColumn(bar_width=20),
        DownloadColumn(),
        TransferSpeedColumn(),
        TextColumn("{task.fields[status]}"),
        console=_console,
    ) as progress:
        # Create tasks for each country
        tasks: Dict[str, TaskID] = {}
        for code in codes:
            label = COUNTRIES.get(code, code.upper())
            task_id = progress.add_task(
                "", label=label, status="[yellow]Waiting...", total=None
            )
            tasks[code] = task_id

        def download_one(code: str) -> Tuple[str, Optional[Path]]:
            """Download a single country with progress updates."""
            task_id = tasks[code]
            label = COUNTRIES.get(code, code.upper())
            url = get_url(code)
            compressed_path = output_dir / f"wof-{code}.db.bz2"
            db_path = get_db_path(output_dir, code)

            # Skip if exists
            if db_path.exists():
                size_mb = db_path.stat().st_size / (1024 * 1024)
                progress.update(task_id, status=f"[dim]Exists ({size_mb:.1f} MB)", visible=False)
                return (code, db_path)

            try:
                # Start download
                progress.update(task_id, status="[cyan]Connecting...")
                req = urllib.request.Request(url, headers={"User-Agent": "wof-explorer/0.5"})

                with urllib.request.urlopen(req, timeout=300) as response:
                    total = int(response.headers.get("Content-Length", 0))
                    progress.update(task_id, total=total, completed=0, status="[cyan]Downloading...")

                    with open(compressed_path, "wb") as f:
                        while True:
                            chunk = response.read(65536)
                            if not chunk:
                                break
                            f.write(chunk)
                            progress.advance(task_id, len(chunk))

                # Extract
                progress.update(task_id, status="[yellow]Extracting...", completed=0, total=None)
                with bz2.open(compressed_path, "rb") as f_in:
                    with open(db_path, "wb") as f_out:
                        while True:
                            chunk = f_in.read(1024 * 1024)
                            if not chunk:
                                break
                            f_out.write(chunk)

                compressed_path.unlink()
                size_mb = db_path.stat().st_size / (1024 * 1024)
                progress.update(task_id, status=f"[green]Done ({size_mb:.1f} MB)")
                progress.stop_task(task_id)
                return (code, db_path)

            except urllib.error.HTTPError as e:
                progress.update(task_id, status=f"[red]HTTP {e.code}")
                progress.stop_task(task_id)
                return (code, None)
            except Exception as e:
                progress.update(task_id, status=f"[red]Failed")
                progress.stop_task(task_id)
                return (code, None)

        # Run downloads in parallel
        with ThreadPoolExecutor(max_workers=min(4, len(codes))) as executor:
            futures = {executor.submit(download_one, code): code for code in codes}
            for future in as_completed(futures):
                code, db_path = future.result()
                if db_path:
                    downloaded.append(db_path)

    return downloaded


def download_countries_simple(codes: List[str], output_dir: Path) -> List[Path]:
    """Download countries with simple text output (no Rich)."""
    downloaded = []

    def download_one(code: str) -> Tuple[str, Optional[Path]]:
        label = COUNTRIES.get(code, code.upper())
        url = get_url(code)
        compressed_path = output_dir / f"wof-{code}.db.bz2"
        db_path = get_db_path(output_dir, code)

        if db_path.exists():
            _print(f"  {label}: Already exists")
            return (code, db_path)

        try:
            _print(f"  {label}: Downloading...")
            req = urllib.request.Request(url, headers={"User-Agent": "wof-explorer/0.5"})

            with urllib.request.urlopen(req, timeout=300) as response:
                total = int(response.headers.get("Content-Length", 0))
                dl = 0
                with open(compressed_path, "wb") as f:
                    while True:
                        chunk = response.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        dl += len(chunk)

            _print(f"  {label}: Extracting...")
            with bz2.open(compressed_path, "rb") as f_in:
                with open(db_path, "wb") as f_out:
                    while chunk := f_in.read(1024 * 1024):
                        f_out.write(chunk)

            compressed_path.unlink()
            size_mb = db_path.stat().st_size / (1024 * 1024)
            _print(f"  {label}: Done ({size_mb:.1f} MB)")
            return (code, db_path)

        except Exception as e:
            _print(f"  {label}: Failed ({e})")
            return (code, None)

    with ThreadPoolExecutor(max_workers=min(4, len(codes))) as executor:
        futures = {executor.submit(download_one, code): code for code in codes}
        for future in as_completed(futures):
            code, db_path = future.result()
            if db_path:
                downloaded.append(db_path)

    return downloaded


def verify_database(db_path: Path) -> bool:
    """Check if a SQLite database is valid."""
    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute("SELECT 1 FROM spr LIMIT 1")
        conn.close()
        return True
    except Exception:
        return False


def merge_databases(databases: List[Path], output: Path) -> bool:
    """Merge multiple SQLite databases into one."""
    if len(databases) == 0:
        print("No databases to merge.")
        return False

    # Verify all databases are valid
    valid_dbs = []
    for db in databases:
        if verify_database(db):
            valid_dbs.append(db)
        else:
            print(f"  Warning: {db.name} is corrupted, skipping")

    if len(valid_dbs) == 0:
        print("No valid databases to merge.")
        return False

    databases = valid_dbs

    if len(databases) == 1:
        # Just rename the single database
        print(f"Single database - renaming to {output.name}")
        databases[0].rename(output)
        return True

    print(f"\nMerging {len(databases)} databases...")

    # Sort by size, use largest as base
    databases.sort(key=lambda p: p.stat().st_size, reverse=True)
    base_db = databases[0]
    other_dbs = databases[1:]

    # Copy base to output
    print(f"  Using {base_db.name} as base...")
    import shutil
    shutil.copy2(base_db, output)

    # Connect and merge others
    conn = sqlite3.connect(str(output))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    cursor = conn.cursor()

    tables = ["spr", "names", "geojson", "ancestors", "concordances"]

    try:
        for i, db_path in enumerate(other_dbs, 1):
            print(f"  Merging {db_path.name} ({i}/{len(other_dbs)})...")

            alias = f"db{i}"
            cursor.execute(f"ATTACH DATABASE ? AS {alias}", (str(db_path),))

            for table in tables:
                # Check if table exists
                cursor.execute(
                    f"SELECT name FROM {alias}.sqlite_master WHERE type='table' AND name=?",
                    (table,)
                )
                if not cursor.fetchone():
                    continue

                # Get columns
                cursor.execute(f"PRAGMA {alias}.table_info({table})")
                columns = [row[1] for row in cursor.fetchall()]
                cols_str = ", ".join(columns)

                # Merge with INSERT OR REPLACE
                cursor.execute(f"""
                    INSERT OR REPLACE INTO main.{table} ({cols_str})
                    SELECT {cols_str} FROM {alias}.{table}
                """)

            conn.commit()
            cursor.execute(f"DETACH DATABASE {alias}")

        # Optimize
        print("  Optimizing...")
        cursor.execute("VACUUM")
        cursor.execute("ANALYZE")
        conn.commit()

        # Stats
        cursor.execute("SELECT COUNT(*) FROM spr")
        total = cursor.fetchone()[0]
        size_mb = output.stat().st_size / (1024 * 1024)

        print(f"\nCombined database: {output.name}")
        print(f"  Size: {size_mb:.1f} MB")
        print(f"  Places: {total:,}")

        conn.close()
        return True

    except Exception as e:
        print(f"  Merge failed: {e}")
        conn.close()
        if output.exists():
            output.unlink()
        return False


def download_and_merge(
    country_codes: List[str],
    output_dir: Optional[Path] = None,
    output_name: str = "whosonfirst-combined.db",
    keep_individual: bool = False,
    max_parallel: int = 4,
) -> Optional[Path]:
    """
    Download WOF databases for specified countries and merge into one.

    Args:
        country_codes: List of 2-letter country codes (e.g., ["us", "ca"])
        output_dir: Directory to save files (default: ./wof-data)
        output_name: Name for the merged database
        keep_individual: Keep individual country databases after merging
        max_parallel: Maximum parallel downloads (default: 4)

    Returns:
        Path to merged database, or None on failure
    """
    if output_dir is None:
        output_dir = Path("wof-data")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Normalize country codes
    codes = [c.lower().strip() for c in country_codes]

    # Validate
    invalid = [c for c in codes if len(c) != 2]
    if invalid:
        print(f"Invalid country codes (must be 2 letters): {invalid}")
        return None

    print(f"WOF Database Download")
    print(f"=" * 40)
    print(f"Countries: {', '.join(c.upper() for c in codes)}")
    print(f"Output: {output_dir / output_name}")
    print()

    # Download countries in parallel (use Rich if available)
    if RICH_AVAILABLE:
        downloaded = download_countries_rich(codes, output_dir)
    else:
        downloaded = download_countries_simple(codes, output_dir)

    print()
    if not downloaded:
        print("No databases downloaded successfully.")
        return None

    failed_count = len(codes) - len(downloaded)
    if failed_count > 0:
        print(f"({failed_count} download(s) failed)")

    # Merge
    output_path = output_dir / output_name

    if output_path.exists():
        print(f"\nRemoving existing {output_name}...")
        output_path.unlink()

    if not merge_databases(downloaded, output_path):
        return None

    # Cleanup individual files unless keeping
    if not keep_individual and len(downloaded) > 1:
        print("\nCleaning up individual databases...")
        for db in downloaded:
            if db.exists() and db != output_path:
                db.unlink()

    print(f"\nDone! Database ready at: {output_path}")
    return output_path


def list_countries():
    """Print available country codes."""
    print("Common country codes:")
    print()

    # Group by region for readability
    regions = {
        "North America": ["us", "ca", "mx"],
        "Europe": ["gb", "ie", "de", "fr", "it", "es", "pt", "nl", "be", "ch", "at",
                   "se", "no", "dk", "fi", "pl", "cz", "hu", "gr", "ro", "bg", "hr"],
        "Asia Pacific": ["au", "nz", "jp", "kr", "cn", "tw", "hk", "sg", "my", "th",
                        "vn", "ph", "id", "in"],
        "Other": ["br", "ar", "za", "il", "ae", "tr", "ru", "ua"],
    }

    for region, codes in regions.items():
        print(f"  {region}:")
        items = [f"{c.upper()} ({COUNTRIES.get(c, '?')})" for c in codes if c in COUNTRIES]
        # Print in rows of 3
        for i in range(0, len(items), 3):
            row = items[i:i+3]
            print(f"    {', '.join(row)}")
        print()

    print("Any valid 2-letter ISO country code will work.")
    print("Full list: https://data.geocode.earth/wof/dist/sqlite/")
