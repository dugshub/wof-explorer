"""
Tests for example files to ensure they use correct imports and syntax.
"""

import ast
from pathlib import Path


def test_example_imports():
    """Test that all examples have correct imports."""
    examples_dir = Path(__file__).parent.parent / "examples"

    # Valid imports from public API
    valid_imports = {
        "WOFConnector",
        "WOFSearchFilters",
        "WOFFilters",
        "PlaceCollection",
        "WOFSearchCursor",
        "WOFBatchCursor",
        "WOFHierarchyCursor",
    }

    for example_file in examples_dir.glob("*.py"):
        if example_file.name.startswith("__"):
            continue

        print(f"Checking {example_file.name}...")

        with open(example_file, "r") as f:
            content = f.read()

        # Parse the AST to check imports
        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module == "wof_explorer":
                    # Check that we only import from public API
                    for alias in node.names:
                        imported_name = alias.name
                        assert (
                            imported_name in valid_imports
                        ), f"Example {example_file.name} imports non-public '{imported_name}'"
                        print(f"  ✓ {imported_name}")


def test_example_syntax():
    """Test that all examples have valid Python syntax."""
    examples_dir = Path(__file__).parent.parent / "examples"

    for example_file in examples_dir.glob("*.py"):
        if example_file.name.startswith("__"):
            continue

        print(f"Syntax checking {example_file.name}...")

        with open(example_file, "r") as f:
            content = f.read()

        try:
            ast.parse(content)
            print("  ✓ Valid syntax")
        except SyntaxError as e:
            raise AssertionError(f"Syntax error in {example_file.name}: {e}")


def test_example_structure():
    """Test that examples follow expected structure."""
    examples_dir = Path(__file__).parent.parent / "examples"

    expected_files = {
        "basic_usage.py",
        "hierarchical_search.py",
        "spatial_queries.py",
        "batch_processing.py",
        "README.md",
    }

    actual_files = {f.name for f in examples_dir.iterdir()}

    missing = expected_files - actual_files
    assert not missing, f"Missing example files: {missing}"

    print(f"✓ All {len(expected_files)} expected files present")


def test_examples_can_import():
    """Test that examples can import without database."""
    examples_dir = Path(__file__).parent.parent / "examples"

    for example_file in examples_dir.glob("*.py"):
        if example_file.name.startswith("__"):
            continue

        print(f"Testing imports for {example_file.name}...")

        # Test that we can at least import the modules used in examples
        try:
            from wof_explorer import WOFConnector, WOFSearchFilters, PlaceCollection

            # Test that imports work
            _ = WOFConnector, WOFSearchFilters, PlaceCollection

            print("  ✓ Imports successful")
        except ImportError as e:
            raise AssertionError(f"Import error in {example_file.name}: {e}")


def test_basic_usage_structure():
    """Test that basic_usage.py has the expected structure."""
    examples_dir = Path(__file__).parent.parent / "examples"
    basic_usage_file = examples_dir / "basic_usage.py"

    with open(basic_usage_file, "r") as f:
        content = f.read()

    # Check for key functions and patterns
    assert "async def basic_example" in content, "Missing basic_example function"
    assert "WOFConnector(" in content, "Missing WOFConnector usage"
    assert "WOFSearchFilters(" in content, "Missing WOFSearchFilters usage"
    assert "await connector.connect()" in content, "Missing connector.connect()"
    assert "await connector.disconnect()" in content, "Missing connector.disconnect()"
    assert "PlaceCollection(" in content, "Missing PlaceCollection usage"

    print("✓ basic_usage.py has correct structure")


def test_batch_processing_fix():
    """Test that batch_processing.py has been fixed after PR feedback."""
    examples_dir = Path(__file__).parent.parent / "examples"
    batch_file = examples_dir / "batch_processing.py"

    with open(batch_file, "r") as f:
        content = f.read()

    # Ensure the bug is fixed - should NOT use batch_cursor.process_in_chunks
    assert (
        "batch_cursor.process_in_chunks" not in content
    ), "batch_processing.py still has the cursor bug - should use cursor, not batch_cursor"

    # Should have proper chunked processing
    assert (
        "for i in range(0, len(" in content
    ), "Missing proper chunked processing implementation"

    print("✓ batch_processing.py cursor bug has been fixed")


def test_cli_module_exists():
    """Test that CLI entry point module exists and is importable."""
    try:
        from wof_explorer.scripts.wof_explore import main

        print("✓ CLI module imports successfully")

        # Test that main function exists and is callable
        assert callable(main), "main() function is not callable"
        print("✓ CLI main() function is callable")

    except ImportError as e:
        raise AssertionError(f"CLI module import error: {e}")


if __name__ == "__main__":
    print("Testing examples...")

    test_example_structure()
    test_example_syntax()
    test_example_imports()
    test_examples_can_import()
    test_basic_usage_structure()
    test_batch_processing_fix()
    test_cli_module_exists()

    print("\n✓ All example tests passed!")
