"""
Import aggregator for RECIPER Static Analyzer MVP.

This module aggregates imports from multiple Python files, tracks where each
import occurs, removes duplicates while preserving occurrence information,
and provides statistics.

Phase 9: Added parallel processing and AST caching for performance improvements.
"""

import concurrent.futures
import sys
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from reciper.cache import ASTCache, get_global_cache


@dataclass
class ImportOccurrence:
    """Represents a single occurrence of an import."""

    file_path: Path
    line_number: int | None = None  # Line number in the file (if available)
    import_type: str = "import"  # "import" or "from"
    module_path: str | None = None  # Full module path (e.g., "numpy.linalg")
    alias: str | None = None  # Import alias (e.g., "np" for "import numpy as np")

    def __str__(self) -> str:
        """Return string representation of import occurrence.

        Returns:
            String in format "module as alias at file:line" or "module at file:line".
        """
        location = f"{self.file_path}"
        if self.line_number:
            location += f":{self.line_number}"

        if self.module_path:
            if self.alias:
                return f"{self.module_path} as {self.alias} at {location}"
            else:
                return f"{self.module_path} at {location}"
        else:
            return f"import at {location}"


@dataclass
class AggregatedImport:
    """Aggregated information about a package imported across multiple files."""

    package_name: str
    occurrences: list[ImportOccurrence]
    file_count: int  # Number of files that import this package

    def __post_init__(self) -> None:
        """Post-initialization hook for dataclass.

        Ensures file_count matches the actual number of unique files in occurrences.
        """
        # Ensure file_count matches unique files in occurrences
        unique_files = {occ.file_path for occ in self.occurrences}
        self.file_count = len(unique_files)

    @property
    def frequency(self) -> int:
        """Total number of occurrences across all files."""
        return len(self.occurrences)

    def add_occurrence(self, occurrence: ImportOccurrence) -> None:
        """Add a new occurrence of this import."""
        self.occurrences.append(occurrence)
        # Update file count
        unique_files = {occ.file_path for occ in self.occurrences}
        self.file_count = len(unique_files)


class ImportAggregator:
    """Aggregates imports from multiple Python files."""

    def __init__(self) -> None:
        """Initialize ImportAggregator with empty data structures."""
        self.imports: dict[str, AggregatedImport] = {}
        self.files_processed: set[Path] = set()
        self.total_imports: int = 0
        self.errors: list[tuple[Path, Exception]] = []

    def add_file(self, file_path: Path, imports: list[tuple[str, int | None]]) -> None:
        """
        Add imports from a single file to the aggregator.

        Args:
            file_path: Path to the Python file
            imports: List of (package_name, line_number) tuples
        """
        self.files_processed.add(file_path)

        for package_name, line_number in imports:
            self.total_imports += 1

            # Create import occurrence
            occurrence = ImportOccurrence(
                file_path=file_path,
                line_number=line_number,
                import_type="import",  # Simplified - could be enhanced
                module_path=package_name,
            )

            # Add to aggregated imports
            if package_name not in self.imports:
                self.imports[package_name] = AggregatedImport(
                    package_name=package_name, occurrences=[occurrence], file_count=1
                )
            else:
                self.imports[package_name].add_occurrence(occurrence)

    def add_imports_from_parser(
        self, file_path: Path, package_names: list[str]
    ) -> None:
        """
        Add imports from parser.py output (which doesn't provide line numbers).

        Args:
            file_path: Path to the Python file
            package_names: List of package names extracted by parser.py
        """
        imports = [(pkg, None) for pkg in package_names]
        self.add_file(file_path, imports)  # type: ignore[arg-type]

    def get_statistics(self) -> dict[str, Any]:
        """
        Get statistics about aggregated imports.

        Returns:
            Dictionary with statistics
        """
        if not self.files_processed:
            return {
                "files_processed": 0,
                "total_imports": 0,
                "unique_packages": 0,
                "most_common_packages": [],
                "files_by_import_count": {},
            }

        # Sort packages by frequency (number of files that import them)
        sorted_packages = sorted(
            self.imports.items(), key=lambda x: x[1].file_count, reverse=True
        )

        # Get top 10 most common packages
        most_common = [
            {
                "package": pkg,
                "file_count": agg.file_count,
                "total_occurrences": agg.frequency,
            }
            for pkg, agg in sorted_packages[:10]
        ]

        # Count files by number of imports
        files_by_import_count: dict[int, int] = defaultdict(int)
        for file_path in self.files_processed:
            # Count imports in this file
            import_count = sum(
                1
                for agg in self.imports.values()
                for occ in agg.occurrences
                if occ.file_path == file_path
            )
            files_by_import_count[import_count] += 1

        return {
            "files_processed": len(self.files_processed),
            "total_imports": self.total_imports,
            "unique_packages": len(self.imports),
            "most_common_packages": most_common,
            "files_by_import_count": dict(files_by_import_count),
            "error_count": len(self.errors),
        }

    def get_package_occurrences(self, package_name: str) -> list[ImportOccurrence]:
        """
        Get all occurrences of a specific package.

        Args:
            package_name: Name of the package

        Returns:
            List of ImportOccurrence objects
        """
        if package_name in self.imports:
            return self.imports[package_name].occurrences
        return []

    def get_imports_by_file(self, file_path: Path) -> list[str]:
        """
        Get all packages imported in a specific file.

        Args:
            file_path: Path to the file

        Returns:
            List of package names imported in the file
        """
        packages = set()
        for package_name, agg in self.imports.items():
            for occ in agg.occurrences:
                if occ.file_path == file_path:
                    packages.add(package_name)
        return sorted(packages)

    def get_all_packages(self) -> list[str]:
        """
        Get all unique package names.

        Returns:
            Sorted list of all package names
        """
        return sorted(self.imports.keys())

    def merge(self, other: "ImportAggregator") -> None:
        """
        Merge another ImportAggregator into this one.

        Args:
            other: Another ImportAggregator instance
        """
        # Merge files processed
        self.files_processed.update(other.files_processed)

        # Merge imports
        for package_name, other_agg in other.imports.items():
            if package_name not in self.imports:
                self.imports[package_name] = AggregatedImport(
                    package_name=package_name,
                    occurrences=other_agg.occurrences.copy(),
                    file_count=other_agg.file_count,
                )
            else:
                # Add all occurrences from other aggregator
                for occ in other_agg.occurrences:
                    self.imports[package_name].add_occurrence(occ)

        # Update total imports
        self.total_imports += other.total_imports

        # Merge errors
        self.errors.extend(other.errors)

    def clear(self) -> None:
        """Clear all aggregated data."""
        self.imports.clear()
        self.files_processed.clear()
        self.total_imports = 0
        self.errors.clear()

    def to_dict(self) -> dict[str, Any]:
        """
        Convert aggregator data to a dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "files_processed": [str(p) for p in self.files_processed],
            "imports": {
                pkg: {
                    "package_name": agg.package_name,
                    "file_count": agg.file_count,
                    "frequency": agg.frequency,
                    "occurrences": [
                        {
                            "file_path": str(occ.file_path),
                            "line_number": occ.line_number,
                            "import_type": occ.import_type,
                            "module_path": occ.module_path,
                            "alias": occ.alias,
                        }
                        for occ in agg.occurrences
                    ],
                }
                for pkg, agg in self.imports.items()
            },
            "statistics": self.get_statistics(),
        }


def extract_imports_from_file(
    file_path: Path,
    cache: Optional[ASTCache] = None,
    use_cache: bool = True
) -> tuple[Path, list[str], Optional[Exception]]:
    """
    Extract imports from a single file with optional caching.

    Args:
        file_path: Path to the Python file
        cache: ASTCache instance (uses global cache if None)
        use_cache: Whether to use caching

    Returns:
        Tuple of (file_path, list_of_package_names, error_if_any)
    """
    if cache is None and use_cache:
        cache = get_global_cache()

    try:
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        # Use cache if available
        if use_cache and cache is not None:
            package_names = cache.get_imports(file_path)
            if package_names is not None:
                return (file_path, package_names, None)

        # Fall back to direct parsing
        import ast
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content, filename=str(file_path))
        packages = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    package = alias.name.split(".")[0]
                    packages.add(package)
            elif isinstance(node, ast.ImportFrom):
                if node.module is not None and node.level == 0:
                    package = node.module.split(".")[0]
                    packages.add(package)

        package_names = sorted(packages)
        return (file_path, package_names, None)

    except Exception as e:
        return (file_path, [], e)


def extract_imports_parallel(
    file_paths: list[Path],
    max_workers: Optional[int] = None,
    use_cache: bool = True,
    cache: Optional[ASTCache] = None
) -> ImportAggregator:
    """
    Extract imports from multiple files in parallel.

    Args:
        file_paths: List of file paths to process
        max_workers: Maximum number of worker threads/processes
        use_cache: Whether to use AST caching
        cache: ASTCache instance (uses global cache if None)

    Returns:
        ImportAggregator instance with aggregated imports
    """
    aggregator = ImportAggregator()
    
    # Determine optimal number of workers
    if max_workers is None:
        # Use min(32, number_of_files + 4) as per concurrent.futures recommendation
        max_workers = min(32, len(file_paths) + 4)
    
    # Use ThreadPoolExecutor for I/O bound tasks (file reading)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_file = {
            executor.submit(extract_imports_from_file, file_path, cache, use_cache): file_path
            for file_path in file_paths
        }
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                file_path_result, package_names, error = future.result()
                
                if error is not None:
                    aggregator.errors.append((file_path, error))
                    print(f"Error processing {file_path}: {error}", file=sys.stderr)
                elif package_names:
                    aggregator.add_imports_from_parser(file_path, package_names)
                else:
                    # No imports found, but file was processed successfully
                    aggregator.files_processed.add(file_path)
                    
            except Exception as e:
                aggregator.errors.append((file_path, e))
                print(f"Unexpected error processing {file_path}: {e}", file=sys.stderr)
    
    return aggregator


def aggregate_imports_from_files(
    file_paths: list[Path],
    parser_func: Callable[[str], list[str]],
    parallel: bool = True,
    max_workers: Optional[int] = None,
    use_cache: bool = True,
    cache: Optional[ASTCache] = None
) -> ImportAggregator:
    """
    Aggregate imports from multiple files using a parser function.

    Args:
        file_paths: List of file paths to process
        parser_func: Function that takes a file path and returns list of package names
        parallel: Whether to use parallel processing (enabled by default for >50 files)
        max_workers: Maximum number of worker threads/processes
        use_cache: Whether to use AST caching
        cache: ASTCache instance (uses global cache if None)

    Returns:
        ImportAggregator instance with aggregated imports
    """
    # Auto-enable parallel processing for large projects
    if parallel and len(file_paths) > 50:
        # Use the new parallel implementation
        return extract_imports_parallel(
            file_paths=file_paths,
            max_workers=max_workers,
            use_cache=use_cache,
            cache=cache
        )
    
    # Fall back to sequential processing for small projects
    aggregator = ImportAggregator()
    
    # Use cache if available
    if use_cache and cache is None:
        cache = get_global_cache()

    for file_path in file_paths:
        try:
            if not file_path.exists():
                print(f"Warning: File not found: {file_path}", file=sys.stderr)
                continue

            if not file_path.is_file():
                print(f"Warning: Path is not a file: {file_path}", file=sys.stderr)
                continue

            # Use cache if available
            package_names = None
            if use_cache and cache is not None:
                package_names = cache.get_imports(file_path)
            
            # Fall back to parser function
            if package_names is None:
                package_names = parser_func(str(file_path))

            # Add to aggregator
            aggregator.add_imports_from_parser(file_path, package_names)

        except Exception as e:
            error_msg = f"Error processing {file_path}: {e}"
            print(error_msg, file=sys.stderr)
            aggregator.errors.append((file_path, e))

    return aggregator


def print_aggregation_summary(aggregator: ImportAggregator) -> None:
    """
    Print a human-readable summary of aggregated imports.

    Args:
        aggregator: ImportAggregator instance
    """
    stats = aggregator.get_statistics()

    print("\n" + "=" * 60)
    print("IMPORT AGGREGATION SUMMARY")
    print("=" * 60)
    print(f"Files processed: {stats['files_processed']}")
    print(f"Total imports found: {stats['total_imports']}")
    print(f"Unique packages: {stats['unique_packages']}")

    if stats["error_count"] > 0:
        print(f"Errors encountered: {stats['error_count']}")

    print("\nMost common packages:")
    for i, pkg_info in enumerate(stats["most_common_packages"][:5], 1):
        print(
            f"  {i}. {pkg_info['package']} - {pkg_info['file_count']} files, {pkg_info['total_occurrences']} occurrences"
        )

    print("\nFiles by import count:")
    for import_count, file_count in sorted(stats["files_by_import_count"].items()):
        print(f"  {import_count} imports: {file_count} file(s)")

    print("=" * 60)


if __name__ == "__main__":
    """Test the import aggregator module."""
    import tempfile

    from reciper.parser import parse_imports

    # Create test files
    test_dir = Path(tempfile.mkdtemp(prefix="wac_aggregator_test_"))
    print(f"Test directory: {test_dir}")

    try:
        # Create multiple Python files with imports
        file1 = test_dir / "main.py"
        file1.write_text("""
import numpy as np
import pandas as pd
from sklearn import preprocessing
import os
""")

        file2 = test_dir / "utils.py"
        file2.write_text("""
import numpy
from pathlib import Path
import pandas as pd
import json
""")

        file3 = test_dir / "analysis.py"
        file3.write_text("""
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
import pandas
""")

        # Test aggregation
        print("\nTesting import aggregation...")
        file_paths = [file1, file2, file3]
        aggregator = aggregate_imports_from_files(file_paths, parse_imports)

        # Print summary
        print_aggregation_summary(aggregator)

        # Test specific queries
        print("\nAll unique packages:")
        for pkg in aggregator.get_all_packages():
            print(f"  - {pkg}")

        print("\nOccurrences of 'numpy':")
        for occ in aggregator.get_package_occurrences("numpy"):
            print(f"  - {occ}")

        print("\nImports in main.py:")
        for pkg in aggregator.get_imports_by_file(file1):
            print(f"  - {pkg}")

        # Test statistics
        stats = aggregator.get_statistics()
        assert stats["files_processed"] == 3
        assert (
            stats["unique_packages"] == 7
        )  # numpy, pandas, sklearn, os, pathlib, json, matplotlib
        assert stats["total_imports"] == 10  # Total import statements across all files

        print("\n✓ All tests passed!")

    finally:
        # Cleanup
        import shutil

        shutil.rmtree(test_dir, ignore_errors=True)
