#!/usr/bin/env python3
"""
Simple CLI interface for WOF Explorer.

This provides a basic command-line interface for the WOF Explorer package.
For more advanced usage, see the examples directory.
"""

import sys
from pathlib import Path


def main():
    """Main CLI entry point."""
    print("WOF Explorer CLI v0.5.0a1")
    print()

    if len(sys.argv) < 2:
        print_usage()
        return

    command = sys.argv[1]

    if command in ["-h", "--help", "help"]:
        print_usage()
    elif command == "version":
        print_version()
    elif command == "examples":
        print_examples()
    elif command == "validate":
        validate_installation()
    elif command == "download":
        run_download()
    elif command == "countries":
        list_countries()
    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)


def print_usage():
    """Print CLI usage information."""
    print("Usage: wof-explore <command> [options]")
    print()
    print("Commands:")
    print("  download <codes>  Download and merge WOF databases")
    print("  countries         List available country codes")
    print("  validate          Test package installation")
    print("  version           Show version information")
    print("  help              Show this help message")
    print()
    print("Examples:")
    print("  wof-explore download us,ca        # Download US + Canada")
    print("  wof-explore download us ca mx     # Download US, Canada, Mexico")
    print("  wof-explore countries             # List country codes")
    print()
    print("For more info: https://github.com/DougsHub/wof-explorer")


def print_version():
    """Print version information."""
    try:
        from wof_explorer import __version__

        print(f"WOF Explorer version: {__version__}")
    except ImportError:
        print("WOF Explorer version: unknown (package not properly installed)")


def print_examples():
    """Print example usage information."""
    print("WOF Explorer Examples:")
    print()
    print("Basic usage:")
    print("  python -m wof_explorer.examples.basic_usage")
    print()
    print("Hierarchical search:")
    print("  python -m wof_explorer.examples.hierarchical_search")
    print()
    print("Spatial queries:")
    print("  python -m wof_explorer.examples.spatial_queries")
    print()
    print("Batch processing:")
    print("  python -m wof_explorer.examples.batch_processing")
    print()
    print("Download examples from:")
    print("  https://github.com/dugspi/wof-explorer/tree/main/examples")


def validate_installation():
    """Validate that WOF Explorer is properly installed."""
    print("Validating WOF Explorer installation...")
    print()

    try:
        # Test basic imports
        from wof_explorer import WOFSearchFilters

        print("✓ Core imports successful")

        # Test version
        from wof_explorer import __version__

        print(f"✓ Version: {__version__}")

        # Test that we can create objects (without connecting to DB)
        _ = WOFSearchFilters(placetype="locality")
        print("✓ Filter creation successful")

        print()
        print("Installation validation successful!")
        print("You can now use WOF Explorer in your Python code.")

    except ImportError as e:
        print(f"✗ Import error: {e}")
        print()
        print("Installation validation failed!")
        print("Try reinstalling with:")
        print("  pip install wof-explorer")
        sys.exit(1)

    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        sys.exit(1)


def run_download():
    """Run the download command."""
    from wof_explorer.scripts.downloader import download_and_merge, COUNTRIES

    args = sys.argv[2:]  # Everything after 'download'

    # Show help
    if args and args[0] in ["-h", "--help"]:
        print("Usage: wof-explore download [country_codes] [options]")
        print()
        print("Arguments:")
        print("  country_codes    Comma-separated or space-separated country codes")
        print()
        print("Options:")
        print("  -o, --output DIR    Output directory (default: ./wof-data)")
        print("  -k, --keep          Keep individual database files after merge")
        print()
        print("Examples:")
        print("  wof-explore download us,ca")
        print("  wof-explore download us ca mx")
        print("  wof-explore download us,ca -o ./data")
        print()
        print("Run 'wof-explore countries' to see all available codes.")
        return

    # Parse arguments
    codes = []
    output_dir = None
    keep_individual = False

    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ["-o", "--output"] and i + 1 < len(args):
            output_dir = Path(args[i + 1])
            i += 2
        elif arg in ["-k", "--keep"]:
            keep_individual = True
            i += 1
        elif arg.startswith("-"):
            print(f"Unknown option: {arg}")
            sys.exit(1)
        else:
            # Could be comma-separated or single code
            codes.extend(c.strip() for c in arg.split(",") if c.strip())
            i += 1

    # Interactive prompt if no codes provided
    if not codes:
        print("Download WhosOnFirst Database")
        print("=" * 40)
        print()
        print("Common codes: US, CA, MX, GB, AU, DE, FR, JP")
        print("Full list:    wof-explore countries")
        print()
        try:
            user_input = input("Enter country codes (comma-separated): ").strip()
            if not user_input:
                print("No countries entered. Exiting.")
                return
            codes = [c.strip() for c in user_input.split(",") if c.strip()]
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled.")
            return

    if not codes:
        print("No country codes provided.")
        sys.exit(1)

    # Run download
    result = download_and_merge(
        country_codes=codes,
        output_dir=output_dir,
        keep_individual=keep_individual,
    )

    if result is None:
        sys.exit(1)


def list_countries():
    """List available country codes."""
    from wof_explorer.scripts.downloader import list_countries as show_countries
    show_countries()


if __name__ == "__main__":
    main()
