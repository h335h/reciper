"""
File scanner component for RECIPER Static Analyzer MVP.

This module provides functionality to scan directories recursively for Python files,
filter out virtual environments, and collect file metadata.
"""

import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class FileInfo:
    """Metadata for a scanned Python file."""

    path: Path
    size: int  # in bytes
    modified_time: float  # timestamp
    relative_path: Path | None = None

    def __post_init__(self) -> None:
        """Post-initialization hook for dataclass.

        Sets relative_path to path if not provided.
        """
        if self.relative_path is None:
            self.relative_path = self.path


def is_virtual_env_directory(path: Path) -> bool:
    """
    Check if a directory is a virtual environment directory.

    Args:
        path: Path to check

    Returns:
        True if the directory appears to be a virtual environment
    """
    # Common virtual environment directory names
    venv_names = {"venv", ".venv", "env", ".env", "virtualenv"}

    # Check if directory name matches virtual environment patterns
    if path.name in venv_names:
        return True

    # Check for common virtual environment marker files
    marker_files = {"pyvenv.cfg", "activate", "activate.bat", "activate.ps1"}
    for marker in marker_files:
        if (path / marker).exists():
            return True

    # Check for Python executable in bin/ or Scripts/ subdirectory
    if (path / "bin" / "python").exists() or (path / "bin" / "python3").exists():
        return True
    if (path / "Scripts" / "python.exe").exists():
        return True

    return False


def should_skip_directory(path: Path) -> bool:
    """
    Determine if a directory should be skipped during scanning.

    Args:
        path: Directory path to check

    Returns:
        True if directory should be skipped
    """
    # Skip virtual environment directories
    if is_virtual_env_directory(path):
        return True

    # Skip hidden directories (starting with .) except .git for version control
    if path.name.startswith(".") and path.name != ".git":
        return True

    # Skip common build and cache directories
    skip_names = {
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".eggs",
        "*.egg-info",
        "site-packages",
    }

    if path.name in skip_names:
        return True

    # Skip directories that match common patterns
    if any(pattern in path.name for pattern in ["cache", "temp", "tmp"]):
        return True

    return False


def scan_directory(
    root_dir: Path,
    progress_callback: Callable[..., None] | None = None,
    max_files: int | None = None,
) -> list[FileInfo]:
    """
    Scan a directory recursively for Python files.

    Args:
        root_dir: Root directory to scan
        progress_callback: Optional callback function for progress reporting
        max_files: Optional maximum number of files to scan (for performance)

    Returns:
        List of FileInfo objects for each Python file found

    Raises:
        FileNotFoundError: If root_dir doesn't exist
        PermissionError: If directory cannot be accessed
    """
    if not root_dir.exists():
        raise FileNotFoundError(f"Directory not found: {root_dir}")

    if not root_dir.is_dir():
        raise ValueError(f"Path is not a directory: {root_dir}")

    python_files: list[FileInfo] = []
    scanned_dirs = 0
    scanned_files = 0

    # Use os.walk for efficient directory traversal
    for dirpath, dirnames, filenames in os.walk(root_dir, followlinks=False):
        current_dir = Path(dirpath)

        # Filter out directories to skip
        dirnames[:] = [
            d for d in dirnames if not should_skip_directory(current_dir / d)
        ]
        scanned_dirs += 1

        # Process Python files in current directory
        for filename in filenames:
            if filename.endswith(".py"):
                file_path = current_dir / filename

                try:
                    # Get file metadata
                    stat = file_path.stat()
                    file_info = FileInfo(
                        path=file_path,
                        size=stat.st_size,
                        modified_time=stat.st_mtime,
                        relative_path=file_path.relative_to(root_dir),
                    )
                    python_files.append(file_info)
                    scanned_files += 1

                    # Call progress callback if provided
                    if progress_callback:
                        progress_callback(
                            scanned_dirs=scanned_dirs,
                            scanned_files=scanned_files,
                            found_files=len(python_files),
                            current_dir=current_dir,
                        )

                    # Stop if we've reached max_files
                    if max_files and len(python_files) >= max_files:
                        return python_files

                except (OSError, PermissionError):
                    # Skip files we can't access
                    continue

    return python_files


def scan_single_file(file_path: Path) -> FileInfo | None:
    """
    Scan a single file and return its metadata.

    Args:
        file_path: Path to the file

    Returns:
        FileInfo object if file is a Python file, None otherwise

    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file cannot be accessed
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    if not file_path.name.endswith(".py"):
        return None

    try:
        stat = file_path.stat()
        return FileInfo(path=file_path, size=stat.st_size, modified_time=stat.st_mtime)
    except (OSError, PermissionError) as e:
        raise PermissionError(f"Cannot access file {file_path}: {e}")


def find_requirements_file(directory: Path) -> Path | None:
    """
    Look for requirements.txt file in a directory.

    Args:
        directory: Directory to search

    Returns:
        Path to requirements.txt if found, None otherwise
    """
    # Check for requirements.txt in the directory
    requirements_path = directory / "requirements.txt"
    if requirements_path.exists() and requirements_path.is_file():
        return requirements_path

    # Also check for pyproject.toml (which may contain dependencies)
    pyproject_path = directory / "pyproject.toml"
    if pyproject_path.exists() and pyproject_path.is_file():
        return pyproject_path

    # Check for setup.py
    setup_path = directory / "setup.py"
    if setup_path.exists() and setup_path.is_file():
        return setup_path

    return None


def get_directory_summary(file_infos: list[FileInfo]) -> dict[str, Any]:
    """
    Generate summary statistics for scanned files.

    Args:
        file_infos: List of FileInfo objects

    Returns:
        Dictionary with summary statistics
    """
    if not file_infos:
        return {
            "total_files": 0,
            "total_size": 0,
            "newest_file": None,
            "oldest_file": None,
            "average_size": 0,
        }

    total_size = sum(f.size for f in file_infos)
    newest_file = max(file_infos, key=lambda f: f.modified_time)
    oldest_file = min(file_infos, key=lambda f: f.modified_time)

    return {
        "total_files": len(file_infos),
        "total_size": total_size,
        "newest_file": newest_file.path,
        "newest_time": time.ctime(newest_file.modified_time),
        "oldest_file": oldest_file.path,
        "oldest_time": time.ctime(oldest_file.modified_time),
        "average_size": total_size / len(file_infos) if file_infos else 0,
    }


def simple_progress_callback(
    scanned_dirs: int, scanned_files: int, found_files: int, current_dir: Path
) -> None:
    """
    Simple progress callback that prints to stdout.

    Args:
        scanned_dirs: Number of directories scanned
        scanned_files: Number of files examined
        found_files: Number of Python files found
        current_dir: Current directory being scanned
    """
    if scanned_dirs % 10 == 0:  # Print every 10 directories
        print(
            f"  Scanned {scanned_dirs} directories, {scanned_files} files, found {found_files} Python files"
        )
        print(f"  Current directory: {current_dir}")


if __name__ == "__main__":
    """Test the scanner module."""
    import shutil
    import tempfile

    # Create a test directory structure
    test_dir = Path(tempfile.mkdtemp(prefix="wac_scanner_test_"))
    print(f"Test directory: {test_dir}")

    try:
        # Create some Python files
        (test_dir / "main.py").write_text("import os\nimport sys\n")
        (test_dir / "utils.py").write_text("from pathlib import Path\n")

        # Create a subdirectory with more files
        subdir = test_dir / "subdir"
        subdir.mkdir()
        (subdir / "module.py").write_text("import numpy as np\n")

        # Create a virtual environment directory (should be skipped)
        venv_dir = test_dir / "venv"
        venv_dir.mkdir()
        (venv_dir / "pyvenv.cfg").write_text("[venv]")

        # Create requirements.txt
        (test_dir / "requirements.txt").write_text("numpy>=1.20\npandas\n")

        # Test scanning
        print("\nScanning directory...")
        files = scan_directory(test_dir, progress_callback=simple_progress_callback)

        print(f"\nFound {len(files)} Python files:")
        for file_info in files:
            print(f"  - {file_info.relative_path} ({file_info.size} bytes)")

        # Test summary
        summary = get_directory_summary(files)
        print(f"\nSummary: {summary}")

        # Test requirements file detection
        req_file = find_requirements_file(test_dir)
        print(f"\nRequirements file found: {req_file}")

        # Test single file scanning
        single_file = scan_single_file(test_dir / "main.py")
        print(f"\nSingle file scan: {single_file}")

        print("\n✓ All tests passed!")

    finally:
        # Cleanup
        shutil.rmtree(test_dir, ignore_errors=True)
