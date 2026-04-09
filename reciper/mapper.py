"""
Mapping module for converting Python package names to conda package names.

This module provides functionality to map Python package names extracted from
import statements to their corresponding conda package names for the static analyzer MVP.
"""

import os
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


def load_mappings() -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    """
    Load package mappings from YAML configuration file.

    Returns:
        Tuple of (primary_mappings, detailed_mappings) where:
        - primary_mappings: Dict[str, str] mapping Python package names to conda package names
        - detailed_mappings: Dict[str, Dict[str, str]] mapping with additional metadata

    The function caches the result after first load and includes fallback to
    default mappings if the YAML file doesn't exist or YAML parsing fails.
    """
    # Module-level cache
    if hasattr(load_mappings, "_cached_mappings"):
        return load_mappings._cached_mappings  # type: ignore

    # Default fallback mappings (same as original hardcoded dictionaries)
    default_primary = {
        "numpy": "numpy",
        "pandas": "pandas",
        "scikit-learn": "scikit-learn",
        "sklearn": "scikit-learn",  # Common alias for scikit-learn
        "matplotlib": "matplotlib",
        "scipy": "scipy",
        "requests": "requests",
        "tensorflow": "tensorflow",
        "torch": "pytorch",
        "pytorch": "pytorch",
        "seaborn": "seaborn",
        "plotly": "plotly",
        "dask": "dask",
        "xarray": "xarray",
        "networkx": "networkx",
        "sympy": "sympy",
        "statsmodels": "statsmodels",
        "pillow": "pillow",
        "opencv-python": "opencv",
        "flask": "flask",
        "django": "django",
        "sqlalchemy": "sqlalchemy",
        "pytest": "pytest",
        "jupyter": "jupyter",
        "notebook": "notebook",
        "ipython": "ipython",
        "black": "black",
        "flake8": "flake8",
        "mypy": "mypy",
        "isort": "isort",
        "pylint": "pylint",
        "yaml": "pyyaml",
        "pyyaml": "pyyaml",
        "toml": "toml",
        "tomli": "tomli",
        "tomlkit": "tomlkit",
        "click": "click",
        "typer": "typer",
        "rich": "rich",
        "tqdm": "tqdm",
        "loguru": "loguru",
        "colorama": "colorama",
        "pathlib": "pathlib",
        "pathlib2": "pathlib2",
        "path": "path",
        "pathlib3": "pathlib3",
        "os": "",  # Standard library, no conda package needed
        "sys": "",  # Standard library
        "collections": "",  # Standard library
        "itertools": "",  # Standard library
        "functools": "",  # Standard library
        "datetime": "",  # Standard library
        "json": "",  # Standard library
        "re": "",  # Standard library
        "math": "",  # Standard library
        "random": "",  # Standard library
        "statistics": "",  # Standard library
        "hashlib": "",  # Standard library
        "ssl": "",  # Standard library
        "socket": "",  # Standard library
        "subprocess": "",  # Standard library
        "multiprocessing": "",  # Standard library
        "threading": "",  # Standard library
        "asyncio": "",  # Standard library
        "typing": "",  # Standard library (Python 3.5+)
        "dataclasses": "",  # Standard library (Python 3.7+)
        "enum": "",  # Standard library
        "abc": "",  # Standard library
        "contextlib": "",  # Standard library
        "copy": "",  # Standard library
        "decimal": "",  # Standard library
        "fractions": "",  # Standard library
        "csv": "",  # Standard library
        "xml": "",  # Standard library
        "html": "",  # Standard library
        "urllib": "",  # Standard library
        "email": "",  # Standard library
        "zipfile": "",  # Standard library
        "tarfile": "",  # Standard library
        "gzip": "",  # Standard library
        "bz2": "",  # Standard library
        "lzma": "",  # Standard library
        "pickle": "",  # Standard library
        "shelve": "",  # Standard library
        "sqlite3": "",  # Standard library
        "tkinter": "",  # Standard library
        "uuid": "",  # Standard library
        "base64": "",  # Standard library
        "binascii": "",  # Standard library
        "hmac": "",  # Standard library
        "secrets": "",  # Standard library
        "time": "",  # Standard library
        "calendar": "",  # Standard library
        "locale": "",  # Standard library
        "gettext": "",  # Standard library
        "string": "",  # Standard library
        "textwrap": "",  # Standard library
        "unicodedata": "",  # Standard library
        "reprlib": "",  # Standard library
        "pprint": "",  # Standard library
        "inspect": "",  # Standard library
        "ast": "",  # Standard library
        "symtable": "",  # Standard library
        "tokenize": "",  # Standard library
        "keyword": "",  # Standard library
        "token": "",  # Standard library
        "opcode": "",  # Standard library
        "dis": "",  # Standard library
        "gc": "",  # Standard library
        "sysconfig": "",  # Standard library
        "site": "",  # Standard library
        "builtins": "",  # Standard library
        "__future__": "",  # Standard library
        "warnings": "",  # Standard library
        "traceback": "",  # Standard library
        "linecache": "",  # Standard library
        "types": "",  # Standard library
        "weakref": "",  # Standard library
        "atexit": "",  # Standard library
        "signal": "",  # Standard library
        "mmap": "",  # Standard library
        "errno": "",  # Standard library
        "ctypes": "",  # Standard library
        "msvcrt": "",  # Standard library (Windows only)
        "winreg": "",  # Standard library (Windows only)
        "posix": "",  # Standard library (Unix only)
        "pwd": "",  # Standard library (Unix only)
        "grp": "",  # Standard library (Unix only)
        "spwd": "",  # Standard library (Unix only)
        "crypt": "",  # Standard library (Unix only)
        "termios": "",  # Standard library (Unix only)
        "tty": "",  # Standard library (Unix only)
        "pty": "",  # Standard library (Unix only)
        "fcntl": "",  # Standard library (Unix only)
        "resource": "",  # Standard library (Unix only)
        "syslog": "",  # Standard library (Unix only)
        "select": "",  # Standard library
        "selectors": "",  # Standard library
        "asyncore": "",  # Standard library
        "asynchat": "",  # Standard library
        "socketserver": "",  # Standard library
        "http": "",  # Standard library
        "ftplib": "",  # Standard library
        "poplib": "",  # Standard library
        "imaplib": "",  # Standard library
        "nntplib": "",  # Standard library
        "smtplib": "",  # Standard library
        "smtpd": "",  # Standard library
        "telnetlib": "",  # Standard library
        "concurrent": "",  # Standard library
        "queue": "",  # Standard library
        "_thread": "",  # Standard library
        "dummy_threading": "",  # Standard library
        "contextvars": "",  # Standard library
    }

    default_detailed = {
        "numpy": {"conda_name": "numpy", "version_constraint": ""},
        "pandas": {"conda_name": "pandas", "version_constraint": ""},
        "scikit-learn": {"conda_name": "scikit-learn", "version_constraint": ""},
        "sklearn": {"conda_name": "scikit-learn", "version_constraint": ""},
        "matplotlib": {"conda_name": "matplotlib", "version_constraint": ""},
        "scipy": {"conda_name": "scipy", "version_constraint": ""},
        "requests": {"conda_name": "requests", "version_constraint": ""},
        "tensorflow": {"conda_name": "tensorflow", "version_constraint": ""},
        "torch": {"conda_name": "pytorch", "version_constraint": ""},
        "pytorch": {"conda_name": "pytorch", "version_constraint": ""},
        "seaborn": {"conda_name": "seaborn", "version_constraint": ""},
        "plotly": {"conda_name": "plotly", "version_constraint": ""},
        "dask": {"conda_name": "dask", "version_constraint": ""},
        "xarray": {"conda_name": "xarray", "version_constraint": ""},
        "networkx": {"conda_name": "networkx", "version_constraint": ""},
        "sympy": {"conda_name": "sympy", "version_constraint": ""},
        "statsmodels": {"conda_name": "statsmodels", "version_constraint": ""},
        "pillow": {"conda_name": "pillow", "version_constraint": ""},
        "opencv-python": {"conda_name": "opencv", "version_constraint": ""},
        "flask": {"conda_name": "flask", "version_constraint": ""},
        "django": {"conda_name": "django", "version_constraint": ""},
        "sqlalchemy": {"conda_name": "sqlalchemy", "version_constraint": ""},
        "pytest": {"conda_name": "pytest", "version_constraint": ""},
        "jupyter": {"conda_name": "jupyter", "version_constraint": ""},
        "notebook": {"conda_name": "notebook", "version_constraint": ""},
        "ipython": {"conda_name": "ipython", "version_constraint": ""},
        "black": {"conda_name": "black", "version_constraint": ""},
        "flake8": {"conda_name": "flake8", "version_constraint": ""},
        "mypy": {"conda_name": "mypy", "version_constraint": ""},
        "isort": {"conda_name": "isort", "version_constraint": ""},
        "pylint": {"conda_name": "pylint", "version_constraint": ""},
        "yaml": {"conda_name": "pyyaml", "version_constraint": ""},
        "pyyaml": {"conda_name": "pyyaml", "version_constraint": ""},
        "toml": {"conda_name": "toml", "version_constraint": ""},
        "tomli": {"conda_name": "tomli", "version_constraint": ""},
        "tomlkit": {"conda_name": "tomlkit", "version_constraint": ""},
        "click": {"conda_name": "click", "version_constraint": ""},
        "typer": {"conda_name": "typer", "version_constraint": ""},
        "rich": {"conda_name": "rich", "version_constraint": ""},
        "tqdm": {"conda_name": "tqdm", "version_constraint": ""},
        "loguru": {"conda_name": "loguru", "version_constraint": ""},
        "colorama": {"conda_name": "colorama", "version_constraint": ""},
    }

    # Try to load from YAML file
    yaml_path = os.path.join(os.path.dirname(__file__), "data", "package_mappings.yaml")
    primary_mappings = default_primary
    detailed_mappings = default_detailed

    if yaml is not None and os.path.exists(yaml_path):
        try:
            with open(yaml_path) as f:
                data = yaml.safe_load(f)
            if data and isinstance(data, dict):
                primary_mappings = data.get("primary_mappings", default_primary)
                detailed_mappings = data.get("detailed_mappings", default_detailed)
        except (yaml.YAMLError, OSError, AttributeError):
            # Fall back to default mappings on any error
            pass

    # Cache the result
    load_mappings._cached_mappings = (primary_mappings, detailed_mappings)  # type: ignore[attr-defined]
    return load_mappings._cached_mappings  # type: ignore[attr-defined, no-any-return]


def map_to_conda(
    python_packages: list[str], version_info: dict[str, str | None] | None = None
) -> list[str]:
    """
    Map Python package names to conda package names with optional version information.

    Args:
        python_packages: List of Python package names extracted from import statements.
        version_info: Optional dictionary mapping package names to version constraints.

    Returns:
        List of conda package specifications in format "conda: {package_name}"
        or "conda: {package_name}=={version}" if version is available.
        Packages not found in the mapping are skipped (not included in output).
    """
    # Load mappings from YAML file (with caching)
    MAPPING, _ = load_mappings()

    conda_packages = []

    for pkg in python_packages:
        # Look up the package in the mapping
        conda_name = MAPPING.get(pkg.lower(), None)

        # If mapping exists and is not empty string, add formatted package
        if conda_name is not None:
            if conda_name:  # Non-empty string
                # Check if version information is available
                version = None
                if version_info and pkg in version_info:
                    version = version_info[pkg]

                if version:
                    # Convert pip-style version to conda-style if needed
                    conda_version = convert_pip_to_conda_version(version)
                    conda_packages.append(f"conda: {conda_name}{conda_version}")
                else:
                    conda_packages.append(f"conda: {conda_name}")
            # If conda_name is empty string (standard library), skip it
        else:
            # Package not in mapping - could log a warning in a real implementation
            # For MVP, we skip unmapped packages
            pass

    return conda_packages


def map_to_conda_with_details(
    python_packages: list[str], version_info: dict[str, str | None] | None = None
) -> list[dict[str, Any]]:
    """
    Map Python package names to conda package names with detailed information.

    Args:
        python_packages: List of Python package names extracted from import statements.
        version_info: Optional dictionary mapping package names to version constraints.

    Returns:
        List of dictionaries with mapping details including source and version information.
    """
    # Load mappings from YAML file (with caching)
    MAPPING, _ = load_mappings()

    mapped_packages = []

    for pkg in python_packages:
        pkg_lower = pkg.lower()
        conda_name = MAPPING.get(pkg_lower)

        if conda_name:
            # Package is in mapping
            version = None
            source = "mapping"

            if version_info and pkg in version_info:
                version = version_info[pkg]
                source = "requirements.txt"
            elif version_info and pkg_lower in version_info:
                version = version_info[pkg_lower]
                source = "requirements.txt"

            mapped_packages.append(
                {
                    "name": pkg,
                    "conda_name": conda_name,
                    "version": version or "latest",
                    "source": source,
                    "mapped": True,
                }
            )
        else:
            # Check if it's a standard library module
            if pkg_lower in [
                "os",
                "sys",
                "collections",
                "itertools",
                "functools",
                "datetime",
                "json",
                "re",
                "math",
                "random",
                "statistics",
                "hashlib",
                "ssl",
                "socket",
                "subprocess",
                "multiprocessing",
                "threading",
                "asyncio",
                "typing",
                "dataclasses",
                "enum",
                "abc",
                "contextlib",
                "copy",
                "decimal",
                "fractions",
                "csv",
                "xml",
                "html",
                "urllib",
                "email",
                "zipfile",
                "tarfile",
                "gzip",
                "bz2",
                "lzma",
                "pickle",
                "shelve",
                "sqlite3",
                "tkinter",
                "uuid",
                "base64",
                "binascii",
                "hmac",
                "secrets",
                "time",
                "calendar",
                "locale",
                "gettext",
                "string",
                "textwrap",
                "unicodedata",
                "reprlib",
                "pprint",
                "inspect",
                "ast",
                "symtable",
                "tokenize",
                "keyword",
                "token",
                "opcode",
                "dis",
                "gc",
                "sysconfig",
                "site",
                "builtins",
                "__future__",
                "warnings",
                "traceback",
                "linecache",
                "types",
                "weakref",
                "atexit",
                "signal",
                "mmap",
                "errno",
                "ctypes",
                "msvcrt",
                "winreg",
                "posix",
                "pwd",
                "grp",
                "spwd",
                "crypt",
                "termios",
                "tty",
                "pty",
                "fcntl",
                "resource",
                "syslog",
                "select",
                "selectors",
                "asyncore",
                "asynchat",
                "socketserver",
                "http",
                "ftplib",
                "poplib",
                "imaplib",
                "nntplib",
                "smtplib",
                "smtpd",
                "telnetlib",
                "concurrent",
                "queue",
                "_thread",
                "dummy_threading",
                "contextvars",
            ]:
                # Standard library, no conda package needed
                mapped_packages.append(
                    {
                        "name": pkg,
                        "conda_name": None,
                        "version": None,
                        "source": "standard_library",
                        "mapped": False,
                    }
                )
            else:
                # Package not in mapping and not standard library
                mapped_packages.append(
                    {
                        "name": pkg,
                        "conda_name": None,
                        "version": None,
                        "source": "unmapped",
                        "mapped": False,
                    }
                )

    return mapped_packages


def convert_pip_to_conda_version(pip_version: str) -> str:
    """
    Convert pip-style version constraint to conda-style.

    Args:
        pip_version: Pip version constraint (e.g., "==1.20.0", ">=1.3.0")

    Returns:
        Conda-style version constraint (e.g., "=1.20.0", ">=1.3.0")

    Note: Conda uses "=1.20.0" instead of "==1.20.0" for exact matches.
    """
    if not pip_version:
        return ""

    # Replace "==" with "=" for exact matches
    if pip_version.startswith("=="):
        return "=" + pip_version[2:]

    # Replace "~=" with compatible release (conda doesn't have exact equivalent)
    # For now, just remove the ~ and keep =
    if pip_version.startswith("~="):
        return "=" + pip_version[2:]

    # Other operators (>=, <=, >, <, !=) are the same in conda
    return pip_version


def get_mapping_source(
    package_name: str, version_info: dict[str, str] | None = None
) -> str:
    """
    Determine the source of mapping for a package.

    Args:
        package_name: Name of the Python package
        version_info: Optional dictionary of version constraints

    Returns:
        Source string: "requirements.txt", "mapping", "standard_library", or "unmapped"
    """
    # Check if in version info (from requirements.txt)
    if version_info and (
        package_name in version_info or package_name.lower() in version_info
    ):
        return "requirements.txt"

    # Check if in mapping
    primary_mappings, _ = load_mappings()
    if package_name.lower() in primary_mappings:
        # Check if it's a standard library (empty string mapping)
        if primary_mappings[package_name.lower()] == "":
            return "standard_library"
        return "mapping"

    return "unmapped"


if __name__ == "__main__":
    """Test cases to verify the mapping functionality."""
    print("Testing mapper.py - Week 2 Enhanced Version Support")
    print("=" * 60)

    # Test 1: Basic mapping without version info
    test_packages = [
        "numpy",
        "pandas",
        "scikit-learn",
        "matplotlib",
        "unknown_package",
        "os",
        "sys",
        "collections",
        "tensorflow",
        "requests",
    ]

    result = map_to_conda(test_packages)

    print("\nTest 1: Basic mapping without version info")
    print("Test Python packages:", test_packages)
    print("Mapped conda packages:", result)

    expected = [
        "conda: numpy",
        "conda: pandas",
        "conda: scikit-learn",
        "conda: matplotlib",
        "conda: tensorflow",
        "conda: requests",
    ]

    if sorted(result) == sorted(expected):
        print("✓ Test 1 passed!")
    else:
        print(f"✗ Test 1 failed. Expected {expected}, got {result}")

    # Test 2: Mapping with version info
    version_info = {"numpy": "==1.24.0", "pandas": ">=2.0.0", "matplotlib": "<3.5.0"}

    result_with_versions = map_to_conda(test_packages, version_info)  # type: ignore[arg-type]

    print("\nTest 2: Mapping with version info")
    print("Version info:", version_info)
    print("Mapped conda packages with versions:", result_with_versions)

    expected_with_versions = [
        "conda: numpy=1.24.0",  # Note: == converted to =
        "conda: pandas>=2.0.0",
        "conda: scikit-learn",
        "conda: matplotlib<3.5.0",
        "conda: tensorflow",
        "conda: requests",
    ]

    if sorted(result_with_versions) == sorted(expected_with_versions):
        print("✓ Test 2 passed!")
    else:
        print(
            f"✗ Test 2 failed. Expected {expected_with_versions}, got {result_with_versions}"
        )

    # Test 3: Detailed mapping
    print("\nTest 3: Detailed mapping with source information")
    detailed_result = map_to_conda_with_details(test_packages, version_info)  # type: ignore[arg-type]

    print(f"Detailed mapping for {len(detailed_result)} packages:")
    for pkg in detailed_result:
        print(
            f"  {pkg['name']} -> {pkg['conda_name'] or 'N/A'} "
            f"(version: {pkg['version']}, source: {pkg['source']}, mapped: {pkg['mapped']})"
        )

    # Count mapped vs unmapped
    mapped_count = sum(1 for pkg in detailed_result if pkg["mapped"])
    unmapped_count = sum(1 for pkg in detailed_result if not pkg["mapped"])

    print(f"\nMapped: {mapped_count}, Unmapped: {unmapped_count}")

    # Test 4: Version conversion
    print("\nTest 4: Pip to Conda version conversion")
    test_versions = [
        ("==1.20.0", "=1.20.0"),
        (">=1.3.0", ">=1.3.0"),
        ("<=2.5.0", "<=2.5.0"),
        ("~=3.2.0", "=3.2.0"),
        ("", ""),
        (None, ""),
    ]

    all_passed = True
    for pip_ver, expected_conda in test_versions:
        if pip_ver is None:
            result = convert_pip_to_conda_version("")  # type: ignore[assignment]
        else:
            result = convert_pip_to_conda_version(pip_ver)  # type: ignore[assignment]

        if result == expected_conda:  # type: ignore[comparison-overlap]
            print(f"  ✓ {pip_ver or 'None'} -> {result}")
        else:
            print(f"  ✗ {pip_ver or 'None'} -> {result} (expected: {expected_conda})")
            all_passed = False

    if all_passed:
        print("✓ Test 4 passed!")

    # Test 5: Mapping source detection
    print("\nTest 5: Mapping source detection")
    test_packages_source = ["numpy", "pandas", "unknown", "os"]

    for pkg in test_packages_source:  # type: ignore[assignment]
        source = get_mapping_source(pkg, version_info)  # type: ignore[arg-type]
        print(f"  {pkg}: {source}")

    print("\n" + "=" * 60)
    print("All mapper tests completed!")
